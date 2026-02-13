"""
UDP-Based Low Latency Streaming for WVAB
This implements UDP protocol for reduced latency compared to TCP
"""

import socket
import struct
import cv2
import numpy as np
from ultralytics import YOLO
import pyttsx3
import threading
import time
import queue


MAX_UDP_PAYLOAD = 60000
HEADER_FORMAT = "!IHHH"  # frame_id, total_chunks, chunk_index, payload_size
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
FRAME_BUFFER_TIMEOUT = 2.0

class UDPVisionServer:
    """
    Low-latency vision processing server using UDP protocol
    Optimized for real-time blind navigation assistance
    """
    
    def __init__(self, host='0.0.0.0', port=9999, model_path='yolov8n.pt'):
        self.host = host
        self.port = port
        self.model = YOLO(model_path)
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 160)
        self.speech_queue = queue.Queue(maxsize=20)
        self.tts_stop_event = threading.Event()
        self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.tts_thread.start()
        
        # UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        # Performance metrics
        self.frame_count = 0
        self.fps = 0
        self.latency = 0
        
        # Detection settings
        self.confidence_threshold = 0.5
        self.last_announcement = {}
        self.announcement_cooldown = 2.5  # seconds
        
        # Priority objects for blind navigation
        self.critical_objects = {
            'person': ('Person', 1),
            'car': ('Vehicle', 1),
            'truck': ('Large vehicle', 1),
            'bus': ('Bus', 1),
            'bicycle': ('Bicycle', 2),
            'motorcycle': ('Motorcycle', 2),
            'stop sign': ('Stop sign', 3),
            'traffic light': ('Traffic light', 3),
            'chair': ('Obstacle', 4),
            'bench': ('Obstacle', 4),
            'potted plant': ('Obstacle', 4)
        }

    def _tts_worker(self):
        """Single speech worker to avoid concurrent pyttsx3 access."""
        while not self.tts_stop_event.is_set():
            try:
                text = self.speech_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                print(f"TTS error: {e}")
    
    def speak(self, text, priority=1):
        """Queue text-to-speech output (non-blocking)."""
        try:
            self.speech_queue.put_nowait(text)
        except queue.Full:
            # Drop low-priority/late messages under heavy load.
            pass

    def stop_tts(self):
        """Stop TTS worker thread cleanly."""
        self.tts_stop_event.set()
        if self.tts_thread.is_alive():
            self.tts_thread.join(timeout=1.0)
    
    def calculate_distance_estimate(self, bbox, frame_shape):
        """
        Estimate relative distance based on bounding box size
        Returns: 'immediate', 'close', 'medium', or 'far'
        """
        bbox_height = bbox[3] - bbox[1]
        frame_height = frame_shape[0]
        
        height_ratio = bbox_height / frame_height
        
        if height_ratio > 0.6:
            return 'immediate'
        elif height_ratio > 0.4:
            return 'close'
        elif height_ratio > 0.2:
            return 'medium'
        else:
            return 'far'
    
    def calculate_position(self, bbox, frame_shape):
        """
        Calculate object position relative to user
        Returns: direction and distance
        """
        x_center = (bbox[0] + bbox[2]) / 2
        frame_width = frame_shape[1]
        
        # Horizontal position
        if x_center < frame_width * 0.3:
            direction = 'left'
        elif x_center > frame_width * 0.7:
            direction = 'right'
        else:
            direction = 'center'
        
        # Distance estimation
        distance = self.calculate_distance_estimate(bbox, frame_shape)
        
        return direction, distance
    
    def should_announce(self, object_key):
        """Check if announcement cooldown has passed"""
        current_time = time.time()
        
        if object_key not in self.last_announcement:
            self.last_announcement[object_key] = current_time
            return True
        
        elapsed = current_time - self.last_announcement[object_key]
        if elapsed > self.announcement_cooldown:
            self.last_announcement[object_key] = current_time
            return True
        
        return False
    
    def process_frame(self, frame):
        """Process frame with YOLO detection and generate audio feedback"""
        start_time = time.time()
        
        # Run detection
        results = self.model(frame, verbose=False)
        
        announcements = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                confidence = float(box.conf[0])
                
                if confidence < self.confidence_threshold:
                    continue
                
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                
                if class_name not in self.critical_objects:
                    continue
                
                bbox = box.xyxy[0].cpu().numpy()
                direction, distance = self.calculate_position(bbox, frame.shape)
                
                # Create announcement
                obj_label, priority = self.critical_objects[class_name]
                announcement_key = f"{class_name}_{direction}"
                
                if self.should_announce(announcement_key):
                    # Formulate message
                    if distance == 'immediate':
                        message = f"Warning! {obj_label} very close {direction}"
                    elif distance == 'close':
                        message = f"{obj_label} {direction} close"
                    else:
                        message = f"{obj_label} {direction}"
                    
                    announcements.append((message, priority))
                    
                    # Draw on frame
                    bbox_int = bbox.astype(int)
                    color = (0, 0, 255) if distance in ['immediate', 'close'] else (0, 255, 0)
                    cv2.rectangle(frame, (bbox_int[0], bbox_int[1]), 
                                (bbox_int[2], bbox_int[3]), color, 2)
                    cv2.putText(frame, f"{obj_label} {direction}", 
                              (bbox_int[0], bbox_int[1] - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Announce highest priority detection first
        if announcements:
            announcements.sort(key=lambda x: x[1])
            self.speak(announcements[0][0], announcements[0][1])
        
        # Calculate latency
        self.latency = (time.time() - start_time) * 1000  # ms
        
        return frame
    
    def receive_frames(self):
        """Receive frames via UDP and process them"""
        self.sock.bind((self.host, self.port))
        
        print("=" * 60)
        print("UDP Vision Server Started")
        print("=" * 60)
        print(f"Listening on {self.host}:{self.port}")
        print("Waiting for frames from ESP32-CAM...")
        print("=" * 60)
        
        frame_buffers = {}
        last_cleanup = time.time()
        
        frame_times = []
        last_fps_time = time.time()
        
        try:
            while True:
                # Receive data
                packet, addr = self.sock.recvfrom(65536)
                if len(packet) < HEADER_SIZE:
                    continue

                frame_id, total_chunks, chunk_index, payload_size = struct.unpack(
                    HEADER_FORMAT, packet[:HEADER_SIZE]
                )
                chunk_payload = packet[HEADER_SIZE:]

                if payload_size != len(chunk_payload) or chunk_index >= total_chunks:
                    continue

                if frame_id not in frame_buffers:
                    frame_buffers[frame_id] = {
                        "total": total_chunks,
                        "chunks": {},
                        "timestamp": time.time(),
                    }

                entry = frame_buffers[frame_id]
                if entry["total"] != total_chunks:
                    del frame_buffers[frame_id]
                    continue

                entry["chunks"][chunk_index] = chunk_payload

                if len(entry["chunks"]) == total_chunks:
                    frame_bytes = b"".join(entry["chunks"][i] for i in range(total_chunks))
                    del frame_buffers[frame_id]

                    frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
                    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                    if frame is None:
                        continue

                    # Process frame
                    processed_frame = self.process_frame(frame)

                    # Calculate FPS
                    self.frame_count += 1
                    frame_times.append(time.time())

                    if time.time() - last_fps_time > 1.0:
                        frame_times = [t for t in frame_times if time.time() - t < 1.0]
                        self.fps = len(frame_times)
                        last_fps_time = time.time()

                        print(
                            f"FPS: {self.fps:.1f} | Latency: {self.latency:.1f}ms | "
                            f"Frames: {self.frame_count}"
                        )

                    # Display frame
                    cv2.putText(
                        processed_frame,
                        f"FPS: {self.fps:.1f} | Latency: {self.latency:.0f}ms",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )

                    cv2.imshow('WVAB - UDP Server', processed_frame)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                # Cleanup stale incomplete frames.
                if time.time() - last_cleanup > 1.0:
                    cutoff = time.time() - FRAME_BUFFER_TIMEOUT
                    stale_ids = [
                        fid for fid, entry in frame_buffers.items()
                        if entry["timestamp"] < cutoff
                    ]
                    for fid in stale_ids:
                        del frame_buffers[fid]
                    last_cleanup = time.time()
        
        except KeyboardInterrupt:
            print("\nShutting down UDP server...")
        
        finally:
            self.stop_tts()
            self.sock.close()
            cv2.destroyAllWindows()
            print("UDP server stopped")


class UDPCameraClient:
    """
    UDP Client for ESP32-CAM or webcam
    Sends frames via UDP to the vision server
    """
    
    def __init__(self, server_ip='192.168.4.1', server_port=9999):
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
    
    def send_frames(self, camera_source=0):
        """
        Send frames from camera to server
        camera_source: 0 for webcam, or IP camera URL
        """
        cap = cv2.VideoCapture(camera_source)
        
        if not cap.isOpened():
            print(f"Error: Could not open camera {camera_source}")
            return
        
        print("=" * 60)
        print("UDP Camera Client Started")
        print("=" * 60)
        print(f"Sending frames to {self.server_ip}:{self.server_port}")
        print("Press 'q' to quit")
        print("=" * 60)
        
        frame_count = 0
        frame_id = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Resize frame to reduce bandwidth
                frame = cv2.resize(frame, (640, 480))
                
                # JPEG encode before sending to fit practical UDP payload sizes.
                ok, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if not ok:
                    continue

                data = buffer.tobytes()
                max_chunk = MAX_UDP_PAYLOAD - HEADER_SIZE
                total_chunks = (len(data) + max_chunk - 1) // max_chunk
                if total_chunks > 65535:
                    continue

                for chunk_index in range(total_chunks):
                    start = chunk_index * max_chunk
                    end = start + max_chunk
                    chunk_payload = data[start:end]
                    header = struct.pack(
                        HEADER_FORMAT,
                        frame_id,
                        total_chunks,
                        chunk_index,
                        len(chunk_payload),
                    )
                    self.sock.sendto(header + chunk_payload, (self.server_ip, self.server_port))

                frame_id = (frame_id + 1) % (2 ** 32)
                
                frame_count += 1
                if frame_count % 30 == 0:
                    print(f"Sent {frame_count} frames")
                
                # Show local preview
                cv2.imshow('Camera Client', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
        except KeyboardInterrupt:
            print("\nStopping camera client...")
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.sock.close()
            print("Camera client stopped")


def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("WVAB UDP Low-Latency System")
    print("=" * 60)
    print("\n1. Start UDP Server (Vision Processing)")
    print("2. Start UDP Client (Camera Sender)")
    print("3. Exit")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        server = UDPVisionServer()
        server.receive_frames()
    
    elif choice == "2":
        server_ip = input("Enter server IP (default 192.168.4.1): ").strip() or "192.168.4.1"
        camera = input("Enter camera source (0 for webcam, or URL): ").strip() or "0"
        
        if camera == "0":
            camera = 0
        
        client = UDPCameraClient(server_ip=server_ip)
        client.send_frames(camera_source=camera)
    
    else:
        print("Exiting...")


if __name__ == "__main__":
    main()
