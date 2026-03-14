# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 

import os
import time
import json
import queue
import threading
import threading as _threading
import logging
from logging.handlers import RotatingFileHandler
import urllib.request
import urllib.parse
import subprocess
import unicodedata
from collections import deque
import asyncio

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pyttsx3

from offline_utils import configure_offline_env, ensure_local_model
from ultralytics import YOLO

OFFLINE_MODE = configure_offline_env()

def _env_flag(name, default="0"):
    return str(os.environ.get(name, default)).strip().lower() not in ("0", "false", "no", "off", "")

def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except Exception:
        return float(default)


def _setup_logger():
    log_path = os.environ.get("WVAB_LOG_PATH", "wvab_server.log")
    level = os.environ.get("WVAB_LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger("wvab_server")
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, level, logging.INFO))
    handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

try:
    import websockets
except Exception:
    websockets = None
try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None

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
        self.model = YOLO(ensure_local_model(model_path, offline=OFFLINE_MODE))
        self.language = language
        self.speech_language = self.language
        self.labels_path = labels_path
        self.logger = _setup_logger()
        self.prod_mode = _env_flag("WVAB_PROD", "0")
        self.enable_display = _env_flag("WVAB_DISPLAY", "1") and not self.prod_mode
        self.log_fps = _env_flag("WVAB_LOG_FPS", "1") and not self.prod_mode
        self.tts_rate = int(os.environ.get("WVAB_TTS_RATE", "190"))
        self.tts_stale_s = float(os.environ.get("WVAB_TTS_STALE_MS", "800")) / 1000.0
        self.tts_flush_on_priority = os.environ.get("WVAB_TTS_FLUSH_ON_PRIORITY", "1") != "0"
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty("rate", self.tts_rate)
        self.tts_engine.setProperty("volume", 1.0)
        self._select_tts_voice(os.environ.get("WVAB_TTS_VOICE", ""))
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
        # Smaller input size to reduce latency for live use.
        self.model_imgsz = 320
        self.infer_width = 640
        self.infer_height = 360
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
        self.overlay_font = self._load_overlay_font()
        self.speech_language = self._resolve_speech_language(self.language)
        self.navigation_phrases = {
            "STOP - obstacle very close": {
                "en": "Stop",
                "ru": "СТОП",
                "bn": "থামুন",
                "hi": "रुकें",
                "es": "Alto",
                "fr": "Stop",
                "ar": "توقف",
            },
            "GO LEFT": {
                "en": "Go left",
                "ru": "НАЛЕВО",
                "bn": "বামে যান",
                "hi": "बाएं जाएं",
                "es": "Izquierda",
                "fr": "À gauche",
                "ar": "يسار",
            },
            "GO RIGHT": {
                "en": "Go right",
                "ru": "НАПРАВО",
                "bn": "ডানে যান",
                "hi": "दाएं जाएं",
                "es": "Derecha",
                "fr": "À droite",
                "ar": "يمين",
            },
            "SLOW - path blocked ahead": {
                "en": "Slow",
                "ru": "МЕДЛЕННЕЕ",
                "bn": "ধীরে",
                "hi": "धीरे",
                "es": "Despacio",
                "fr": "Lent",
                "ar": "ببطء",
            },
            "CLEAN AREA GO STRAIGHT": {
                "en": "Go straight",
                "ru": "ПРЯМО",
                "bn": "সোজা যান",
                "hi": "सीधे जाएं",
                "es": "Recto",
                "fr": "Tout droit",
                "ar": "مستقيم",
            },
        }
        self.system_phrases = {
            "started": {
                "en": "Vision aid started",
                "ru": "Система запущена",
                "bn": "সিস্টেম চালু",
                "hi": "सिस्टम शुरू",
                "es": "Sistema iniciado",
                "fr": "Système démarré",
                "ar": "تم تشغيل النظام",
            },
            "stopped": {
                "en": "Vision aid stopped",
                "ru": "Система остановлена",
                "bn": "সিস্টেম বন্ধ",
                "hi": "सिस्टम बंद",
                "es": "Sistema detenido",
                "fr": "Système arrêté",
                "ar": "تم إيقاف النظام",
            },
        }
        self.ws_control = None
        if websockets is not None and os.environ.get("WVAB_WS", "1") != "0":
            self.ws_control = WebSocketControl(self)
        self.v2x_publisher = None
        if mqtt is not None and os.environ.get("WVAB_MQTT", "0") == "1":
            self.v2x_publisher = V2XPublisher()


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

    def _select_tts_voice(self, preferred):
        if not preferred or not self.tts_engine:
            return
        try:
            voices = self.tts_engine.getProperty("voices")
        except Exception:
            return
        preferred = preferred.strip().lower()
        for voice in voices:
            name = str(getattr(voice, "name", "")).lower()
            vid = str(getattr(voice, "id", "")).lower()
            if preferred in name or preferred in vid:
                try:
                    self.tts_engine.setProperty("voice", voice.id)
                    self.logger.info("TTS voice set: %s", getattr(voice, "name", voice.id))
                    return
                except Exception:
                    return
        self.logger.warning("TTS voice '%s' not found. Using default.", preferred)

    def _load_multilingual_labels(self, path):
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            self.logger.exception("Could not load labels file '%s'", path)
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

    def translate_system(self, key):
        mapping = self.system_phrases.get(key)
        if isinstance(mapping, dict):
            return mapping.get(self.language, mapping.get("en", key))
        return key

    def _localized_direction(self, direction):
        phrases = self.multilingual_labels.get("__phrases__", {})
        if isinstance(phrases, dict):
            lang_map = phrases.get(self.language, {})
            if isinstance(lang_map, dict):
                maybe = lang_map.get(direction)
                if isinstance(maybe, str) and maybe.strip():
                    return maybe
        table = {
            "en": {"left": "left", "right": "right", "in front": "ahead"},
            "ru": {"left": "слева", "right": "справа", "in front": "спереди"},
            "bn": {"left": "বামে", "right": "ডানে", "in front": "সামনে"},
            "hi": {"left": "बाएं", "right": "दाएं", "in front": "सामने"},
            "es": {"left": "izquierda", "right": "derecha", "in front": "delante"},
            "fr": {"left": "à gauche", "right": "à droite", "in front": "devant"},
            "ar": {"left": "يسار", "right": "يمين", "in front": "أمام"},
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
            "en": {"too far": "far", "close": "close", "very close": "very close"},
            "ru": {"too far": "далеко", "close": "близко", "very close": "очень близко"},
            "bn": {"too far": "দূরে", "close": "কাছে", "very close": "খুব কাছে"},
            "hi": {"too far": "दूर", "close": "पास", "very close": "बहुत पास"},
            "es": {"too far": "lejos", "close": "cerca", "very close": "muy cerca"},
            "fr": {"too far": "loin", "close": "proche", "very close": "très proche"},
            "ar": {"too far": "بعيد", "close": "قريب", "very close": "قريب جدًا"},
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

    def _load_overlay_font(self):
        env_path = os.environ.get("WVAB_FONT_PATH", "").strip()
        font_candidates = []
        if env_path:
            font_candidates.append(env_path)

        lang = (self.language or "en").lower()
        if lang.startswith("bn"):
            font_candidates += [
                "C:/Windows/Fonts/Nirmala.ttf",
                "C:/Windows/Fonts/kalpurush.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansBengaliUI-Regular.ttf",
            ]
        elif lang.startswith("hi"):
            font_candidates += [
                "C:/Windows/Fonts/Mangal.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
            ]
        elif lang.startswith("ru"):
            font_candidates += [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        else:
            font_candidates += [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/seguiemj.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        for path in font_candidates:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, 18)
                    self.logger.info("Overlay font loaded: %s", path)
                    return font
                except Exception:
                    continue
        try:
            self.logger.warning("Overlay font not found; using default font.")
            return ImageFont.load_default()
        except Exception:
            return None

    def _draw_unicode_text(self, frame, text, x, y, color_bgr):
        if self.overlay_font is None:
            cv2.putText(
                frame,
                self._overlay_safe_text(text),
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color_bgr,
                2,
            )
            return frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        draw = ImageDraw.Draw(img)
        color_rgb = (int(color_bgr[2]), int(color_bgr[1]), int(color_bgr[0]))
        draw.text((x, y), text, font=self.overlay_font, fill=color_rgb)
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    def prettify_class_name(self, class_name):
        return class_name.replace("_", " ").strip().title()

    def _tts_worker(self):
        """Single speech worker to keep pyttsx3 access thread-safe."""
        while not self.tts_stop_event.is_set():
            self.speech_event.wait(timeout=0.1)
            if self.tts_stop_event.is_set():
                break

            text = None
            ts = 0.0
            is_priority = False
            with self.speech_lock:
                if self.priority_speech is not None:
                    text, ts = self.priority_speech
                    is_priority = True
                    self.priority_speech = None
                elif self.latest_speech is not None:
                    text, ts = self.latest_speech
                    self.latest_speech = None
                self.speech_event.clear()
            if not text:
                continue
            try:
                if self.tts_stale_s > 0 and (time.time() - ts) > self.tts_stale_s:
                    continue
                self._speak_blocking(text, flush=is_priority)
                self.last_spoken_text = text
            except Exception:
                self.logger.exception("TTS error")

    def _speak_blocking(self, text, flush=False):
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

        if flush:
            try:
                self.tts_engine.stop()
            except Exception:
                pass
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def speak(self, text):
        """Queue text-to-speech output (non-blocking)."""
        with self.speech_lock:
            self.priority_speech = None
            self.latest_speech = (text, time.time())
            self.speech_event.set()
        if self.ws_control is not None:
            self.ws_control.publish_tts(text)
        if self.v2x_publisher is not None:
            self.v2x_publisher.publish_tts(text)

    def speak_priority(self, text):
        """Prioritize urgent navigation speech by clearing stale queue."""
        with self.speech_lock:
            self.priority_speech = (text, time.time())
            self.speech_event.set()
        if self.ws_control is not None:
            self.ws_control.publish_tts(text)
        if self.v2x_publisher is not None:
            self.v2x_publisher.publish_tts(text)

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

    def estimate_distance_m(self, class_name, bbox):
        """Estimate object distance in meters using pinhole-camera approximation."""
        object_width_m = self.known_object_width_m.get(class_name)
        if object_width_m is None:
            return None
        bbox_width_px = max(float(bbox[2] - bbox[0]), 1.0)
        distance_m = (object_width_m * self.default_focal_length_px) / bbox_width_px
        return float(np.clip(distance_m, 0.2, 20.0))

    def distance_bucket(self, distance_m, size_ratio):
        """Map numeric distance to coarse proximity labels."""
        if distance_m is not None:
            if distance_m <= 1.0:
                return "very close"
            if distance_m <= 2.5:
                return "close"
            return "too far"
        if size_ratio > 0.3:
            return "very close"
        if size_ratio > 0.15:
            return "close"
        return "too far"

    def distance_text_for_speech(self, distance_m):
        if distance_m is None:
            return ""
        return f"about {distance_m:.1f} meters"

    def _compact_speech_message(self, spoken_name, direction, distance):
        dir_text = self._localized_direction(direction)
        dist_text = self._localized_distance(distance)
        parts = [spoken_name]
        if dir_text:
            parts.append(dir_text)
        if distance in ("close", "very close"):
            parts.append(dist_text)
        message = " ".join(parts)
        if distance == "very close":
            message = f"Warning {message}"
        return message
    
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
                
                distance_m = self.estimate_distance_m(class_name, bbox)
                distance = self.distance_bucket(distance_m, size_ratio)

                spoken_name = self.translate_class_name(class_name)
                detection_info = {
                    'class': class_name,
                    'label': spoken_name,
                    'confidence': confidence,
                    'direction': direction,
                    'distance': distance,
                    'distance_m': distance_m,
                    'bbox': bbox
                }
                detections.append(detection_info)

                detection_key = f"{class_name}_{direction}_{distance}"
                frame_keys.add(detection_key)
                speech_candidates.append(
                    (confidence, detection_key, spoken_name, direction, distance, distance_m)
                )

        self.recent_detection_keys.append(frame_keys)

        # Speak only top confident stable objects to avoid audio flood.
        spoken_this_frame = 0
        used_keys = set()
        for confidence, detection_key, spoken_name, direction, distance, distance_m in sorted(
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

            message = self._compact_speech_message(spoken_name, direction, distance)
            self.speak(message)
            if self.ws_control is not None:
                self.ws_control.publish_event(
                    {
                        "object": class_name,
                        "label": spoken_name,
                        "direction": direction,
                        "distance": distance,
                        "distance_m": distance_m,
                        "confidence": float(confidence),
                        "timestamp": time.time(),
                    }
                )
            if self.v2x_publisher is not None:
                self.v2x_publisher.publish_event(
                    {
                        "object": class_name,
                        "label": spoken_name,
                        "direction": direction,
                        "distance": distance,
                        "distance_m": distance_m,
                        "confidence": float(confidence),
                        "timestamp": time.time(),
                    }
                )
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
            distance_m = det.get("distance_m")
            
            # Draw bounding box
            color = (0, 255, 0) if det['distance'] != "very close" else (0, 0, 255)
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            
            # Draw label
            distance_suffix = f", {distance_m:.1f}m" if distance_m is not None else ""
            label = f"{class_name} {confidence:.2f} ({direction}, {det['distance']}{distance_suffix})"
            frame = self._draw_unicode_text(frame, label, bbox[0], bbox[1] - 10, color)

        if instruction:
            if severity == "danger":
                nav_color = (0, 0, 255)
            elif severity == "warning":
                nav_color = (0, 165, 255)
            else:
                nav_color = (0, 255, 0)
            frame = self._draw_unicode_text(frame, f"NAV: {instruction}", 10, 35, nav_color)
        
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
        self.speak(self.translate_system("started"))
        self.running = True
        
        fps_counter = 0
        start_time = time.time()
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    print("Error: Failed to grab frame")
                    break
                
                # Downscale frame for faster inference
                infer_frame = cv2.resize(frame, (self.infer_width, self.infer_height))
                results = self.model(infer_frame, imgsz=self.model_imgsz, verbose=False)
                
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
                if self.log_fps and fps_counter % 30 == 0:
                    elapsed = time.time() - start_time
                    fps = fps_counter / elapsed
                    print(f"FPS: {fps:.2f} | Detections: {len(detections)}")
                
                # Display frame (comment out for headless operation)
                if self.enable_display:
                    cv2.imshow('WVAB - Vision Aid System', annotated_frame)
                
                # Press 'q' to quit
                if self.enable_display and cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        except KeyboardInterrupt:
            print("\nStopping vision aid system...")
        
        finally:
            self.running = False
            cap.release()
            cv2.destroyAllWindows()
            self.speak(self.translate_system("stopped"))
            self.stop_tts()
    
    def run_with_mjpeg_stream(self):
        """Run with MJPEG stream (for ESP32-CAM)"""
        print(f"Connecting to ESP32-CAM at {self.camera_url}...")
        
        try:
            stream = urllib.request.urlopen(self.camera_url, timeout=10)
        except Exception as e:
            self.logger.exception("Error connecting to camera")
            return
        
        print("Connected! Starting vision aid system...")
        self.speak(self.translate_system("started"))
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
                        # Downscale frame for faster inference
                        infer_frame = cv2.resize(frame, (self.infer_width, self.infer_height))
                        results = self.model(infer_frame, imgsz=self.model_imgsz, verbose=False)
                        
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
                        if self.log_fps and fps_counter % 30 == 0:
                            elapsed = time.time() - start_time
                            fps = fps_counter / elapsed
                            print(f"FPS: {fps:.2f} | Detections: {len(detections)}")
                        
                        # Display frame (optional for production)
                        if self.enable_display:
                            cv2.imshow('WVAB - Vision Aid System', annotated_frame)
                        
                        if self.enable_display and cv2.waitKey(1) & 0xFF == ord('q'):
                            break
        
        except KeyboardInterrupt:
            print("\nStopping vision aid system...")
        
        except Exception as e:
            self.logger.exception("Error in stream processing")
        
        finally:
            self.running = False
            stream.close()
            cv2.destroyAllWindows()
            self.speak(self.translate_system("stopped"))
            self.stop_tts()


class WebSocketControl:
    """
    Lightweight WebSocket control/feedback channel.
    Commands:
      {"cmd":"set_language","value":"bn"}
      {"cmd":"set_all_objects","value":true}
      {"cmd":"set_confidence","value":0.4}
    """

    def __init__(self, server, host="0.0.0.0", port=8765):
        self.server = server
        self.host = host
        self.port = port
        self.clients = set()
        self.auth_token = os.environ.get("WVAB_WS_TOKEN", "").strip()
        self.queue = queue.Queue(maxsize=200)
        self.last_event_time = {}
        self.last_tts_time = 0.0
        self.last_event_key = None
        self.event_min_interval = float(os.environ.get("WVAB_WS_EVENT_MS", "150")) / 1000.0
        self.tts_min_interval = float(os.environ.get("WVAB_WS_TTS_MS", "120")) / 1000.0
        self.drop_duplicates = os.environ.get("WVAB_WS_DROP_DUP", "1") != "0"
        self.max_queue = 200
        self.loop = asyncio.new_event_loop()
        self.thread = _threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def publish_tts(self, text):
        now = time.time()
        if now - self.last_tts_time < self.tts_min_interval:
            return
        self.last_tts_time = now
        payload = json.dumps({"type": "tts", "text": text}, ensure_ascii=False)
        try:
            if self.queue.qsize() >= self.max_queue:
                return
            self.queue.put_nowait(payload)
        except Exception:
            pass
    def publish_event(self, event):
        key = f"{event.get('object')}|{event.get('direction')}|{event.get('distance')}"
        now = time.time()
        last = self.last_event_time.get(key, 0.0)
        if now - last < self.event_min_interval:
            return
        if self.drop_duplicates and self.last_event_key == key:
            return
        self.last_event_time[key] = now
        self.last_event_key = key
        payload = json.dumps({"type": "detection", **event}, ensure_ascii=False)
        try:
            if self.queue.qsize() >= self.max_queue:
                return
            self.queue.put_nowait(payload)
        except Exception:
            pass

    async def _sender(self):
        while True:
            text = await self.loop.run_in_executor(None, self.queue.get)
            if not text:
                continue
            dead = []
            for ws in list(self.clients):
                try:
                    await ws.send(text)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.clients.discard(ws)

    def _is_authenticated(self, websocket):
        if not self.auth_token:
            return True
        token = ""
        try:
            headers = getattr(websocket, "request_headers", {}) or {}
            auth_header = headers.get("Authorization", "")
            if auth_header.lower().startswith("bearer "):
                token = auth_header.split(" ", 1)[1].strip()
        except Exception:
            token = ""
        if not token:
            try:
                path = getattr(websocket, "path", "")
                qs = urllib.parse.urlparse(path).query
                params = urllib.parse.parse_qs(qs)
                token = (params.get("token", [""]) or [""])[0].strip()
            except Exception:
                token = ""
        return token == self.auth_token

    async def _handler(self, websocket):
        if not self._is_authenticated(websocket):
            try:
                await websocket.close(code=1008, reason="Unauthorized")
            except Exception:
                pass
            return
        self.clients.add(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                except Exception:
                    continue
                cmd = data.get("cmd")
                if cmd == "set_language":
                    self.server.set_language(data.get("value", "en"))
                elif cmd == "set_all_objects":
                    self.server.detect_all_objects = bool(data.get("value", True))
                elif cmd == "set_confidence":
                    try:
                        self.server.confidence_threshold = float(data.get("value", 0.5))
                    except Exception:
                        pass
        finally:
            self.clients.discard(websocket)

    def _run(self):
        asyncio.set_event_loop(self.loop)
        start_server = websockets.serve(self._handler, self.host, self.port)
        self.loop.run_until_complete(start_server)
        self.loop.create_task(self._sender())
        self.loop.run_forever()


class V2XPublisher:
    """
    MQTT publisher for V2X/audit events.
    Set env:
      WVAB_MQTT=1
      WVAB_MQTT_HOST (default localhost)
      WVAB_MQTT_PORT (default 1883)
      WVAB_MQTT_TOPIC (default wvab/v2x/detection)
    """

    def __init__(self):
        self.host = os.environ.get("WVAB_MQTT_HOST", "localhost")
        self.port = int(os.environ.get("WVAB_MQTT_PORT", "1883"))
        self.topic = os.environ.get("WVAB_MQTT_TOPIC", "wvab/v2x/detection")
        self.tts_topic = os.environ.get("WVAB_MQTT_TTS_TOPIC", "wvab/v2x/tts")
        self.client = mqtt.Client()
        self.client.connect(self.host, self.port, 60)
        self.client.loop_start()

    def publish_event(self, event):
        payload = json.dumps({"type": "detection", **event}, ensure_ascii=False)
        try:
            self.client.publish(self.topic, payload, qos=0)
        except Exception:
            pass

    def publish_tts(self, text):
        payload = json.dumps({"type": "tts", "text": text}, ensure_ascii=False)
        try:
            self.client.publish(self.tts_topic, payload, qos=0)
        except Exception:
            pass


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
    
    MODEL_PATH = os.environ.get("WVAB_MODEL", "yolov8n.pt")  # Nano model (fastest)
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
    try:
        server = VisionAidServer(
            camera_url=CAMERA_URL,
            model_path=MODEL_PATH,
            language=language,
            labels_path=labels_path,
        )
    except FileNotFoundError as exc:
        print(f"Model error: {exc}")
        return
    
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
