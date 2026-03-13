# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 

import sys
import socket
import time
import os
import json
import cv2
import numpy as np
from offline_utils import configure_offline_env, ensure_local_model

OFFLINE_MODE = configure_offline_env()
NONINTERACTIVE = os.environ.get("WVAB_TEST_NONINTERACTIVE", "0") == "1"

class WVABTester:
    """Comprehensive testing utility for WVAB system."""

    def __init__(self):
        self.results = {}
        # Real-world priority objects for blind navigation tests.
        self.real_objects = {
            "person": "Person",
            "car": "Car",
            "truck": "Truck",
            "bus": "Bus",
            "motorcycle": "Motorcycle",
            "bicycle": "Bicycle",
            "chair": "Chair",
            "table": "Table",
            "bench": "Bench",
            "door": "Door",
            "stairs": "Stairs",
            "traffic light": "Traffic light",
            "stop sign": "Stop sign",
            "dog": "Dog",
            "cat": "Cat",
        }

    def print_header(self, text):
        print("\n" + "=" * 60)
        print(f"  {text}")
        print("=" * 60)

    def print_result(self, test_name, passed, message=""):
        status = "PASS" if passed else "FAIL"
        self.results[test_name] = passed
        print(f"{status} | {test_name}")
        if message:
            print(f"       {message}")

    def test_python_version(self):
        self.print_header("Testing Python Version")
        version = sys.version_info
        is_valid = version.major == 3 and version.minor >= 8
        self.print_result(
            "Python Version",
            is_valid,
            f"Version: {version.major}.{version.minor}.{version.micro}",
        )
        return is_valid

    def test_opencv(self):
        self.print_header("Testing OpenCV")
        try:
            version = cv2.__version__
            self.print_result("OpenCV Import", True, f"Version: {version}")

            cap = cv2.VideoCapture(0)
            has_camera = cap.isOpened()
            if has_camera:
                ret, frame = cap.read()
                has_camera = ret and frame is not None
            cap.release()

            msg = "Built-in webcam accessible" if has_camera else "No webcam detected"
            self.print_result("Webcam Access", has_camera, msg)
            return True
        except Exception as e:
            self.print_result("OpenCV Import", False, str(e))
            return False

    def test_yolo(self):
        self.print_header("Testing YOLOv8")
        try:
            from ultralytics import YOLO

            self.print_result("Ultralytics Import", True)
            try:
                print("Loading YOLOv8 model (offline)...")
                model = YOLO(ensure_local_model("yolov8n.pt", offline=OFFLINE_MODE))
                self.print_result("YOLO Model Load", True, "yolov8n.pt loaded successfully")

                dummy_image = np.zeros((640, 480, 3), dtype=np.uint8)
                model(dummy_image, verbose=False)
                self.print_result("YOLO Inference", True, "Model can perform detection")
                return True
            except Exception as e:
                self.print_result("YOLO Model Load", False, str(e))
                return False
        except Exception as e:
            self.print_result("Ultralytics Import", False, str(e))
            return False

    def test_pyttsx3(self):
        self.print_header("Testing Text-to-Speech")
        try:
            import pyttsx3

            self.print_result("pyttsx3 Import", True)
            try:
                engine = pyttsx3.init()
                self.print_result("TTS Engine Init", True)

                print("Testing audio output (you should hear 'Test')...")
                engine.say("Test")
                engine.runAndWait()
                if NONINTERACTIVE:
                    self.print_result("Audio Output", True, "Skipped (non-interactive)")
                    return True
                user_input = input("Did you hear the audio? (y/n): ").strip().lower()
                heard_audio = user_input == "y"
                self.print_result("Audio Output", heard_audio)
                return heard_audio
            except Exception as e:
                self.print_result("TTS Engine Init", False, str(e))
                return False
        except Exception as e:
            self.print_result("pyttsx3 Import", False, str(e))
            return False

    def test_network(self):
        self.print_header("Testing Network")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            self.print_result("Network Connection", True, f"Local IP: {local_ip}")
            return True
        except Exception:
            self.print_result("Network Connection", False, "No network connection")
            return False

    def test_udp_security_primitives(self):
        self.print_header("Testing UDP Security Primitives")
        try:
            from udp_streaming import _validate_aes_key
        except Exception as e:
            self.print_result("UDP Import", False, str(e))
            return False

        try:
            _validate_aes_key(b"\x00" * 16)
            _validate_aes_key(b"\x00" * 24)
            _validate_aes_key(b"\x00" * 32)
            self.print_result("AES Key Lengths", True, "16/24/32 bytes accepted")
        except Exception as e:
            self.print_result("AES Key Lengths", False, str(e))
            return False

        try:
            _validate_aes_key(b"\x00" * 10)
            self.print_result("AES Invalid Length", False, "Invalid length accepted")
            return False
        except ValueError:
            self.print_result("AES Invalid Length", True, "Invalid length rejected")
            return True
        except Exception as e:
            self.print_result("AES Invalid Length", False, str(e))
            return False

    def test_camera_connection(self, camera_url):
        self.print_header(f"Testing Camera: {camera_url}")
        try:
            cap = cv2.VideoCapture(camera_url)

            if not cap.isOpened():
                self.print_result("Camera Connection", False, "Could not connect")
                return False

            self.print_result("Camera Connection", True, "Connected successfully")

            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                self.print_result(
                    "Frame Capture",
                    True,
                    f"Frame size: {frame.shape[1]}x{frame.shape[0]}",
                )
                return True

            self.print_result("Frame Capture", False, "Could not read frame")
            return False
        except Exception as e:
            self.print_result("Camera Connection", False, str(e))
            return False

    def test_pc_webcam_real(self, camera_index=0, sample_seconds=5, min_frames=20):
        """Run a real webcam test with live preview and performance checks."""
        self.print_header("Testing PC Webcam (Real Test)")

        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_index)

        if not cap.isOpened():
            self.print_result("PC Webcam Connection", False, "Could not open webcam")
            return False

        self.print_result("PC Webcam Connection", True, f"Webcam index {camera_index} opened")
        print("Starting live preview. Press 'q' to stop early...")

        good_frames = 0
        total_brightness = 0.0
        frame_width = 0
        frame_height = 0
        start_time = time.time()

        while time.time() - start_time < sample_seconds:
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            if frame_width == 0:
                frame_height, frame_width = frame.shape[:2]

            good_frames += 1
            total_brightness += float(frame.mean())

            cv2.imshow("WVAB Webcam Test - Press q to exit", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        elapsed = max(time.time() - start_time, 1e-6)
        cap.release()
        cv2.destroyAllWindows()

        if good_frames == 0:
            self.print_result("PC Webcam Frame Capture", False, "No frames captured")
            return False

        avg_fps = good_frames / elapsed
        avg_brightness = total_brightness / good_frames

        frame_ok = good_frames >= min_frames
        fps_ok = avg_fps >= 5.0
        brightness_ok = avg_brightness > 5.0

        self.print_result(
            "PC Webcam Frame Capture",
            frame_ok,
            f"Captured {good_frames} frames in {elapsed:.1f}s ({frame_width}x{frame_height})",
        )
        self.print_result("PC Webcam FPS", fps_ok, f"Average FPS: {avg_fps:.1f}")
        self.print_result(
            "PC Webcam Visibility",
            brightness_ok,
            f"Average brightness: {avg_brightness:.1f}",
        )

        user_input = input("Did you see the live webcam preview clearly? (y/n): ").strip().lower()
        preview_ok = user_input == "y"
        self.print_result("PC Webcam Live Preview", preview_ok)

        return frame_ok and fps_ok and brightness_ok and preview_ok

    def test_camera_gui_real(
        self,
        camera_source=0,
        language="en",
        labels_path="multilingual_labels.common.json",
    ):
        """Launch real GUI camera test and keep running until user closes it."""
        self.print_header("Testing Camera GUI (Real Continuous Test)")
        try:
            from camera_gui import run_camera_gui

            print("Opening real camera GUI with ML detection...")
            print("Camera will stay ON until you close the GUI window.")
            summary = run_camera_gui(
                camera_source=camera_source,
                model_path="yolov8n.pt",
                language=language,
                labels_path=labels_path,
            )

            camera_started = bool(summary.get("camera_started"))
            frames = int(summary.get("frames", 0))
            model_loaded = bool(summary.get("model_loaded"))
            defined_objects = int(summary.get("defined_objects", len(self.real_objects)))
            detected_types = int(summary.get("detected_types", 0))
            detected_total = int(summary.get("detected_total", 0))

            self.print_result("Camera GUI Session", camera_started, "GUI closed by user")
            self.print_result("Camera GUI Language", True, f"Language: {language}")
            self.print_result("Camera GUI Frame Stream", frames > 0, f"Total frames: {frames}")
            self.print_result("Camera GUI ML Model", model_loaded, "YOLO model status")
            self.print_result(
                "Camera GUI Real Object Definitions",
                True,
                f"{defined_objects} real objects defined",
            )
            self.print_result(
                "Camera GUI Real Object Detection",
                detected_types > 0,
                f"Detected types: {detected_types}, detections: {detected_total}",
            )
            return camera_started and frames > 0 and model_loaded
        except Exception as e:
            self.print_result("Camera GUI Session", False, str(e))
            return False
    def test_complete_pipeline(self, camera_source=0):
        self.print_header("Testing Complete Pipeline")
        try:
            from ultralytics import YOLO
            import pyttsx3

            print("Initializing components...")
            model = YOLO(ensure_local_model("yolov8n.pt", offline=OFFLINE_MODE))
            pyttsx3.init()
            cap = cv2.VideoCapture(camera_source)

            if not cap.isOpened():
                self.print_result("Pipeline Test", False, "Camera not accessible")
                return False

            print("Running detection on 10 frames...")
            detections = 0
            real_object_counts = {}
            real_examples = {}
            processed_frames = 0
            model_names = model.names if hasattr(model, "names") else {}
            if isinstance(model_names, dict):
                defined_count = len(model_names)
            else:
                defined_count = len(list(model_names))

            for _ in range(10):
                ret, frame = cap.read()
                if not ret:
                    break
                processed_frames += 1
                frame_h, frame_w = frame.shape[:2]
                results = model(frame, verbose=False)
                for result in results:
                    detections += len(result.boxes)
                    for box in result.boxes:
                        class_id = int(box.cls[0])
                        class_name = model.names[class_id]

                        confidence = float(box.conf[0])
                        if confidence < 0.4:
                            continue

                        bbox = box.xyxy[0].cpu().numpy()
                        x_center = (bbox[0] + bbox[2]) / 2.0
                        bbox_area = max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 1.0)
                        frame_area = max(frame_w * frame_h, 1.0)
                        size_ratio = bbox_area / frame_area

                        if x_center < frame_w * 0.33:
                            direction = "left"
                        elif x_center > frame_w * 0.67:
                            direction = "right"
                        else:
                            direction = "center"

                        if size_ratio > 0.3:
                            distance = "very close"
                        elif size_ratio > 0.15:
                            distance = "close"
                        else:
                            distance = "ahead"

                        real_object_counts[class_name] = real_object_counts.get(class_name, 0) + 1
                        if class_name not in real_examples:
                            pretty_name = class_name.replace("_", " ").strip().title()
                            real_examples[class_name] = (
                                f"{pretty_name}: {direction}, {distance}, conf {confidence:.2f}"
                            )

            cap.release()

            real_objects_detected = len(real_object_counts) > 0
            self.print_result(
                "Pipeline Test",
                processed_frames > 0,
                f"Processed {processed_frames} frames, {detections} total detections",
            )
            self.print_result(
                "Real Object Definitions",
                True,
                f"{defined_count} objects available in the loaded YOLO model",
            )
            self.print_result(
                "Real Object Detection",
                real_objects_detected,
                f"Detected {len(real_object_counts)} defined object types",
            )

            if real_objects_detected:
                print("\nDetected real objects:")
                for class_name, count in sorted(
                    real_object_counts.items(), key=lambda x: x[1], reverse=True
                ):
                    pretty_name = class_name.replace("_", " ").strip().title()
                    print(f"  - {pretty_name} ({class_name}): {count} detections")
                    print(f"    Example: {real_examples[class_name]}")
            else:
                print("\nNo defined real objects were detected.")
                print("Show common objects (person/chair/car etc.) to the camera and test again.")

            return True
        except Exception as e:
            self.print_result("Pipeline Test", False, str(e))
            return False

    def generate_report(self):
        self.print_header("Test Summary")
        total = len(self.results)
        passed = sum(1 for v in self.results.values() if v)

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed / total * 100):.1f}%")

        if passed == total:
            print("\nPASS: All tests passed. System is ready.")
        else:
            print("\nFAIL: Some tests failed. Check the results above.")
            print("\nFailed tests:")
            for test, result in self.results.items():
                if not result:
                    print(f"  - {test}")


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
    except Exception:
        pass
    return sorted(langs)


def main():
    print("=" * 60)
    print("  WVAB System Diagnostic Tool")
    print("=" * 60)

    tester = WVABTester()

    print("\n[1/7] Testing Python...")
    tester.test_python_version()

    print("\n[2/7] Testing OpenCV...")
    tester.test_opencv()

    print("\n[3/7] Testing YOLOv8...")
    tester.test_yolo()

    print("\n[4/7] Testing Text-to-Speech...")
    tester.test_pyttsx3()

    print("\n[5/8] Testing Network...")
    tester.test_network()

    print("\n[6/8] Testing UDP Security...")
    tester.test_udp_security_primitives()

    print("\n[7/8] Testing Camera...")
    print("\nSelect camera type:")
    print("1. PC webcam GUI (real + ML, stays ON until close)")
    print("2. ESP32-CAM (192.168.4.1)")
    print("3. IP Camera (custom URL)")
    print("4. Skip camera test")

    if NONINTERACTIVE:
        choice = "4"
    else:
        choice = input("\nEnter choice (1-4): ").strip()
    url = ""
    labels_path = "multilingual_labels.common.json"

    if choice == "1":
        available_languages = detect_languages_from_labels_file(labels_path)
        print("\nSelect test language:")
        for idx, lang in enumerate(available_languages, start=1):
            print(f"{idx}. {lang}")
        lang_choice = input(f"Enter choice (1-{len(available_languages)}): ").strip()
        try:
            lang_idx = int(lang_choice) - 1
        except ValueError:
            lang_idx = 0
        if lang_idx < 0 or lang_idx >= len(available_languages):
            lang_idx = 0
        test_language = available_languages[lang_idx]
        tester.test_camera_gui_real(0, language=test_language, labels_path=labels_path)
    elif choice == "2":
        tester.test_camera_connection("http://192.168.4.1:81/stream")
    elif choice == "3":
        url = input("Enter camera URL: ").strip()
        tester.test_camera_connection(url)
    else:
        print("Skipping camera test")

    print("\n[8/8] Testing Complete Pipeline...")
    if choice == "1":
        print("Skipping separate pipeline test: GUI mode already runs real-time ML detection.")
    elif choice in ["2", "3"] and (not NONINTERACTIVE and input("Run pipeline test? (y/n): ").strip().lower() == "y"):
        if choice == "2":
            tester.test_complete_pipeline("http://192.168.4.1:81/stream")
        elif choice == "3":
            tester.test_complete_pipeline(url)
    else:
        print("Skipping pipeline test")

    tester.generate_report()

    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
