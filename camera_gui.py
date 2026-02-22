"""
WVAB Camera GUI
Real webcam preview with YOLO object detection and real diagnostics.
"""

import os
import time
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import queue
import threading
import subprocess
import unicodedata
from collections import deque

import cv2
import numpy as np
from PIL import Image, ImageTk
from PIL import ImageDraw, ImageFont
import pyttsx3

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None


class CameraGUI:
    def __init__(
        self,
        root,
        camera_source=0,
        model_path="yolov8n.pt",
        language="en",
        labels_path="multilingual_labels.common.json",
    ):
        self.root = root
        self.root.title("WVAB Camera GUI - Real Test + ML")
        self.root.geometry("1120x760")

        self.model_path = model_path
        self.language = (language or "en").strip().lower()
        self.speech_language = self.language
        self.labels_path = labels_path
        self.model = None
        self.ml_enabled = False
        self.audio_enabled = True
        self.audio_cooldown = 0.25
        self.last_audio_announcement = {}
        self.max_audio_objects_per_frame = 1
        self.stability_window = 4
        self.min_stable_frames = 1
        self.recent_detection_keys = deque(maxlen=self.stability_window)
        self.movement_cooldown = 1.2
        self.last_movement_announcement = ""
        self.last_movement_time = 0.0
        self.last_spoken_gui_text = ""
        self.gui_speech_cooldown = 0.25
        self.last_gui_speech_time = 0.0
        self.default_focal_length_px = 700.0
        self.known_object_width_m = {
            "person": 0.45,
            "car": 1.8,
            "truck": 2.5,
            "bus": 2.6,
            "bicycle": 0.6,
            "motorcycle": 0.8,
            "chair": 0.5,
            "door": 0.9,
            "stop sign": 0.75,
            "traffic light": 0.3,
        }

        self.object_labels = {}
        self.multilingual_labels = self._load_multilingual_labels(self.labels_path)
        self.available_languages = self._detect_available_languages(self.multilingual_labels)
        if self.language not in self.available_languages:
            self.language = "en"
        self.speech_language = self._resolve_speech_language(self.language)

        self.cap = None
        self.camera_running = False
        self.current_frame = None
        self.video_writer = None
        self.recording = False

        self.total_frames = 0
        self.detected_counts = {}
        self.last_detect_text = "No real objects yet"

        self.last_loop_time = time.time()
        self.last_fps = 0.0

        self.test_active = False
        self.test_start = 0.0
        self.test_frames = 0
        self.test_brightness_sum = 0.0
        self.test_blur_sum = 0.0
        self.test_detected_types = set()

        self.session_summary = {
            "frames": 0,
            "model_loaded": False,
            "defined_objects": 0,
            "detected_types": 0,
            "detected_total": 0,
            "camera_started": False,
            "audio_enabled": True,
        }

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
        self.overlay_font = self._load_overlay_font()

        self._build_ui()
        self.source_var.set(str(camera_source))
        self._load_model()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(top, text="Camera Source (0 / URL):").pack(side=tk.LEFT)
        self.source_var = tk.StringVar(value="0")
        tk.Entry(top, textvariable=self.source_var, width=35).pack(side=tk.LEFT, padx=6)

        tk.Button(top, text="Start Camera", command=self.start_camera).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Stop Camera", command=self.stop_camera).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Real Test (5s)", command=self.start_real_test).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Snapshot", command=self.save_snapshot).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Record", command=self.toggle_recording).pack(side=tk.LEFT, padx=4)
        self.ml_btn = tk.Button(top, text="ML: OFF", command=self.toggle_ml)
        self.ml_btn.pack(side=tk.LEFT, padx=4)
        self.audio_btn = tk.Button(top, text="Audio: ON", command=self.toggle_audio)
        self.audio_btn.pack(side=tk.LEFT, padx=4)
        tk.Label(top, text="Lang:").pack(side=tk.LEFT, padx=(10, 3))
        self.lang_var = tk.StringVar(value=self.language)
        self.lang_menu = tk.OptionMenu(top, self.lang_var, *self.available_languages, command=self.set_language)
        self.lang_menu.pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="Exit", command=self.on_close).pack(side=tk.RIGHT, padx=4)

        body = tk.Frame(self.root)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        self.preview = tk.Label(body, bg="black", width=960, height=540)
        self.preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        side_panel = tk.Frame(body, width=220)
        side_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=8)
        tk.Label(side_panel, text="Detected Objects", font=("Segoe UI", 10, "bold")).pack(
            anchor="w", pady=(0, 6)
        )
        self.detect_box = tk.Text(side_panel, width=28, height=30, state=tk.DISABLED)
        self.detect_box.pack(fill=tk.Y, expand=True)

        bottom = tk.Frame(self.root)
        bottom.pack(fill=tk.X, padx=10, pady=8)
        self.status_var = tk.StringVar(value="Idle")
        self.metrics_var = tk.StringVar(value="FPS: - | Brightness: - | Blur: -")
        self.object_var = tk.StringVar(value="Objects: No real objects yet")
        tk.Label(bottom, textvariable=self.status_var, anchor="w").pack(fill=tk.X)
        tk.Label(bottom, textvariable=self.metrics_var, anchor="w").pack(fill=tk.X)
        tk.Label(bottom, textvariable=self.object_var, anchor="w").pack(fill=tk.X)

    def _load_model(self):
        if YOLO is None:
            self.status_var.set("Ultralytics not installed. ML disabled.")
            self.ml_enabled = False
            self.ml_btn.configure(text="ML: OFF")
            return
        try:
            self.model = YOLO(self.model_path)
            self.ml_enabled = True
            self.ml_btn.configure(text="ML: ON")
            self.object_labels = self._build_object_labels()
            self.status_var.set(f"ML model loaded: {self.model_path}")
            self.session_summary["model_loaded"] = True
            self.session_summary["defined_objects"] = len(self.object_labels)
        except Exception as exc:
            self.model = None
            self.ml_enabled = False
            self.ml_btn.configure(text="ML: OFF")
            self.status_var.set(f"Model load failed: {exc}")

    def _load_multilingual_labels(self, path):
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

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
        return "en"

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
        lang = (language or "en").strip().lower()
        if lang not in self.available_languages:
            lang = "en"
        self.language = lang
        self.speech_language = self._resolve_speech_language(lang)
        if self.speech_language != self.language:
            self.status_var.set(
                f"Language: {self.language}, speech fallback: {self.speech_language} (voice not installed)"
            )
        else:
            self.status_var.set(f"Language set to: {self.language}")

    def translate_class_name(self, class_name, fallback_name):
        entry = self.multilingual_labels.get(class_name)
        if isinstance(entry, dict):
            return entry.get(self.language, entry.get("en", fallback_name))
        return fallback_name

    def _localized_direction(self, direction):
        phrases = self.multilingual_labels.get("__phrases__", {})
        if isinstance(phrases, dict):
            lang_map = phrases.get(self.language, {})
            if isinstance(lang_map, dict):
                maybe = lang_map.get(direction)
                if isinstance(maybe, str) and maybe.strip():
                    return maybe
        dmap = {
            "en": {"left": "in left", "right": "in right", "in front": "in front"},
            "ru": {"left": "слева", "right": "справа", "in front": "спереди"},
        }
        table = dmap.get(self.language, dmap["en"])
        return table.get(direction, direction)

    def _localized_distance(self, distance):
        phrases = self.multilingual_labels.get("__phrases__", {})
        if isinstance(phrases, dict):
            lang_map = phrases.get(self.language, {})
            if isinstance(lang_map, dict):
                maybe = lang_map.get(distance)
                if isinstance(maybe, str) and maybe.strip():
                    return maybe
        dmap = {
            "en": {"too far": "too far", "close": "close", "very close": "very close"},
            "ru": {"too far": "далеко", "close": "близко", "very close": "очень близко"},
        }
        table = dmap.get(self.language, dmap["en"])
        return table.get(distance, distance)

    def _build_localized_object_phrase(self, object_name, direction, distance):
        if isinstance(distance, tuple):
            distance_label, distance_m = distance
        else:
            distance_label, distance_m = distance, None
        text = f"{object_name} {self._localized_direction(direction)} {self._localized_distance(distance_label)}"
        if distance_m is not None:
            text = f"{text}, about {distance_m:.1f} meters"
        return text

    def _overlay_safe_text(self, text):
        try:
            text.encode("ascii")
            return text
        except UnicodeEncodeError:
            normalized = unicodedata.normalize("NFKD", text)
            ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
            return ascii_text if ascii_text.strip() else "object"

    def _load_overlay_font(self):
        font_candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/seguiemj.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
        ]
        for path in font_candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, 18)
                except Exception:
                    continue
        try:
            return ImageFont.load_default()
        except Exception:
            return None

    def _draw_unicode_text(self, frame, text, x, y, color_bgr):
        if self.overlay_font is None:
            cv2.putText(frame, self._overlay_safe_text(text), (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 2)
            return frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        draw = ImageDraw.Draw(img)
        color_rgb = (int(color_bgr[2]), int(color_bgr[1]), int(color_bgr[0]))
        draw.text((x, y), text, font=self.overlay_font, fill=color_rgb)
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    def _build_object_labels(self):
        labels = {}
        names = self.model.names if self.model is not None else {}
        if isinstance(names, dict):
            for value in names.values():
                key = str(value)
                labels[key] = key.replace("_", " ").strip().title()
        else:
            for value in names:
                key = str(value)
                labels[key] = key.replace("_", " ").strip().title()
        return labels

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
            # If requested speech language isn't available, we already fallback to EN.
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
        engine.setProperty("rate", 190)
        engine.setProperty("volume", 1.0)
        engine.say(text)
        engine.runAndWait()
        engine.stop()

    def _tts_worker(self):
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
            except Exception as exc:
                print(f"[AUDIO][GUI] speech failed: {exc}")
                time.sleep(0.05)

    def speak(self, text):
        if not self.audio_enabled:
            return
        with self.speech_lock:
            self.priority_speech = None
            self.latest_speech = text
            self.speech_event.set()

    def speak_priority(self, text):
        if not self.audio_enabled:
            return
        with self.speech_lock:
            self.priority_speech = text
            self.speech_event.set()

    def should_announce(self, announcement_key):
        now = time.time()
        last_time = self.last_audio_announcement.get(announcement_key, 0.0)
        if now - last_time >= self.audio_cooldown:
            self.last_audio_announcement[announcement_key] = now
            return True
        return False

    def is_stable_detection(self, detection_key):
        count = 0
        for frame_keys in self.recent_detection_keys:
            if detection_key in frame_keys:
                count += 1
        return count >= self.min_stable_frames

    def toggle_audio(self):
        self.audio_enabled = not self.audio_enabled
        self.audio_btn.configure(text=f"Audio: {'ON' if self.audio_enabled else 'OFF'}")
        self.session_summary["audio_enabled"] = self.audio_enabled
        self.status_var.set(f"Audio guidance {'enabled' if self.audio_enabled else 'disabled'}")

    def toggle_ml(self):
        if self.model is None:
            messagebox.showwarning("ML", "Model is not loaded.")
            return
        self.ml_enabled = not self.ml_enabled
        self.ml_btn.configure(text=f"ML: {'ON' if self.ml_enabled else 'OFF'}")
        self.status_var.set(f"ML detection {'enabled' if self.ml_enabled else 'disabled'}")

    def parse_source(self):
        source_text = self.source_var.get().strip()
        if source_text.isdigit():
            return int(source_text)
        return source_text

    def start_camera(self):
        if self.camera_running:
            self.status_var.set("Camera already running")
            return

        source = self.parse_source()
        self.cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(source)

        if not self.cap.isOpened():
            messagebox.showerror("Camera Error", f"Could not open camera source: {source}")
            self.status_var.set("Camera open failed")
            return

        self.camera_running = True
        self.session_summary["camera_started"] = True
        self.status_var.set(f"Camera started: {source}")
        self.last_loop_time = time.time()
        self.update_frame()

    def stop_camera(self):
        self.camera_running = False
        self.stop_recording_if_needed()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.preview.configure(image="")
        self.status_var.set("Camera stopped")

    def _object_direction(self, bbox, frame_w):
        x_center = (bbox[0] + bbox[2]) / 2.0
        if x_center < frame_w * 0.33:
            return "left"
        if x_center > frame_w * 0.67:
            return "right"
        return "in front"

    def _estimate_distance_m(self, class_name, bbox):
        object_width_m = self.known_object_width_m.get(class_name)
        if object_width_m is None:
            return None
        bbox_width_px = max(float(bbox[2] - bbox[0]), 1.0)
        distance_m = (object_width_m * self.default_focal_length_px) / bbox_width_px
        return float(np.clip(distance_m, 0.2, 20.0))

    def _object_distance(self, class_name, bbox, frame_w, frame_h):
        area = max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 1.0)
        frame_area = max(frame_w * frame_h, 1.0)
        ratio = area / frame_area
        distance_m = self._estimate_distance_m(class_name, bbox)
        if distance_m is not None:
            if distance_m <= 1.0:
                return "very close", distance_m
            if distance_m <= 2.5:
                return "close", distance_m
            return "too far", distance_m
        if ratio > 0.3:
            return "very close", None
        if ratio > 0.15:
            return "close", None
        return "too far", None

    def _detect_real_objects(self, frame):
        if not self.ml_enabled or self.model is None:
            return frame, []

        detections = []
        frame_keys = set()
        speech_candidates = []
        frame_h, frame_w = frame.shape[:2]
        results = self.model(frame, imgsz=416, verbose=False)
        for result in results:
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf < 0.4:
                    continue

                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]

                bbox = box.xyxy[0].cpu().numpy().astype(int)
                direction = self._object_direction(bbox, frame_w)
                distance, distance_m = self._object_distance(class_name, bbox, frame_w, frame_h)
                default_name = self.object_labels.get(
                    class_name, class_name.replace("_", " ").strip().title()
                )
                pretty_name = self.translate_class_name(class_name, default_name)
                distance_suffix = f", {distance_m:.1f}m" if distance_m is not None else ""

                label = (
                    f"{pretty_name} {conf:.2f} "
                    f"{self._localized_direction(direction)} {self._localized_distance(distance)}{distance_suffix}"
                )
                color = (0, 0, 255) if distance == "very close" else (0, 255, 0)
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                frame = self._draw_unicode_text(
                    frame,
                    label,
                    int(bbox[0]),
                    int(max(20, bbox[1] - 20)),
                    color,
                )

                detections.append((class_name, pretty_name, direction, distance, conf, bbox, distance_m))
                self.detected_counts[class_name] = self.detected_counts.get(class_name, 0) + 1
                self.test_detected_types.add(class_name)

                detection_key = f"{class_name}_{direction}_{distance}"
                frame_keys.add(detection_key)
                speech_candidates.append((conf, detection_key, pretty_name, direction, distance, distance_m))

        self.recent_detection_keys.append(frame_keys)

        spoken_this_frame = 0
        used_keys = set()
        for conf, detection_key, pretty_name, direction, distance, distance_m in sorted(
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
            # GUI speech is handled from the exact displayed text in update_frame().
            spoken_this_frame += 1

        return frame, detections

    def maybe_speak_display_text(self, text):
        if not self.audio_enabled or not text or text == "No real objects yet":
            return
        now = time.time()
        if text != self.last_spoken_gui_text or now - self.last_gui_speech_time >= self.gui_speech_cooldown:
            self.last_spoken_gui_text = text
            self.last_gui_speech_time = now
            self.speak(text)

    def _get_movement_instruction(self, detections, frame_shape):
        frame_h, frame_w = frame_shape[:2]
        lane_risk = {"left": 0.0, "center": 0.0, "right": 0.0}

        for det in detections:
            bbox = det[5]
            conf = det[4]
            x_center = (bbox[0] + bbox[2]) / 2.0
            if x_center < frame_w * 0.33:
                lane = "left"
            elif x_center > frame_w * 0.67:
                lane = "right"
            else:
                lane = "center"

            area = max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 1.0)
            frame_area = max(frame_w * frame_h, 1.0)
            size_ratio = area / frame_area
            lane_risk[lane] += conf * (1.0 + min(size_ratio * 4.0, 2.0))

        left = lane_risk["left"]
        center = lane_risk["center"]
        right = lane_risk["right"]

        if center >= 3.0 and left >= 2.5 and right >= 2.5:
            return "Stop. Obstacles very close"
        if center >= 2.0:
            if left + 0.3 < right:
                return "Move left"
            if right + 0.3 < left:
                return "Move right"
            return "Slow down"
        if left + 0.2 < right:
            return "Move left"
        if right + 0.2 < left:
            return "Move right"
        return "Move straight"

    def maybe_announce_movement(self, detections, frame_shape):
        if not self.audio_enabled:
            return
        instruction = self._get_movement_instruction(detections, frame_shape)
        now = time.time()
        if (
            instruction != self.last_movement_announcement
            or now - self.last_movement_time >= self.movement_cooldown
        ):
            self.last_movement_announcement = instruction
            self.last_movement_time = now
            self.speak(instruction)

    def _refresh_detect_box(self):
        lines = []
        if not self.detected_counts:
            lines.append("No objects detected")
        else:
            for key, value in sorted(self.detected_counts.items(), key=lambda x: x[1], reverse=True):
                default_name = self.object_labels.get(
                    key, key.replace("_", " ").strip().title()
                )
                pretty_name = self.translate_class_name(key, default_name)
                lines.append(f"{pretty_name} ({key}): {value}")

        self.detect_box.configure(state=tk.NORMAL)
        self.detect_box.delete("1.0", tk.END)
        self.detect_box.insert(tk.END, "\n".join(lines))
        self.detect_box.configure(state=tk.DISABLED)

    def update_frame(self):
        if not self.camera_running or self.cap is None:
            return

        ok, frame = self.cap.read()
        if not ok or frame is None:
            self.status_var.set("Frame read failed")
            self.root.after(50, self.update_frame)
            return

        self.total_frames += 1
        self.current_frame = frame.copy()

        if self.recording and self.video_writer is not None:
            self.video_writer.write(frame)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = float(gray.mean())
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        frame, detections = self._detect_real_objects(frame)
        if detections:
            first = detections[0]
            self.last_detect_text = self._build_localized_object_phrase(first[1], first[2], (first[3], first[6]))
            self.maybe_speak_display_text(self.last_detect_text)
        else:
            self.last_detect_text = "No real objects yet"
        self._refresh_detect_box()

        if self.test_active:
            self.test_frames += 1
            self.test_brightness_sum += brightness
            self.test_blur_sum += blur_score
            self._finish_test_if_needed()

        now = time.time()
        dt = max(now - self.last_loop_time, 1e-6)
        self.last_fps = 1.0 / dt
        self.last_loop_time = now

        display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        display = cv2.resize(display, (900, 540))
        image = Image.fromarray(display)
        image_tk = ImageTk.PhotoImage(image=image)
        self.preview.image_tk = image_tk
        self.preview.configure(image=image_tk)

        self.metrics_var.set(
            f"FPS: {self.last_fps:.1f} | Brightness: {brightness:.1f} | Blur: {blur_score:.1f}"
        )
        self.object_var.set(f"Objects: {self.last_detect_text}")
        self.root.after(15, self.update_frame)

    def save_snapshot(self):
        if self.current_frame is None:
            messagebox.showwarning("Snapshot", "No frame available. Start camera first.")
            return

        default_name = f"snapshot_{int(time.time())}.jpg"
        file_path = filedialog.asksaveasfilename(
            title="Save Snapshot",
            initialfile=default_name,
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"), ("All files", "*.*")],
        )
        if not file_path:
            return

        cv2.imwrite(file_path, self.current_frame)
        self.status_var.set(f"Snapshot saved: {os.path.basename(file_path)}")

    def toggle_recording(self):
        if not self.camera_running or self.current_frame is None:
            messagebox.showwarning("Recording", "Start camera before recording.")
            return

        if self.recording:
            self.stop_recording_if_needed()
            self.status_var.set("Recording stopped")
            return

        frame_h, frame_w = self.current_frame.shape[:2]
        default_name = f"recording_{int(time.time())}.avi"
        file_path = filedialog.asksaveasfilename(
            title="Save Recording",
            initialfile=default_name,
            defaultextension=".avi",
            filetypes=[("AVI", "*.avi"), ("MP4", "*.mp4"), ("All files", "*.*")],
        )
        if not file_path:
            return

        ext = os.path.splitext(file_path)[1].lower()
        fourcc = cv2.VideoWriter_fourcc(*("XVID" if ext == ".avi" else "mp4v"))
        self.video_writer = cv2.VideoWriter(file_path, fourcc, 20.0, (frame_w, frame_h))
        if not self.video_writer.isOpened():
            self.video_writer = None
            messagebox.showerror("Recording", "Could not start video writer.")
            return

        self.recording = True
        self.status_var.set(f"Recording started: {os.path.basename(file_path)}")

    def stop_recording_if_needed(self):
        self.recording = False
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None

    def start_real_test(self):
        if not self.camera_running:
            self.start_camera()
            if not self.camera_running:
                return

        self.test_active = True
        self.test_start = time.time()
        self.test_frames = 0
        self.test_brightness_sum = 0.0
        self.test_blur_sum = 0.0
        self.test_detected_types = set()
        self.status_var.set("Running real camera+ML test for 5 seconds...")

    def _finish_test_if_needed(self):
        if not self.test_active:
            return

        elapsed = time.time() - self.test_start
        if elapsed < 5.0:
            return

        self.test_active = False
        if self.test_frames <= 0:
            messagebox.showerror("Real Test Result", "FAIL: No frames captured.")
            self.status_var.set("Real test failed")
            return

        fps = self.test_frames / max(elapsed, 1e-6)
        avg_brightness = self.test_brightness_sum / self.test_frames
        avg_blur = self.test_blur_sum / self.test_frames
        detected_types = len(self.test_detected_types)

        pass_frames = self.test_frames >= 20
        pass_fps = fps >= 5.0
        pass_brightness = avg_brightness > 5.0
        pass_focus = avg_blur > 20.0
        pass_ml = (not self.ml_enabled) or detected_types > 0
        passed = pass_frames and pass_fps and pass_brightness and pass_focus and pass_ml

        result_text = (
            f"{'PASS' if passed else 'FAIL'}\n"
            f"Frames: {self.test_frames}\n"
            f"Elapsed: {elapsed:.1f}s\n"
            f"FPS: {fps:.1f}\n"
            f"Brightness: {avg_brightness:.1f}\n"
            f"Focus(blur var): {avg_blur:.1f}\n"
            f"Defined objects: {len(self.object_labels)}\n"
            f"Detected types in test: {detected_types}"
        )
        if passed:
            messagebox.showinfo("Real Test Result", result_text)
            self.status_var.set("Real camera+ML test passed")
        else:
            messagebox.showwarning("Real Test Result", result_text)
            self.status_var.set("Real camera+ML test failed")

    def get_summary(self):
        self.session_summary["frames"] = self.total_frames
        self.session_summary["detected_types"] = len(self.detected_counts)
        self.session_summary["detected_total"] = sum(self.detected_counts.values())
        return self.session_summary

    def on_close(self):
        self.stop_camera()
        self.tts_stop_event.set()
        self.speech_event.set()
        if self.tts_thread.is_alive():
            self.tts_thread.join(timeout=1.0)
        self.root.quit()
        self.root.destroy()


def run_camera_gui(
    camera_source=0,
    model_path="yolov8n.pt",
    language="en",
    labels_path="multilingual_labels.common.json",
):
    root = tk.Tk()
    app = CameraGUI(
        root,
        camera_source=camera_source,
        model_path=model_path,
        language=language,
        labels_path=labels_path,
    )
    app.start_camera()
    root.mainloop()
    return app.get_summary()


def main():
    run_camera_gui(camera_source=0, model_path="yolov8n.pt", language="en")


if __name__ == "__main__":
    main()
