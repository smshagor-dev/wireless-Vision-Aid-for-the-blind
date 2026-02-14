"""
Wireless Vision-Aid for the Blind (WVAB) - Main Server
This script receives video stream from ESP32-CAM via Wi-Fi and performs real-time object detection
"""

import cv2
import numpy as np
from ultralytics import YOLO
import pyttsx3
import threading
import time
from collections import deque
import urllib.request
import queue
import os
import subprocess
import json
import unicodedata

class VisionAidServer:
    def __init__(
        self,
        camera_url="http://192.168.4.1:81/stream",
        model_path="yolov8n.pt",
        language="en",
        labels_path="multilingual_labels.common.json",
    ):
        """
        Initialize the Vision Aid Server
        
        Args:
            camera_url: URL of the ESP32-CAM or IP camera stream
            model_path: Path to YOLO model (yolov8n.pt for nano, yolov8s.pt for small)
        """
        self.camera_url = camera_url
        self.model = YOLO(model_path)
        self.language = language
        self.speech_language = self.language
        self.labels_path = labels_path
        self.tts_engine = None
        self.cpp_speaker_path = self._find_cpp_speaker()
        self.speech_queue = queue.Queue(maxsize=1)
        self.speech_lock = threading.Lock()
        self.priority_speech = None
        self.latest_speech = None
        self.speech_event = threading.Event()
        self.tts_stop_event = threading.Event()
        self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.tts_thread.start()
        self.last_spoken_text = ""
        
        # Detection parameters
        self.confidence_threshold = 0.5
        self.detection_cooldown = 0.25  # low-latency repeated updates
        self.last_announcement = {}
        self.navigation_cooldown = 0.6
        self.last_navigation_message = ""
        self.last_navigation_time = 0.0
        self.detect_all_objects = True
        self.max_audio_objects_per_frame = 1
        self.stability_window = 4
        self.min_stable_frames = 1
        self.recent_detection_keys = deque(maxlen=self.stability_window)
        self.model_imgsz = 416
        
        # Priority objects (most important for blind navigation)
        self.priority_objects = {
            'person': 'Person',
            'car': 'Car',
            'truck': 'Truck',
            'bicycle': 'Bicycle',
            'motorcycle': 'Motorcycle',
            'bus': 'Bus',
            'traffic light': 'Traffic light',
            'stop sign': 'Stop sign',
            'chair': 'Chair',
            'door': 'Door',
            'stairs': 'Stairs'
        }

        # Higher score means higher risk for path planning.
        self.navigation_risk_weights = {
            'person': 2.0,
            'car': 3.0,
            'truck': 3.5,
            'bicycle': 2.0,
            'motorcycle': 2.5,
            'bus': 3.5,
            'traffic light': 1.0,
            'stop sign': 1.0,
            'chair': 1.5,
            'door': 0.5,
            'stairs': 4.0
        }
        
        self.running = False
        self.frame_buffer = deque(maxlen=30)
        self.multilingual_labels = self._load_multilingual_labels(self.labels_path)
        self.available_languages = self._detect_available_languages(self.multilingual_labels)
        if self.language not in self.available_languages:
            self.language = "en"
        self.speech_language = self._resolve_speech_language(self.language)
        self.navigation_phrases = {
            "STOP - obstacle very close": {
                "en": "STOP obstacle very close",
                "ru": "СТОП, препятствие очень близко",
            },
            "GO LEFT": {
                "en": "GO LEFT",
                "ru": "ИДИТЕ НАЛЕВО",
            },
            "GO RIGHT": {
                "en": "GO RIGHT",
                "ru": "ИДИТЕ НАПРАВО",
            },
            "SLOW - path blocked ahead": {
                "en": "SLOW DOWN, path blocked ahead",
                "ru": "МЕДЛЕННЕЕ, путь впереди заблокирован",
            },
            "CLEAN AREA GO STRAIGHT": {
                "en": "CLEAN AREA GO STRAIGHT",
                "ru": "ПУТЬ СВОБОДЕН, ИДИТЕ ПРЯМО",
            },
        }

    def _find_cpp_speaker(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "cpp", "build", "wvab_speaker.exe"),
            os.path.join(base_dir, "cpp", "build", "Release", "wvab_speaker.exe"),
            os.path.join(base_dir, "cpp", "build", "Debug", "wvab_speaker.exe"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _detect_tts_languages(self):
        langs = {"en"}
        if os.name != "nt":
            return langs
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            cmd = (
                "Add-Type -AssemblyName System.Speech; "
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Culture.Name }"
            )
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                check=False,
                creationflags=flags,
                timeout=5,
            )
            for line in (r.stdout or "").splitlines():
                code = line.strip().lower()
                if code:
                    langs.add(code.split("-")[0])
        except Exception:
            pass
        return langs

    def _resolve_speech_language(self, requested_language):
        installed = self._detect_tts_languages()
        if requested_language in installed:
            return requested_language
        print(f"Warning: TTS voice for '{requested_language}' not found. Falling back to 'en'.")
        return "en"

    def _load_multilingual_labels(self, path):
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            print(f"Warning: could not load labels file '{path}': {exc}")
            return {}

    def _detect_available_languages(self, labels):
        langs = {"en"}
        if isinstance(labels, dict):
            for value in labels.values():
                if isinstance(value, dict):
                    for k in value.keys():
                        if isinstance(k, str) and k.strip():
                            langs.add(k.strip().lower())
        return sorted(langs)

    def set_language(self, language):
        self.language = (language or "en").strip().lower()

    def translate_class_name(self, class_name):
        fallback = self.priority_objects.get(class_name, self.prettify_class_name(class_name))
        entry = self.multilingual_labels.get(class_name)
        if isinstance(entry, dict):
            return entry.get(self.language, entry.get("en", fallback))
        return fallback

    def translate_navigation(self, instruction):
        mapping = self.navigation_phrases.get(instruction)
        if isinstance(mapping, dict):
            return mapping.get(self.language, mapping.get("en", instruction))
        return instruction

    def _localized_direction(self, direction):
        phrases = self.multilingual_labels.get("__phrases__", {})
        if isinstance(phrases, dict):
            lang_map = phrases.get(self.language, {})
            if isinstance(lang_map, dict):
                maybe = lang_map.get(direction)
                if isinstance(maybe, str) and maybe.strip():
                    return maybe
        table = {
            "en": {"left": "in left", "right": "in right", "in front": "in front"},
            "ru": {"left": "слева", "right": "справа", "in front": "спереди"},
        }
        return table.get(self.language, table["en"]).get(direction, direction)

    def _localized_distance(self, distance):
        phrases = self.multilingual_labels.get("__phrases__", {})
        if isinstance(phrases, dict):
            lang_map = phrases.get(self.language, {})
            if isinstance(lang_map, dict):
                maybe = lang_map.get(distance)
                if isinstance(maybe, str) and maybe.strip():
                    return maybe
        table = {
            "en": {"too far": "too far", "close": "close", "very close": "very close"},
            "ru": {"too far": "далеко", "close": "близко", "very close": "очень близко"},
        }
        return table.get(self.language, table["en"]).get(distance, distance)

    def _overlay_safe_text(self, text):
        try:
            text.encode("ascii")
            return text
        except UnicodeEncodeError:
            normalized = unicodedata.normalize("NFKD", text)
            ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
            return ascii_text if ascii_text.strip() else "object"

    def prettify_class_name(self, class_name):
        return class_name.replace("_", " ").strip().title()

    def _tts_worker(self):
        """Single speech worker to keep pyttsx3 access thread-safe."""
        while not self.tts_stop_event.is_set():
            self.speech_event.wait(timeout=0.1)
            if self.tts_stop_event.is_set():
                break

            text = None
            with self.speech_lock:
                if self.priority_speech is not None:
                    text = self.priority_speech
                    self.priority_speech = None
                elif self.latest_speech is not None:
                    text = self.latest_speech
                    self.latest_speech = None
                self.speech_event.clear()
            if not text:
                continue
            try:
                self._speak_blocking(text)
                self.last_spoken_text = text
            except Exception as e:
                print(f"TTS error: {e}")

    def _speak_blocking(self, text):
        if self.cpp_speaker_path and os.name == "nt" and self.speech_language == "en":
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            result = subprocess.run(
                [self.cpp_speaker_path, text],
                check=False,
                timeout=4,
                creationflags=flags,
            )
            if result.returncode == 0:
                return

        if os.name == "nt":
            escaped = text.replace("'", "''")
            escaped_lang = (self.speech_language or "en").replace("'", "''")
            ps_cmd = (
                "Add-Type -AssemblyName System.Speech; "
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$lang='{escaped_lang}'; "
                "$v=$s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo } | "
                "Where-Object { $_.Culture.TwoLetterISOLanguageName -eq $lang } | Select-Object -First 1; "
                "if($v){$s.SelectVoice($v.Name)}; "
                "$s.Rate=2; "
                f"$s.Speak('{escaped}')"
            )
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                check=False,
                timeout=5,
                creationflags=flags,
            )
            if result.returncode == 0:
                return

        engine = pyttsx3.init()
        engine.setProperty('rate', 190)
        engine.setProperty('volume', 1.0)
        engine.say(text)
        engine.runAndWait()
        engine.stop()

    def speak(self, text):
        """Queue text-to-speech output (non-blocking)."""
        with self.speech_lock:
            self.priority_speech = None
            self.latest_speech = text
            self.speech_event.set()

    def speak_priority(self, text):
        """Prioritize urgent navigation speech by clearing stale queue."""
        with self.speech_lock:
            self.priority_speech = text
            self.speech_event.set()

    def stop_tts(self):
        """Stop the TTS worker cleanly."""
        self.tts_stop_event.set()
        self.speech_event.set()
        if self.tts_thread.is_alive():
            self.tts_thread.join(timeout=1.0)
    
    def should_announce(self, object_name):
        """Check if enough time has passed since last announcement"""
        current_time = time.time()
        if object_name not in self.last_announcement:
            self.last_announcement[object_name] = current_time
            return True
        
        if current_time - self.last_announcement[object_name] > self.detection_cooldown:
            self.last_announcement[object_name] = current_time
            return True
        
        return False

    def is_stable_detection(self, detection_key):
        count = 0
        for frame_keys in self.recent_detection_keys:
            if detection_key in frame_keys:
                count += 1
        return count >= self.min_stable_frames
    
    def get_direction(self, bbox, frame_width):
        """Determine if object is left, center, or right"""
        x_center = (bbox[0] + bbox[2]) / 2
        
        if x_center < frame_width * 0.33:
            return "left"
        elif x_center > frame_width * 0.67:
            return "right"
        else:
            return "in front"
    
    def process_detections(self, results, frame):
        """Process YOLO detection results and generate audio feedback"""
        frame_height, frame_width = frame.shape[:2]
        detections = []
        frame_keys = set()
        speech_candidates = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                confidence = float(box.conf[0])
                if confidence < self.confidence_threshold:
                    continue
                
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                bbox = box.xyxy[0].cpu().numpy()
                
                if (not self.detect_all_objects) and (class_name not in self.priority_objects):
                    continue

                direction = self.get_direction(bbox, frame_width)
                
                # Calculate distance estimation (very rough, based on bbox size)
                bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                frame_area = frame_width * frame_height
                size_ratio = bbox_area / frame_area
                
                if size_ratio > 0.3:
                    distance = "very close"
                elif size_ratio > 0.15:
                    distance = "close"
                else:
                    distance = "too far"

                spoken_name = self.translate_class_name(class_name)
                detection_info = {
                    'class': class_name,
                    'label': spoken_name,
                    'confidence': confidence,
                    'direction': direction,
                    'distance': distance,
                    'bbox': bbox
                }
                detections.append(detection_info)

                detection_key = f"{class_name}_{direction}_{distance}"
                frame_keys.add(detection_key)
                speech_candidates.append(
                    (confidence, detection_key, spoken_name, direction, distance)
                )

        self.recent_detection_keys.append(frame_keys)

        # Speak only top confident stable objects to avoid audio flood.
        spoken_this_frame = 0
        used_keys = set()
        for confidence, detection_key, spoken_name, direction, distance in sorted(
            speech_candidates, key=lambda x: x[0], reverse=True
        ):
            if detection_key in used_keys:
                continue
            used_keys.add(detection_key)
            if spoken_this_frame >= self.max_audio_objects_per_frame:
                break
            if not self.is_stable_detection(detection_key):
                continue
            if not self.should_announce(detection_key):
                continue

            if direction == "in front":
                message = (
                    f"{spoken_name} {self._localized_direction(direction)}, "
                    f"{self._localized_distance(distance)}"
                )
            elif direction == "left":
                message = (
                    f"{spoken_name} {self._localized_direction(direction)}, "
                    f"{self._localized_distance(distance)}"
                )
            else:
                message = (
                    f"{spoken_name} {self._localized_direction(direction)}, "
                    f"{self._localized_distance(distance)}"
                )
            if distance == "very close":
                message = f"Warning. {message}"
            self.speak(message)
            spoken_this_frame += 1
        
        return detections

    def get_navigation_instruction(self, detections, frame_shape):
        """
        Build a simple navigation decision from detections.
        Returns tuple: (instruction, severity, lane_risk)
        """
        frame_height, frame_width = frame_shape[:2]
        lane_risk = {"left": 0.0, "center": 0.0, "right": 0.0}

        for det in detections:
            bbox = det["bbox"]
            class_name = det["class"]
            confidence = det["confidence"]

            x_center = (bbox[0] + bbox[2]) / 2.0
            if x_center < frame_width * 0.33:
                lane = "left"
            elif x_center > frame_width * 0.67:
                lane = "right"
            else:
                lane = "center"

            bbox_area = max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 1.0)
            frame_area = max(frame_width * frame_height, 1.0)
            size_ratio = bbox_area / frame_area

            base_risk = self.navigation_risk_weights.get(class_name, 1.0)
            distance_boost = 1.0 + min(size_ratio * 4.0, 2.0)
            lane_risk[lane] += base_risk * confidence * distance_boost

        left_risk = lane_risk["left"]
        center_risk = lane_risk["center"]
        right_risk = lane_risk["right"]

        if center_risk >= 4.5 and left_risk >= 4.0 and right_risk >= 4.0:
            return "STOP - obstacle very close", "danger", lane_risk

        if center_risk >= 3.0:
            if left_risk + 0.6 < right_risk:
                return "GO LEFT", "warning", lane_risk
            if right_risk + 0.6 < left_risk:
                return "GO RIGHT", "warning", lane_risk
            return "SLOW - path blocked ahead", "warning", lane_risk

        if left_risk + 0.4 < right_risk and left_risk < 3.0:
            return "GO LEFT", "safe", lane_risk
        if right_risk + 0.4 < left_risk and right_risk < 3.0:
            return "GO RIGHT", "safe", lane_risk
        return "CLEAN AREA GO STRAIGHT", "safe", lane_risk

    def maybe_announce_navigation(self, instruction):
        """Speak navigation instructions with cooldown."""
        now = time.time()
        if (
            instruction != self.last_navigation_message
            or now - self.last_navigation_time >= self.navigation_cooldown
        ):
            self.last_navigation_message = instruction
            self.last_navigation_time = now
            self.speak(self.translate_navigation(instruction))
    
    def draw_detections(self, frame, detections, instruction=None, severity="safe"):
        """Draw bounding boxes and labels on frame"""
        for det in detections:
            bbox = det['bbox'].astype(int)
            class_name = det.get('label', det['class'])
            confidence = det['confidence']
            direction = det['direction']
            
            # Draw bounding box
            color = (0, 255, 0) if det['distance'] != "very close" else (0, 0, 255)
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            
            # Draw label
            label = f"{class_name} {confidence:.2f} ({direction}, {det['distance']})"
            label = self._overlay_safe_text(label)
            cv2.putText(frame, label, (bbox[0], bbox[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        if instruction:
            if severity == "danger":
                nav_color = (0, 0, 255)
            elif severity == "warning":
                nav_color = (0, 165, 255)
            else:
                nav_color = (0, 255, 0)
            cv2.putText(
                frame,
                f"NAV: {instruction}",
                (10, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                nav_color,
                3
            )
        
        return frame
    
    def connect_to_camera(self):
        """Connect to ESP32-CAM or IP camera stream"""
        print(f"Connecting to camera at {self.camera_url}...")
        
        # For ESP32-CAM MJPEG stream
        stream = urllib.request.urlopen(self.camera_url)
        bytes_data = bytes()
        
        return stream, bytes_data
    
    def run_with_opencv_stream(self):
        """Run with OpenCV VideoCapture (for standard IP cameras)"""
        cap = cv2.VideoCapture(self.camera_url)
        
        if not cap.isOpened():
            print("Error: Could not connect to camera")
            return
        
        print("Connected! Starting vision aid system...")
        self.speak("Vision aid system started")
        self.running = True
        
        fps_counter = 0
        start_time = time.time()
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    print("Error: Failed to grab frame")
                    break
                
                # Run YOLO detection
                results = self.model(frame, imgsz=self.model_imgsz, verbose=False)
                
                # Process detections and generate audio feedback
                detections = self.process_detections(results, frame)
                instruction, severity, _ = self.get_navigation_instruction(detections, frame.shape)
                self.maybe_announce_navigation(instruction)
                
                # Draw detections on frame for monitoring
                annotated_frame = self.draw_detections(
                    frame.copy(), detections, instruction=instruction, severity=severity
                )
                
                # Calculate and display FPS
                fps_counter += 1
                if fps_counter % 30 == 0:
                    elapsed = time.time() - start_time
                    fps = fps_counter / elapsed
                    print(f"FPS: {fps:.2f} | Detections: {len(detections)}")
                
                # Display frame (comment out for headless operation)
                cv2.imshow('WVAB - Vision Aid System', annotated_frame)
                
                # Press 'q' to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        except KeyboardInterrupt:
            print("\nStopping vision aid system...")
        
        finally:
            self.running = False
            cap.release()
            cv2.destroyAllWindows()
            self.speak("Vision aid system stopped")
            self.stop_tts()
    
    def run_with_mjpeg_stream(self):
        """Run with MJPEG stream (for ESP32-CAM)"""
        print(f"Connecting to ESP32-CAM at {self.camera_url}...")
        
        try:
            stream = urllib.request.urlopen(self.camera_url, timeout=10)
        except Exception as e:
            print(f"Error connecting to camera: {e}")
            return
        
        print("Connected! Starting vision aid system...")
        self.speak("Vision aid system started")
        self.running = True
        
        bytes_data = bytes()
        fps_counter = 0
        start_time = time.time()
        
        try:
            while self.running:
                # Read MJPEG stream
                bytes_data += stream.read(1024)
                a = bytes_data.find(b'\xff\xd8')  # JPEG start
                b = bytes_data.find(b'\xff\xd9')  # JPEG end
                
                if a != -1 and b != -1:
                    jpg = bytes_data[a:b+2]
                    bytes_data = bytes_data[b+2:]
                    
                    # Decode JPEG
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # Run YOLO detection
                        results = self.model(frame, imgsz=self.model_imgsz, verbose=False)
                        
                        # Process detections
                        detections = self.process_detections(results, frame)
                        instruction, severity, _ = self.get_navigation_instruction(
                            detections, frame.shape
                        )
                        self.maybe_announce_navigation(instruction)
                        
                        # Draw detections
                        annotated_frame = self.draw_detections(
                            frame.copy(), detections, instruction=instruction, severity=severity
                        )
                        
                        # Calculate FPS
                        fps_counter += 1
                        if fps_counter % 30 == 0:
                            elapsed = time.time() - start_time
                            fps = fps_counter / elapsed
                            print(f"FPS: {fps:.2f} | Detections: {len(detections)}")
                        
                        # Display frame
                        cv2.imshow('WVAB - Vision Aid System', annotated_frame)
                        
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
        
        except KeyboardInterrupt:
            print("\nStopping vision aid system...")
        
        except Exception as e:
            print(f"Error in stream processing: {e}")
        
        finally:
            self.running = False
            stream.close()
            cv2.destroyAllWindows()
            self.speak("Vision aid system stopped")
            self.stop_tts()


def detect_languages_from_labels_file(path):
    langs = {"en"}
    if not path or not os.path.exists(path):
        return sorted(langs)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, dict):
                    for k in value.keys():
                        if isinstance(k, str) and k.strip():
                            langs.add(k.strip().lower())
    except Exception as exc:
        print(f"Warning: language detection from labels failed: {exc}")
    return sorted(langs)


def main():
    """Main function to run the vision aid server"""
    
    # Configuration
    CAMERA_URL = "http://192.168.4.1:81/stream"  # ESP32-CAM default
    # Alternative for IP Camera app: "http://192.168.1.100:8080/video"
    
    MODEL_PATH = "yolov8n.pt"  # Nano model (fastest)
    # Alternatives: "yolov8s.pt" (small), "yolov8m.pt" (medium)
    
    print("=" * 50)
    print("Wireless Vision-Aid for the Blind (WVAB)")
    print("=" * 50)
    print(f"Camera URL: {CAMERA_URL}")
    print(f"Model: {MODEL_PATH}")
    print("=" * 50)

    labels_path = "multilingual_labels.common.json"
    available_languages = detect_languages_from_labels_file(labels_path)

    print("\nSelect voice language:")
    for idx, lang in enumerate(available_languages, start=1):
        print(f"{idx}. {lang}")

    lang_choice = input(f"Enter choice (1-{len(available_languages)}): ").strip()
    try:
        lang_idx = int(lang_choice) - 1
    except ValueError:
        lang_idx = 0
    if lang_idx < 0 or lang_idx >= len(available_languages):
        lang_idx = 0
    language = available_languages[lang_idx]
    
    # Initialize server
    server = VisionAidServer(
        camera_url=CAMERA_URL,
        model_path=MODEL_PATH,
        language=language,
        labels_path=labels_path,
    )
    
    # Choose stream type based on camera
    print("\nSelect stream type:")
    print("1. MJPEG Stream (ESP32-CAM)")
    print("2. Standard Stream (IP Camera App)")
    
    choice = input("Enter choice (1/2): ").strip()
    
    if choice == "1":
        server.run_with_mjpeg_stream()
    else:
        server.run_with_opencv_stream()


if __name__ == "__main__":
    main()
