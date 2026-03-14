# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 
import socket
import struct
import cv2
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import json
import os
from offline_utils import configure_offline_env, ensure_local_model
OFFLINE_MODE = configure_offline_env()
from ultralytics import YOLO
import pyttsx3
import threading
import time
import queue
import base64
import logging
from logging.handlers import RotatingFileHandler
import argparse
import signal

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
except Exception:
    AES = None
    get_random_bytes = None


MAX_UDP_PAYLOAD = 1450
HEADER_FORMAT = "!IHHH"  # frame_id, total_chunks, chunk_index, payload_size
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
FRAME_BUFFER_TIMEOUT = 2.0
NONCE_SIZE = 12
TAG_SIZE = 16
STREAM_TIMEOUT_SEC = 5.0
RECV_IDLE_RESET_SEC = 10.0
SERVER_IDLE_RESTART_DEFAULT_S = 0.0
HEALTH_INTERVAL_DEFAULT_S = 5.0
WATCHDOG_CHECK_DEFAULT_S = 2.0
WATCHDOG_SERVER_IDLE_DEFAULT_S = 30.0
WATCHDOG_CLIENT_IDLE_DEFAULT_S = 15.0
TRACK_IOU_DEFAULT = 0.3
TRACK_MAX_AGE_S_DEFAULT = 1.0
TRACK_MIN_HITS_DEFAULT = 1
AUTH_FRAME_ID = 0xFFFFFFFF


def _bool_env(name, default="0"):
    return os.environ.get(name, default).strip() == "1"


def _validate_aes_key(key_bytes):
    if key_bytes is None:
        return None
    if len(key_bytes) not in (16, 24, 32):
        raise ValueError("AES key must be 16, 24, or 32 bytes.")
    return key_bytes

def _load_udp_key():
    """
    Load UDP key from env. Prefer base64, fallback to hex.
    """
    key_b64 = os.environ.get("WVAB_UDP_KEY_B64", "").strip()
    key_hex = os.environ.get("WVAB_UDP_KEY_HEX", "").strip()
    if key_b64:
        try:
            return base64.b64decode(key_b64, validate=True)
        except Exception:
            return None
    if key_hex:
        try:
            return bytes.fromhex(key_hex)
        except Exception:
            return None
    return None


def _setup_logger(log_path=None, level=None):
    log_path = log_path or os.environ.get("WVAB_UDP_LOG_PATH", "wvab_udp.log")
    level = (level or os.environ.get("WVAB_LOG_LEVEL", "INFO")).upper()
    logger = logging.getLogger("wvab_udp")
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, level, logging.INFO))
    file_handler = RotatingFileHandler(
        log_path, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def _load_overlay_font(language=None, logger=None):
    env_path = os.environ.get("WVAB_FONT_PATH", "").strip()
    font_candidates = []
    if env_path:
        font_candidates.append(env_path)
    lang = (language or "en").lower()
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
                    if logger:
                        logger.info("Overlay font loaded: %s", path)
                    return font
                except Exception:
                    continue
    try:
        if logger:
            logger.warning("Overlay font not found; using default font.")
        return ImageFont.load_default()
    except Exception:
        return None


def _draw_unicode_text(frame, text, x, y, color_bgr, font):
    if text is None:
        text = ""
    text = str(text).strip()
    if not text:
        text = "object"
    x = int(max(x, 2))
    y = int(max(y, 12))
    # draw a simple background for readability
    bg_w = min(frame.shape[1] - x - 2, max(60, len(text) * 10))
    cv2.rectangle(frame, (x - 2, y - 14), (x + bg_w, y + 4), (0, 0, 0), -1)
    if font is None:
        try:
            text.encode("ascii")
            safe = text
        except UnicodeEncodeError:
            safe = "object"
        cv2.putText(frame, safe, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_bgr, 2)
        return frame
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(img)
    color_rgb = (int(color_bgr[2]), int(color_bgr[1]), int(color_bgr[0]))
    draw.text((x, y), text, font=font, fill=color_rgb)
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _write_health(path, payload, logger):
    if not path:
        return
    try:
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception as exc:
        logger.debug("Health write failed: %s", exc)


def _iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter = inter_w * inter_h
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


class SimpleTracker:
    def __init__(self, iou_threshold=TRACK_IOU_DEFAULT, max_age_s=TRACK_MAX_AGE_S_DEFAULT, min_hits=TRACK_MIN_HITS_DEFAULT):
        self.iou_threshold = iou_threshold
        self.max_age_s = max_age_s
        self.min_hits = min_hits
        self.next_id = 1
        self.tracks = {}

    def update(self, detections):
        now = time.time()
        updated = {}
        used_det = set()

        # Match existing tracks
        for track_id, track in list(self.tracks.items()):
            best_iou = 0.0
            best_idx = None
            for idx, det in enumerate(detections):
                if idx in used_det:
                    continue
                if det["class_name"] != track["class_name"]:
                    continue
                iou = _iou(det["bbox"], track["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = idx
            if best_idx is not None and best_iou >= self.iou_threshold:
                det = detections[best_idx]
                used_det.add(best_idx)
                updated[track_id] = {
                    "id": track_id,
                    "class_name": det["class_name"],
                    "bbox": det["bbox"],
                    "last_seen": now,
                    "hits": track["hits"] + 1,
                }
            else:
                if now - track["last_seen"] <= self.max_age_s:
                    updated[track_id] = track

        # Create new tracks
        for idx, det in enumerate(detections):
            if idx in used_det:
                continue
            track_id = self.next_id
            self.next_id += 1
            updated[track_id] = {
                "id": track_id,
                "class_name": det["class_name"],
                "bbox": det["bbox"],
                "last_seen": now,
                "hits": 1,
            }

        self.tracks = updated
        return [t for t in self.tracks.values() if t["hits"] >= self.min_hits]


def _load_config(path):
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        raise RuntimeError(f"Config load failed: {exc}") from exc


def _apply_config_env(config, mode):
    if not isinstance(config, dict):
        return
    env = config.get("env", {})
    mode_env = config.get(f"{mode}_env", {})
    for source in (env, mode_env):
        if isinstance(source, dict):
            for key, value in source.items():
                if key not in os.environ and value is not None:
                    os.environ[key] = str(value)


def _apply_config_args(args, defaults, config, mode):
    if not isinstance(config, dict):
        return args
    section = config.get(mode, {})
    if not isinstance(section, dict):
        return args
    for key, value in section.items():
        if value is None:
            continue
        if hasattr(args, key) and getattr(args, key) == defaults.get(key):
            setattr(args, key, value)
    return args

def _derive_nonce(base_nonce, chunk_index):
    if base_nonce is None or len(base_nonce) != NONCE_SIZE:
        return None
    nonce = bytearray(base_nonce)
    ctr = (nonce[8] << 24) | (nonce[9] << 16) | (nonce[10] << 8) | nonce[11]
    ctr = (ctr + chunk_index) & 0xFFFFFFFF
    nonce[8] = (ctr >> 24) & 0xFF
    nonce[9] = (ctr >> 16) & 0xFF
    nonce[10] = (ctr >> 8) & 0xFF
    nonce[11] = ctr & 0xFF
    return bytes(nonce)

class UDPVisionServer:
    """
    Low-latency vision processing server using UDP protocol
    Optimized for real-time blind navigation assistance
    """
    
    def __init__(
        self,
        host='0.0.0.0',
        port=9999,
        model_path='yolov8n.pt',
        language='en',
        labels_path='multilingual_labels.common.json',
        headless=False,
    ):
        self.host = host
        self.port = port
        try:
            self.model = YOLO(ensure_local_model(model_path, offline=OFFLINE_MODE))
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Model not found: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Model load failure: {exc}") from exc
        self.language = (language or "en").strip().lower()
        self.logger = _setup_logger()
        self.overlay_font = _load_overlay_font(language=self.language, logger=self.logger)
        self.labels_path = labels_path
        self.multilingual_labels = self._load_multilingual_labels(self.labels_path)
        self.available_languages = self._detect_available_languages(self.multilingual_labels)
        if self.language not in self.available_languages:
            self.language = "en"
        self.headless = headless or _bool_env("WVAB_UDP_HEADLESS", "0")
        self.encrypt_udp = _bool_env("WVAB_UDP_ENCRYPT", "1")
        self.udp_key = _validate_aes_key(_load_udp_key()) if self.encrypt_udp else None
        if self.encrypt_udp and (AES is None or self.udp_key is None):
            raise RuntimeError("UDP encryption enabled but Crypto/key not available or key invalid.")
        self.require_auth = _bool_env("WVAB_UDP_AUTH", "1")
        self.auth_token = os.environ.get("WVAB_UDP_TOKEN", "").strip()
        if self.require_auth and not self.auth_token:
            raise RuntimeError("UDP auth enabled but WVAB_UDP_TOKEN is not set.")
        self.auth_ttl_s = float(os.environ.get("WVAB_UDP_AUTH_TTL_S", "120"))
        self.auth_ok = {}
        self.server_idle_restart_s = float(
            os.environ.get("WVAB_UDP_SERVER_IDLE_RESTART_S", str(SERVER_IDLE_RESTART_DEFAULT_S))
        )
        self.enable_tracking = _bool_env("WVAB_UDP_TRACKING", "1")
        self.track_iou = float(os.environ.get("WVAB_UDP_TRACK_IOU", str(TRACK_IOU_DEFAULT)))
        self.track_max_age_s = float(os.environ.get("WVAB_UDP_TRACK_MAX_AGE_S", str(TRACK_MAX_AGE_S_DEFAULT)))
        self.track_min_hits = int(os.environ.get("WVAB_UDP_TRACK_MIN_HITS", str(TRACK_MIN_HITS_DEFAULT)))
        self.tracker = SimpleTracker(
            iou_threshold=self.track_iou,
            max_age_s=self.track_max_age_s,
            min_hits=self.track_min_hits,
        ) if self.enable_tracking else None
        self.health_path = os.environ.get("WVAB_UDP_HEALTH_PATH", "").strip() or None
        self.health_interval_s = float(os.environ.get("WVAB_UDP_HEALTH_INTERVAL_S", str(HEALTH_INTERVAL_DEFAULT_S)))
        self.watchdog_check_s = float(os.environ.get("WVAB_UDP_WATCHDOG_CHECK_S", str(WATCHDOG_CHECK_DEFAULT_S)))
        self.watchdog_server_idle_s = float(
            os.environ.get("WVAB_UDP_WATCHDOG_SERVER_IDLE_S", str(WATCHDOG_SERVER_IDLE_DEFAULT_S))
        )
        self.tts_rate = int(os.environ.get("WVAB_UDP_TTS_RATE", "170"))
        self.tts_stale_s = float(os.environ.get("WVAB_UDP_TTS_STALE_MS", "700")) / 1000.0
        self.tts_flush_on_priority = os.environ.get("WVAB_UDP_TTS_FLUSH_ON_PRIORITY", "1") != "0"
        self.enable_tts = _bool_env("WVAB_UDP_TTS", "1")
        if self.enable_tts:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', self.tts_rate)
            self.speech_language = self._resolve_speech_language(self.language)
            self._select_tts_voice(os.environ.get("WVAB_UDP_TTS_VOICE", ""))
            if self.speech_language != self.language:
                self.logger.warning(
                    "TTS fallback: requested %s, using %s. Install voice pack to enable native speech.",
                    self.language,
                    self.speech_language,
                )
            self.speech_queue = queue.Queue(maxsize=1)
            self.tts_stop_event = threading.Event()
            self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self.tts_thread.start()
        else:
            self.tts_engine = None
            self.speech_queue = queue.Queue(maxsize=1)
            self.tts_stop_event = threading.Event()
            self.speech_language = self.language
        
        # UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        # Performance metrics
        self.frame_count = 0
        self.fps = 0
        self.latency = 0
        self.last_packet_time = time.time()
        self.last_frame_time = time.time()
        
        # Detection settings
        self.confidence_threshold = 0.5
        self.last_announcement = {}
        self.announcement_cooldown = 2.5  # seconds
        
        # Priority objects for blind navigation
        self.critical_objects = {
            'person': 1,
            'car': 1,
            'truck': 1,
            'bus': 1,
            'bicycle': 2,
            'motorcycle': 2,
            'stop sign': 3,
            'traffic light': 3,
            'chair': 4,
            'bench': 4,
            'potted plant': 4,
        }

    def _load_multilingual_labels(self, path):
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
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

    def translate_class_name(self, class_name):
        entry = self.multilingual_labels.get(class_name)
        if isinstance(entry, dict):
            return entry.get(self.language, entry.get("en", class_name))
        return class_name

    def _localized_direction(self, direction):
        phrases = self.multilingual_labels.get("__phrases__", {})
        if isinstance(phrases, dict):
            lang_map = phrases.get(self.language, {})
            if isinstance(lang_map, dict):
                maybe = lang_map.get(direction)
                if isinstance(maybe, str) and maybe.strip():
                    return maybe
        table = {"left": "left", "right": "right", "in front": "ahead"}
        return table.get(direction, direction)

    def _localized_distance(self, distance):
        phrases = self.multilingual_labels.get("__phrases__", {})
        if isinstance(phrases, dict):
            lang_map = phrases.get(self.language, {})
            if isinstance(lang_map, dict):
                maybe = lang_map.get(distance)
                if isinstance(maybe, str) and maybe.strip():
                    return maybe
        table = {"too far": "far", "close": "close", "very close": "very close"}
        return table.get(distance, distance)

    def _detect_tts_languages(self):
        langs = {"en"}
        if not self.tts_engine:
            return langs
        try:
            voices = self.tts_engine.getProperty("voices")
        except Exception:
            return langs
        for voice in voices:
            try:
                for code in getattr(voice, "languages", []) or []:
                    lang = code.decode("utf-8", "ignore") if isinstance(code, bytes) else str(code)
                    if len(lang) >= 2:
                        langs.add(lang[:2].lower())
            except Exception:
                continue
        return langs

    def _resolve_speech_language(self, requested_language):
        installed = self._detect_tts_languages()
        if requested_language in installed:
            return requested_language
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

    def _translate_class_name_for(self, class_name, lang):
        entry = self.multilingual_labels.get(class_name)
        if isinstance(entry, dict):
            return entry.get(lang, entry.get("en", class_name))
        return class_name

    def _is_authed(self, addr):
        if not self.require_auth:
            return True
        ts = self.auth_ok.get(addr)
        if ts is None:
            return False
        if (time.time() - ts) > self.auth_ttl_s:
            del self.auth_ok[addr]
            return False
        return True

    def _handle_auth_packet(self, payload, addr):
        if not self.require_auth:
            return True
        try:
            if self.encrypt_udp:
                if len(payload) <= NONCE_SIZE + TAG_SIZE:
                    return False
                base_nonce = payload[:NONCE_SIZE]
                tag = payload[NONCE_SIZE:NONCE_SIZE + TAG_SIZE]
                ciphertext = payload[NONCE_SIZE + TAG_SIZE:]
                nonce = _derive_nonce(base_nonce, 0)
                cipher = AES.new(self.udp_key, AES.MODE_GCM, nonce=nonce)
                token = cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8", "ignore").strip()
            else:
                token = payload.decode("utf-8", "ignore").strip()
        except Exception:
            return False
        if token != self.auth_token:
            return False
        self.auth_ok[addr] = time.time()
        return True

    def _tts_worker(self):
        """Single speech worker to avoid concurrent pyttsx3 access."""
        while not self.tts_stop_event.is_set():
            try:
                text, ts, priority = self.speech_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if self.tts_stale_s > 0 and (time.time() - ts) > self.tts_stale_s:
                    continue
                if priority and self.tts_flush_on_priority:
                    try:
                        self.tts_engine.stop()
                    except Exception:
                        pass
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                self.logger.exception("TTS error")
    
    def speak(self, text, priority=1):
        """Queue text-to-speech output (non-blocking)."""
        if not self.enable_tts:
            return
        try:
            self.speech_queue.put_nowait((text, time.time(), bool(priority)))
        except queue.Full:
            try:
                self.speech_queue.get_nowait()
            except Exception:
                return
            try:
                self.speech_queue.put_nowait((text, time.time(), bool(priority)))
            except Exception:
                pass

    def stop_tts(self):
        """Stop TTS worker thread cleanly."""
        self.tts_stop_event.set()
        if hasattr(self, "tts_thread") and self.tts_thread.is_alive():
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
        detections = []
        
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
                detections.append({"class_name": class_name, "bbox": bbox})

        if self.enable_tracking and self.tracker is not None:
            tracks = self.tracker.update(detections)
        else:
            tracks = [{"id": None, "class_name": d["class_name"], "bbox": d["bbox"], "hits": 1} for d in detections]

        for track in tracks:
            class_name = track["class_name"]
            bbox = track["bbox"]
            direction, distance = self.calculate_position(bbox, frame.shape)

            # Create announcement
            priority = self.critical_objects[class_name]
            track_id = track.get("id")
            announcement_key = f"{class_name}_{direction}_{track_id}"

            if self.should_announce(announcement_key):
                # Formulate message (compact)
                tts_lang = self.speech_language or self.language
                spoken_name = self._translate_class_name_for(class_name, tts_lang)
                dir_key = "in front" if direction == "center" else direction
                dir_text = self._localized_direction(dir_key) if tts_lang == self.language else dir_key
                if distance == 'immediate':
                    message = f"Warning {spoken_name} {dir_text}"
                elif distance == 'close':
                    distance_label = self._localized_distance('close') if tts_lang == self.language else "close"
                    message = f"{spoken_name} {dir_text} {distance_label}"
                else:
                    message = f"{spoken_name} {dir_text}"
                
                announcements.append((message, priority))
                
                # Draw on frame
                bbox_int = bbox.astype(int)
                color = (0, 0, 255) if distance in ['immediate', 'close'] else (0, 255, 0)
                cv2.rectangle(frame, (bbox_int[0], bbox_int[1]), 
                            (bbox_int[2], bbox_int[3]), color, 2)
                label = f"{spoken_name} {direction}"
                if track_id is not None:
                    label = f"{label} #{track_id}"
                if not str(label).strip():
                    label = str(class_name)
                frame = _draw_unicode_text(
                    frame,
                    label,
                    bbox_int[0],
                    bbox_int[1] - 10,
                    color,
                    self.overlay_font,
                )
        
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
        self.logger.info("UDP Vision Server Started")
        self.logger.info("Listening on %s:%s", self.host, self.port)
        self.logger.info("Waiting for frames...")
        
        frame_buffers = {}
        last_cleanup = time.time()
        
        frame_times = []
        last_fps_time = time.time()
        stop_event = threading.Event()

        def _handle_signal(signum, _frame):
            self.logger.info("Signal %s received. Shutting down...", signum)
            stop_event.set()

        signal.signal(signal.SIGINT, _handle_signal)
        try:
            signal.signal(signal.SIGTERM, _handle_signal)
        except Exception:
            pass

        def _health_loop():
            while not stop_event.is_set():
                payload = {
                    "role": "server",
                    "ts": time.time(),
                    "fps": self.fps,
                    "latency_ms": round(self.latency, 2),
                    "frames_total": self.frame_count,
                    "last_packet_s": round(time.time() - self.last_packet_time, 2),
                    "last_frame_s": round(time.time() - self.last_frame_time, 2),
                }
                _write_health(self.health_path, payload, self.logger)
                time.sleep(self.health_interval_s)

        def _watchdog_loop():
            while not stop_event.is_set():
                idle_s = time.time() - self.last_packet_time
                if self.watchdog_server_idle_s > 0 and idle_s > self.watchdog_server_idle_s:
                    self.logger.error("Watchdog: no packets for %.1fs. Triggering restart.", idle_s)
                    stop_event.set()
                    break
                time.sleep(self.watchdog_check_s)

        if self.health_path:
            threading.Thread(target=_health_loop, daemon=True).start()
        if self.watchdog_server_idle_s > 0:
            threading.Thread(target=_watchdog_loop, daemon=True).start()

        self.last_packet_time = time.time()
        self.last_frame_time = time.time()
        last_idle_warn = 0.0
        last_reset_time = 0.0
        self.sock.settimeout(0.5)
        try:
            while not stop_event.is_set():
                # Receive data
                try:
                    packet, addr = self.sock.recvfrom(65536)
                except socket.timeout:
                    packet = None
                    addr = None
                if packet is not None:
                    self.last_packet_time = time.time()
                    if len(packet) < HEADER_SIZE:
                        continue

                    frame_id, total_chunks, chunk_index, payload_size = struct.unpack(
                        HEADER_FORMAT, packet[:HEADER_SIZE]
                    )
                    chunk_payload = packet[HEADER_SIZE:]
                else:
                    frame_id = None
                    total_chunks = None
                    chunk_index = None
                    payload_size = None
                    chunk_payload = None

                if packet is not None and frame_id == AUTH_FRAME_ID and total_chunks == 0 and chunk_index == 0:
                    if payload_size == len(chunk_payload):
                        self._handle_auth_packet(chunk_payload, addr)
                    continue

                if packet is not None and (payload_size != len(chunk_payload) or chunk_index >= total_chunks):
                    continue

                if packet is not None and not self._is_authed(addr):
                    continue

                if packet is not None and frame_id not in frame_buffers:
                    frame_buffers[frame_id] = {
                        "total": total_chunks,
                        "chunks": {},
                        "timestamp": time.time(),
                        "nonce": None,
                    }

                if packet is not None:
                    entry = frame_buffers[frame_id]
                    if entry["total"] != total_chunks:
                        del frame_buffers[frame_id]
                        continue

                if packet is not None:
                    if self.encrypt_udp:
                        if chunk_index == 0:
                            if len(chunk_payload) <= NONCE_SIZE + TAG_SIZE:
                                continue
                            base_nonce = chunk_payload[:NONCE_SIZE]
                            entry["nonce"] = base_nonce
                            tag = chunk_payload[NONCE_SIZE:NONCE_SIZE + TAG_SIZE]
                            ciphertext = chunk_payload[NONCE_SIZE + TAG_SIZE:]
                            nonce = _derive_nonce(base_nonce, chunk_index)
                        else:
                            if entry.get("nonce") is None:
                                continue
                            if len(chunk_payload) <= TAG_SIZE:
                                continue
                            tag = chunk_payload[:TAG_SIZE]
                            ciphertext = chunk_payload[TAG_SIZE:]
                            nonce = _derive_nonce(entry["nonce"], chunk_index)
                        try:
                            cipher = AES.new(self.udp_key, AES.MODE_GCM, nonce=nonce)
                            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
                        except Exception:
                            if frame_id in frame_buffers:
                                del frame_buffers[frame_id]
                            continue
                        entry["chunks"][chunk_index] = plaintext
                    else:
                        entry["chunks"][chunk_index] = chunk_payload

                if packet is not None and len(entry["chunks"]) == total_chunks:
                    frame_bytes = b"".join(entry["chunks"][i] for i in range(total_chunks))
                    del frame_buffers[frame_id]

                    frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
                    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                    if frame is None:
                        continue
                    self.last_frame_time = time.time()

                    # Process frame
                    processed_frame = self.process_frame(frame)

                    # Calculate FPS
                    self.frame_count += 1
                    frame_times.append(time.time())

                    if time.time() - last_fps_time > 1.0:
                        frame_times = [t for t in frame_times if time.time() - t < 1.0]
                        self.fps = len(frame_times)
                        last_fps_time = time.time()

                        self.logger.info(
                            "FPS: %.1f | Latency: %.1fms | Frames: %s",
                            self.fps,
                            self.latency,
                            self.frame_count,
                        )

                    # Display frame
                    if not self.headless:
                        processed_frame = _draw_unicode_text(
                            processed_frame,
                            f"FPS: {self.fps:.1f} | Latency: {self.latency:.0f}ms",
                            10,
                            30,
                            (0, 255, 0),
                            self.overlay_font,
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

                    if self.require_auth and self.auth_ok:
                        expired = [
                            a for a, ts in self.auth_ok.items()
                            if (time.time() - ts) > self.auth_ttl_s
                        ]
                        for a in expired:
                            del self.auth_ok[a]

                # If no packets for a while, reset buffers (auto-reconnect)
                idle_s = time.time() - self.last_packet_time
                if idle_s > RECV_IDLE_RESET_SEC and time.time() - last_reset_time > 1.0:
                    frame_buffers.clear()
                    last_reset_time = time.time()
                    if time.time() - last_idle_warn > 2.0:
                        self.logger.warning("Stream idle (%.1fs). Waiting for reconnection...", idle_s)
                        last_idle_warn = time.time()
                if self.server_idle_restart_s > 0 and idle_s > self.server_idle_restart_s:
                    self.logger.error("Server idle %.1fs > restart threshold. Exiting for restart.", idle_s)
                    break
        
        except KeyboardInterrupt:
            self.logger.info("Shutting down UDP server...")
        
        finally:
            self.stop_tts()
            self.sock.close()
            if not self.headless:
                cv2.destroyAllWindows()
            self.logger.info("UDP server stopped")


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
        self.encrypt_udp = _bool_env("WVAB_UDP_ENCRYPT", "1")
        self.udp_key = _validate_aes_key(_load_udp_key()) if self.encrypt_udp else None
        if self.encrypt_udp and (AES is None or self.udp_key is None):
            raise RuntimeError("UDP encryption enabled but Crypto/key not available or key invalid.")
        self.require_auth = _bool_env("WVAB_UDP_AUTH", "1")
        self.auth_token = os.environ.get("WVAB_UDP_TOKEN", "").strip()
        if self.require_auth and not self.auth_token:
            raise RuntimeError("UDP auth enabled but WVAB_UDP_TOKEN is not set.")
        self.auth_refresh_s = float(os.environ.get("WVAB_UDP_AUTH_REFRESH_S", "30"))
        self.logger = _setup_logger()
        self.send_timeout_s = float(os.environ.get("WVAB_UDP_CLIENT_SEND_TIMEOUT_S", "2.0"))
        self.health_path = os.environ.get("WVAB_UDP_HEALTH_PATH", "").strip() or None
        self.health_interval_s = float(os.environ.get("WVAB_UDP_HEALTH_INTERVAL_S", str(HEALTH_INTERVAL_DEFAULT_S)))
        self.watchdog_check_s = float(os.environ.get("WVAB_UDP_WATCHDOG_CHECK_S", str(WATCHDOG_CHECK_DEFAULT_S)))
        self.watchdog_client_idle_s = float(
            os.environ.get("WVAB_UDP_WATCHDOG_CLIENT_IDLE_S", str(WATCHDOG_CLIENT_IDLE_DEFAULT_S))
        )
        self.last_send_ok = time.time()
        self.last_frame_ok = time.time()

    def _send_auth(self):
        if not self.require_auth:
            return
        token_bytes = self.auth_token.encode("utf-8")
        if self.encrypt_udp:
            base_nonce = get_random_bytes(NONCE_SIZE)
            nonce = _derive_nonce(base_nonce, 0)
            cipher = AES.new(self.udp_key, AES.MODE_GCM, nonce=nonce)
            ciphertext, tag = cipher.encrypt_and_digest(token_bytes)
            payload = base_nonce + tag + ciphertext
        else:
            payload = token_bytes
        header = struct.pack(HEADER_FORMAT, AUTH_FRAME_ID, 0, 0, len(payload))
        try:
            self.sock.sendto(header + payload, (self.server_ip, self.server_port))
        except OSError:
            pass
    
    def send_frames(self, camera_source=0):
        """
        Send frames from camera to server
        camera_source: 0 for webcam, or IP camera URL
        """
        cap = cv2.VideoCapture(camera_source)
        
        if not cap.isOpened():
            self.logger.error("Could not open camera %s", camera_source)
            return
        
        self.logger.info("UDP Camera Client Started")
        self.logger.info("Sending frames to %s:%s", self.server_ip, self.server_port)
        self.logger.info("Press 'q' to quit")
        
        frame_count = 0
        frame_id = 0
        last_auth_time = 0.0
        
        last_ok_time = time.time()
        consecutive_failures = 0
        self.last_send_ok = time.time()
        self.last_frame_ok = time.time()

        stop_event = threading.Event()

        def _health_loop():
            while not stop_event.is_set():
                payload = {
                    "role": "client",
                    "ts": time.time(),
                    "server": f"{self.server_ip}:{self.server_port}",
                    "last_send_s": round(time.time() - self.last_send_ok, 2),
                    "last_frame_s": round(time.time() - self.last_frame_ok, 2),
                }
                _write_health(self.health_path, payload, self.logger)
                time.sleep(self.health_interval_s)

        def _watchdog_loop():
            while not stop_event.is_set():
                idle_s = time.time() - self.last_send_ok
                if self.watchdog_client_idle_s > 0 and idle_s > self.watchdog_client_idle_s:
                    self.logger.error("Watchdog: no sends for %.1fs. Triggering restart.", idle_s)
                    stop_event.set()
                    break
                time.sleep(self.watchdog_check_s)

        if self.health_path:
            threading.Thread(target=_health_loop, daemon=True).start()
        if self.watchdog_client_idle_s > 0:
            threading.Thread(target=_watchdog_loop, daemon=True).start()
        try:
            if self.require_auth:
                for _ in range(3):
                    self._send_auth()
                    time.sleep(0.1)
                last_auth_time = time.time()
            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    if time.time() - last_ok_time > STREAM_TIMEOUT_SEC:
                        self.logger.warning("Camera read timeout. Reinitializing capture...")
                        cap.release()
                        time.sleep(0.5)
                        cap = cv2.VideoCapture(camera_source)
                        if not cap.isOpened():
                            time.sleep(0.5)
                            continue
                    continue
                last_ok_time = time.time()
                self.last_frame_ok = time.time()
                consecutive_failures = 0
                
                # Resize frame to reduce bandwidth
                # Reduce resolution to lower latency
                frame = cv2.resize(frame, (640, 360))
                
                # JPEG encode before sending to fit practical UDP payload sizes.
                ok, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if not ok:
                    continue

                data = buffer.tobytes()
                if self.encrypt_udp:
                    max_chunk = MAX_UDP_PAYLOAD - HEADER_SIZE - NONCE_SIZE - TAG_SIZE
                else:
                    max_chunk = MAX_UDP_PAYLOAD - HEADER_SIZE
                total_chunks = (len(data) + max_chunk - 1) // max_chunk
                if total_chunks > 65535:
                    continue

                if self.require_auth and (time.time() - last_auth_time) > self.auth_refresh_s:
                    self._send_auth()
                    last_auth_time = time.time()

                for chunk_index in range(total_chunks):
                    start = chunk_index * max_chunk
                    end = start + max_chunk
                    chunk_payload = data[start:end]
                    if self.encrypt_udp:
                        if chunk_index == 0:
                            base_nonce = get_random_bytes(NONCE_SIZE)
                        nonce = _derive_nonce(base_nonce, chunk_index)
                        cipher = AES.new(self.udp_key, AES.MODE_GCM, nonce=nonce)
                        ciphertext, tag = cipher.encrypt_and_digest(chunk_payload)
                        if chunk_index == 0:
                            chunk_payload = base_nonce + tag + ciphertext
                        else:
                            chunk_payload = tag + ciphertext
                    header = struct.pack(
                        HEADER_FORMAT,
                        frame_id,
                        total_chunks,
                        chunk_index,
                        len(chunk_payload),
                    )
                    try:
                        self.sock.sendto(header + chunk_payload, (self.server_ip, self.server_port))
                        self.last_send_ok = time.time()
                    except OSError:
                        consecutive_failures += 1
                        # Recreate socket on network error
                        self.sock.close()
                        time.sleep(0.2)
                        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
                        if consecutive_failures >= 5:
                            self.logger.error("Network send failures. Backing off...")
                            time.sleep(1.0)
                            consecutive_failures = 0

                if time.time() - self.last_send_ok > self.send_timeout_s:
                    self.logger.warning("Network send timeout (%.1fs).", time.time() - self.last_send_ok)
                    self.last_send_ok = time.time()

                frame_id = (frame_id + 1) % (2 ** 32)
                
                frame_count += 1
                if frame_count % 30 == 0:
                    self.logger.info("Sent %s frames", frame_count)
                
                # Show local preview
                cv2.imshow('Camera Client', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
        except KeyboardInterrupt:
            self.logger.info("Stopping camera client...")
        
        finally:
            stop_event.set()
            cap.release()
            cv2.destroyAllWindows()
            self.sock.close()
            self.logger.info("Camera client stopped")


def _build_parser():
    parser = argparse.ArgumentParser(description="WVAB UDP low-latency streaming")
    sub = parser.add_subparsers(dest="mode", required=True)

    server = sub.add_parser("server", help="Start UDP vision server")
    server.add_argument("--config", default=None)
    server.add_argument("--host", default="0.0.0.0")
    server.add_argument("--port", type=int, default=9999)
    server.add_argument("--model", default="yolov8n.pt")
    server.add_argument("--language", default="en")
    server.add_argument("--labels", default="multilingual_labels.common.json")
    server.add_argument("--headless", action="store_true")
    server.add_argument("--log-path", default=None)
    server.add_argument("--log-level", default=None)
    server.add_argument("--auto-restart", action="store_true")
    server.add_argument("--restart-max", type=int, default=3)
    server.add_argument("--restart-delay", type=float, default=2.0)

    client = sub.add_parser("client", help="Start UDP camera client")
    client.add_argument("--config", default=None)
    client.add_argument("--server-ip", default="192.168.4.1")
    client.add_argument("--server-port", type=int, default=9999)
    client.add_argument("--camera", default="0")
    client.add_argument("--log-path", default=None)
    client.add_argument("--log-level", default=None)
    client.add_argument("--auto-restart", action="store_true")
    client.add_argument("--restart-max", type=int, default=3)
    client.add_argument("--restart-delay", type=float, default=2.0)

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()
    defaults = {
        "server": {
            "config": None,
            "host": "0.0.0.0",
            "port": 9999,
            "model": "yolov8n.pt",
            "language": "en",
            "labels": "multilingual_labels.common.json",
            "headless": False,
            "log_path": None,
            "log_level": None,
            "auto_restart": False,
            "restart_max": 3,
            "restart_delay": 2.0,
        },
        "client": {
            "config": None,
            "server_ip": "192.168.4.1",
            "server_port": 9999,
            "camera": "0",
            "log_path": None,
            "log_level": None,
            "auto_restart": False,
            "restart_max": 3,
            "restart_delay": 2.0,
        },
    }
    config = _load_config(args.config) if getattr(args, "config", None) else {}
    _apply_config_env(config, args.mode)
    args = _apply_config_args(args, defaults[args.mode], config, args.mode)

    if args.log_path:
        os.environ["WVAB_UDP_LOG_PATH"] = args.log_path
    if args.log_level:
        os.environ["WVAB_LOG_LEVEL"] = args.log_level
    logger = _setup_logger()

    def _run_with_restart(run_fn, label, max_restarts, delay_s):
        attempt = 0
        while True:
            try:
                run_fn()
                return
            except Exception as exc:
                attempt += 1
                logger.exception("%s crashed: %s", label, exc)
                if attempt > max_restarts:
                    logger.error("%s restart limit reached (%s). Exiting.", label, max_restarts)
                    return
                logger.warning("%s restarting in %.1fs (attempt %s/%s).", label, delay_s, attempt, max_restarts)
                time.sleep(delay_s)

    if args.mode == "server":
        try:
            server = UDPVisionServer(
                host=args.host,
                port=args.port,
                model_path=args.model,
                language=args.language,
                labels_path=args.labels,
                headless=args.headless,
            )
        except FileNotFoundError as exc:
            print(f"Model error: {exc}")
            return
        except RuntimeError as exc:
            print(f"Config error: {exc}")
            return
        if args.auto_restart:
            _run_with_restart(server.receive_frames, "UDP server", args.restart_max, args.restart_delay)
        else:
            server.receive_frames()
    elif args.mode == "client":
        camera = args.camera
        if camera == "0":
            camera = 0
        try:
            client = UDPCameraClient(server_ip=args.server_ip, server_port=args.server_port)
        except RuntimeError as exc:
            print(f"Config error: {exc}")
            return
        if args.auto_restart:
            _run_with_restart(lambda: client.send_frames(camera_source=camera), "UDP client", args.restart_max, args.restart_delay)
        else:
            client.send_frames(camera_source=camera)


if __name__ == "__main__":
    main()
