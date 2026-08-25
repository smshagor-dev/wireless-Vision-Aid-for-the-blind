#!/usr/bin/env python3
"""Secure, replay-aware low-latency UDP camera transport for WVAB."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hmac
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import queue
import signal
import socket
import threading
import time

import cv2
import numpy as np
import pyttsx3
from PIL import Image, ImageDraw, ImageFont

from core.font_paths import overlay_font_candidates
from core.proximity import classify_bbox_proximity
from core.security import normalize_control_host, resolve_control_token, verify_secret
from core.udp_protocol import (
    AUTH_FRAME_ID,
    HEADER_SIZE,
    MAX_DATA_FRAME_ID,
    MAX_FRAME_BYTES,
    MAX_FRAME_CHUNKS,
    MAX_INFLIGHT_FRAMES_PER_CLIENT,
    MAX_UDP_PAYLOAD,
    NONCE_SIZE,
    TAG_SIZE,
    frame_id_is_newer,
    pack_header,
    unpack_header,
    valid_frame_shape,
)
from offline_utils import configure_offline_env, ensure_local_model

OFFLINE_MODE = configure_offline_env()

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
except Exception:
    AES = None
    get_random_bytes = None


FRAME_BUFFER_TIMEOUT_S = 2.0
HEALTH_INTERVAL_DEFAULT_S = 5.0
WATCHDOG_CHECK_DEFAULT_S = 2.0
WATCHDOG_SERVER_FRAME_IDLE_DEFAULT_S = 30.0
WATCHDOG_CLIENT_SEND_IDLE_DEFAULT_S = 15.0
TRACK_IOU_DEFAULT = 0.3
TRACK_MAX_AGE_S_DEFAULT = 1.0
TRACK_MIN_HITS_DEFAULT = 1


def _bool_env(name: str, default: str = "0") -> bool:
    return str(os.environ.get(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def _validate_aes_key(key_bytes: bytes | None) -> bytes | None:
    if key_bytes is None:
        return None
    if len(key_bytes) not in (16, 24, 32):
        raise ValueError("AES key must be 16, 24, or 32 bytes")
    return key_bytes


def _load_udp_key() -> bytes | None:
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


def _derive_nonce(base_nonce: bytes, chunk_index: int) -> bytes:
    if len(base_nonce) != NONCE_SIZE:
        raise ValueError("invalid base nonce length")
    nonce = bytearray(base_nonce)
    counter = int.from_bytes(nonce[8:12], "big")
    nonce[8:12] = ((counter + int(chunk_index)) & 0xFFFFFFFF).to_bytes(4, "big")
    return bytes(nonce)


def _secure_transport_settings():
    encrypt = _bool_env("WVAB_UDP_ENCRYPT", "1")
    require_auth = _bool_env("WVAB_UDP_AUTH", "1")
    allow_insecure = _bool_env("WVAB_ALLOW_INSECURE_UDP", "0")
    if (not encrypt or not require_auth) and not allow_insecure:
        raise RuntimeError(
            "authentication and encryption are required; set WVAB_ALLOW_INSECURE_UDP=1 only for isolated development"
        )

    key = _validate_aes_key(_load_udp_key()) if encrypt else None
    if encrypt and (AES is None or get_random_bytes is None or key is None):
        raise RuntimeError("UDP encryption requires PyCryptodome and a valid 16/24/32-byte AES key")

    token = os.environ.get("WVAB_UDP_TOKEN", "").strip()
    if require_auth and len(token) < 16:
        raise RuntimeError("WVAB_UDP_TOKEN must contain at least 16 characters")
    return encrypt, key, require_auth, token


def _setup_logger(log_path: str | None = None, level: str | None = None):
    log_path = log_path or os.environ.get("WVAB_UDP_LOG_PATH", "wvab_udp.log")
    level = (level or os.environ.get("WVAB_LOG_LEVEL", "INFO")).upper()
    logger = logging.getLogger("wvab_udp")
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, level, logging.INFO))
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    console_handler = logging.StreamHandler()
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def _write_health(path: str | None, payload: dict, logger) -> None:
    if not path:
        return
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(tmp_path, path)
    except Exception as exc:
        logger.debug("Health write failed: %s", exc)
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            pass


def _load_config(path: str | None) -> dict:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise RuntimeError("Config root must be an object")
    return data


def _apply_config_env(config: dict, mode: str) -> None:
    for source in (config.get("env", {}), config.get(f"{mode}_env", {})):
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            if key not in os.environ and value is not None:
                os.environ[key] = str(value)


def _apply_config_args(args, defaults: dict, config: dict, mode: str):
    section = config.get(mode, {})
    if not isinstance(section, dict):
        return args
    for key, value in section.items():
        if value is not None and hasattr(args, key) and getattr(args, key) == defaults.get(key):
            setattr(args, key, value)
    return args


def _load_overlay_font(language: str, logger):
    env_path = os.environ.get("WVAB_FONT_PATH", "").strip() or None
    for path in overlay_font_candidates(language, env_path):
        if not os.path.exists(path):
            continue
        try:
            font = ImageFont.truetype(path, 18)
            logger.info("Overlay font loaded: %s", path)
            return font
        except Exception:
            continue
    logger.warning("Unicode overlay font unavailable; using PIL default")
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _draw_unicode_text(frame, text, x, y, color_bgr, font):
    text = str(text or "object").strip() or "object"
    x = int(max(x, 2))
    y = int(max(y, 12))
    if font is None:
        cv2.putText(
            frame,
            text if text.isascii() else "object",
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color_bgr,
            2,
        )
        return frame
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)
    draw.text((x, y), text, font=font, fill=(int(color_bgr[2]), int(color_bgr[1]), int(color_bgr[0])))
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def _iou(box_a, box_b) -> float:
    ax1, ay1, ax2, ay2 = [float(value) for value in box_a]
    bx1, by1, bx2, by2 = [float(value) for value in box_b]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    intersection = iw * ih
    if intersection <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


class SimpleTracker:
    def __init__(self, iou_threshold=TRACK_IOU_DEFAULT, max_age_s=TRACK_MAX_AGE_S_DEFAULT, min_hits=TRACK_MIN_HITS_DEFAULT):
        self.iou_threshold = float(iou_threshold)
        self.max_age_s = max(float(max_age_s), 0.05)
        self.min_hits = max(int(min_hits), 1)
        self.next_id = 1
        self.tracks = {}

    def update(self, detections):
        now = time.monotonic()
        updated = {}
        used = set()
        for track_id, track in list(self.tracks.items()):
            best_score, best_index = 0.0, None
            for index, detection in enumerate(detections):
                if index in used or detection["class_name"] != track["class_name"]:
                    continue
                score = _iou(track["bbox"], detection["bbox"])
                if score > best_score:
                    best_score, best_index = score, index
            if best_index is not None and best_score >= self.iou_threshold:
                detection = detections[best_index]
                used.add(best_index)
                updated[track_id] = {
                    "id": track_id,
                    "class_name": detection["class_name"],
                    "bbox": detection["bbox"],
                    "last_seen": now,
                    "hits": track["hits"] + 1,
                }
            elif now - track["last_seen"] <= self.max_age_s:
                updated[track_id] = track

        for index, detection in enumerate(detections):
            if index in used:
                continue
            track_id = self.next_id
            self.next_id += 1
            updated[track_id] = {
                "id": track_id,
                "class_name": detection["class_name"],
                "bbox": detection["bbox"],
                "last_seen": now,
                "hits": 1,
            }
        self.tracks = updated
        return [track for track in updated.values() if track["hits"] >= self.min_hits]


class UDPVisionServer:
    def __init__(
        self,
        host="0.0.0.0",
        port=9999,
        model_path="yolov8n.pt",
        language="en",
        labels_path="multilingual_labels.common.json",
        headless=False,
    ):
        self.host = str(host)
        self.port = int(port)
        if not 1 <= self.port <= 65535:
            raise ValueError("UDP port must be in 1..65535")

        self.logger = _setup_logger()
        self.encrypt_udp, self.udp_key, self.require_auth, self.auth_token = _secure_transport_settings()
        self.auth_ttl_s = max(float(os.environ.get("WVAB_UDP_AUTH_TTL_S", "120")), 5.0)
        self.auth_ok = {}
        self.seen_auth_nonces = {}
        self.last_completed_frame = {}

        from ultralytics import YOLO

        self.model = YOLO(ensure_local_model(model_path, offline=OFFLINE_MODE))
        self.language = (language or "en").strip().lower()
        self.multilingual_labels = self._load_labels(labels_path)
        self.available_languages = self._available_languages(self.multilingual_labels)
        if self.language not in self.available_languages:
            self.language = "en"
        self.overlay_font = _load_overlay_font(self.language, self.logger)
        self.headless = bool(headless or _bool_env("WVAB_UDP_HEADLESS", "0"))

        self.confidence_threshold = float(os.environ.get("WVAB_UDP_CONFIDENCE", "0.5"))
        if not 0.05 <= self.confidence_threshold <= 0.99:
            raise ValueError("WVAB_UDP_CONFIDENCE must be between 0.05 and 0.99")
        self.all_objects = _bool_env("WVAB_UDP_ALL_OBJECTS", "0")
        self.critical_objects = {
            "person": 1,
            "car": 1,
            "truck": 1,
            "bus": 1,
            "bicycle": 2,
            "motorcycle": 2,
            "stop sign": 3,
            "traffic light": 3,
            "chair": 4,
            "bench": 4,
            "potted plant": 4,
        }
        self.announcement_cooldown = max(float(os.environ.get("WVAB_UDP_ANNOUNCE_COOLDOWN_S", "2.5")), 0.1)
        self.last_announcement = {}

        self.enable_tracking = _bool_env("WVAB_UDP_TRACKING", "1")
        self.tracker = (
            SimpleTracker(
                os.environ.get("WVAB_UDP_TRACK_IOU", TRACK_IOU_DEFAULT),
                os.environ.get("WVAB_UDP_TRACK_MAX_AGE_S", TRACK_MAX_AGE_S_DEFAULT),
                os.environ.get("WVAB_UDP_TRACK_MIN_HITS", TRACK_MIN_HITS_DEFAULT),
            )
            if self.enable_tracking
            else None
        )

        self.enable_tts = _bool_env("WVAB_UDP_TTS", "1")
        self.tts_engine = None
        self.tts_thread = None
        self.tts_stop = threading.Event()
        self.speech_queue = queue.Queue(maxsize=1)
        self.speech_language = self.language
        if self.enable_tts:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", int(os.environ.get("WVAB_UDP_TTS_RATE", "170")))
                self.speech_language = self._resolve_speech_language(self.language)
                self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
                self.tts_thread.start()
            except Exception as exc:
                self.logger.warning("TTS unavailable: %s", exc)
                self.enable_tts = False
                self.tts_engine = None

        self.health_path = os.environ.get("WVAB_UDP_HEALTH_PATH", "").strip() or None
        self.health_interval_s = max(float(os.environ.get("WVAB_UDP_HEALTH_INTERVAL_S", HEALTH_INTERVAL_DEFAULT_S)), 0.5)
        self.watchdog_server_frame_idle_s = float(
            os.environ.get(
                "WVAB_UDP_WATCHDOG_SERVER_FRAME_IDLE_S",
                os.environ.get("WVAB_UDP_WATCHDOG_SERVER_IDLE_S", WATCHDOG_SERVER_FRAME_IDLE_DEFAULT_S),
            )
        )

        self.control_enabled = _bool_env("WVAB_WS_CONTROL", "1")
        self.control_host = normalize_control_host(os.environ.get("WVAB_WS_CONTROL_HOST"))
        self.control_port = int(os.environ.get("WVAB_WS_CONTROL_PORT", "8765"))
        if not 1 <= self.control_port <= 65535:
            raise ValueError("WebSocket control port must be in 1..65535")
        dedicated_ws_token = os.environ.get("WVAB_WS_TOKEN", "").strip()
        self.control_token = resolve_control_token(dedicated_ws_token, self.auth_token)
        if self.control_enabled and len(self.control_token or "") < 16:
            raise RuntimeError("WebSocket control requires a secret of at least 16 characters")
        if self.control_enabled and self.control_host not in {"127.0.0.1", "::1", "localhost"} and len(dedicated_ws_token) < 16:
            raise RuntimeError("remote WebSocket control requires a dedicated WVAB_WS_TOKEN")
        self.control_stop = threading.Event()
        self.control_thread = None

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262144)
        now = time.monotonic()
        self.started_mono = now
        self.last_valid_packet_mono = now
        self.last_frame_mono = now
        self.frame_count = 0
        self.fps = 0.0
        self.latency_ms = 0.0

    def _load_labels(self, path):
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            self.logger.warning("Label map load failed: %s", exc)
            return {}

    @staticmethod
    def _available_languages(labels):
        languages = {"en"}
        if isinstance(labels, dict):
            for value in labels.values():
                if isinstance(value, dict):
                    languages.update(str(key).lower() for key in value if isinstance(key, str) and key.strip())
        return sorted(languages)

    def _translate(self, class_name, language=None):
        language = language or self.language
        entry = self.multilingual_labels.get(class_name)
        if isinstance(entry, dict):
            return entry.get(language, entry.get("en", class_name))
        return class_name.replace("_", " ")

    def _phrase(self, key, language=None):
        language = language or self.language
        phrases = self.multilingual_labels.get("__phrases__", {})
        if isinstance(phrases, dict):
            table = phrases.get(language, {})
            if isinstance(table, dict) and isinstance(table.get(key), str):
                return table[key]
        return {"left": "left", "right": "right", "in front": "ahead", "close": "close"}.get(key, key)

    def _installed_tts_languages(self):
        languages = {"en"}
        if self.tts_engine is None:
            return languages
        try:
            voices = self.tts_engine.getProperty("voices")
        except Exception:
            return languages
        for voice in voices:
            text = " ".join(
                [str(getattr(voice, "name", "")), str(getattr(voice, "id", ""))]
                + [
                    item.decode("utf-8", "ignore") if isinstance(item, bytes) else str(item)
                    for item in (getattr(voice, "languages", []) or [])
                ]
            ).lower()
            for code in ("bn", "hi", "ru", "en", "ar", "es", "fr"):
                if code in text:
                    languages.add(code)
        return languages

    def _resolve_speech_language(self, requested):
        return requested if requested in self._installed_tts_languages() else "en"

    def _tts_worker(self):
        stale_s = float(os.environ.get("WVAB_UDP_TTS_STALE_MS", "700")) / 1000.0
        while not self.tts_stop.is_set():
            try:
                text, created = self.speech_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if stale_s > 0 and time.monotonic() - created > stale_s:
                continue
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception:
                self.logger.exception("TTS error")

    def _speak(self, text):
        if not self.enable_tts:
            return
        payload = (text, time.monotonic())
        try:
            self.speech_queue.put_nowait(payload)
        except queue.Full:
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.put_nowait(payload)
            except Exception:
                pass

    def _stop_tts(self):
        self.tts_stop.set()
        if self.tts_thread and self.tts_thread.is_alive():
            self.tts_thread.join(timeout=1.0)
        if self.tts_engine is not None:
            try:
                self.tts_engine.stop()
            except Exception:
                pass

    def _is_authed(self, addr) -> bool:
        if not self.require_auth:
            return True
        authenticated_at = self.auth_ok.get(addr)
        if authenticated_at is None:
            return False
        if time.monotonic() - authenticated_at > self.auth_ttl_s:
            self.auth_ok.pop(addr, None)
            return False
        return True

    def _handle_auth(self, header: bytes, payload: bytes, addr) -> bool:
        if not self.require_auth:
            self.last_valid_packet_mono = time.monotonic()
            return True
        try:
            if self.encrypt_udp:
                if len(payload) <= NONCE_SIZE + TAG_SIZE:
                    return False
                base_nonce = payload[:NONCE_SIZE]
                if base_nonce in self.seen_auth_nonces:
                    return False
                tag = payload[NONCE_SIZE:NONCE_SIZE + TAG_SIZE]
                ciphertext = payload[NONCE_SIZE + TAG_SIZE:]
                cipher = AES.new(self.udp_key, AES.MODE_GCM, nonce=_derive_nonce(base_nonce, 0))
                cipher.update(header)
                token = cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8", "strict").strip()
            else:
                base_nonce = None
                token = payload.decode("utf-8", "strict").strip()
        except Exception:
            return False

        if not verify_secret(token, self.auth_token):
            return False
        now = time.monotonic()
        self.auth_ok[addr] = now
        if base_nonce is not None:
            self.seen_auth_nonces[base_nonce] = now
        self.last_valid_packet_mono = now
        return True

    def _cleanup_security_state(self, frame_buffers):
        now = time.monotonic()
        for key in [key for key, value in frame_buffers.items() if now - value["created"] > FRAME_BUFFER_TIMEOUT_S]:
            frame_buffers.pop(key, None)
        for addr in [addr for addr, stamp in self.auth_ok.items() if now - stamp > self.auth_ttl_s]:
            self.auth_ok.pop(addr, None)
        for nonce in [nonce for nonce, stamp in self.seen_auth_nonces.items() if now - stamp > self.auth_ttl_s]:
            self.seen_auth_nonces.pop(nonce, None)

    @staticmethod
    def _evict_excess_frames(frame_buffers, addr):
        keys = [key for key in frame_buffers if key[0] == addr]
        if len(keys) < MAX_INFLIGHT_FRAMES_PER_CLIENT:
            return
        oldest = min(keys, key=lambda key: frame_buffers[key]["created"])
        frame_buffers.pop(oldest, None)

    def _decrypt_chunk(self, header, payload, entry, chunk_index):
        if not self.encrypt_udp:
            return payload
        if len(payload) <= NONCE_SIZE + TAG_SIZE:
            raise ValueError("encrypted chunk is too short")
        base_nonce = payload[:NONCE_SIZE]
        tag = payload[NONCE_SIZE:NONCE_SIZE + TAG_SIZE]
        ciphertext = payload[NONCE_SIZE + TAG_SIZE:]
        if entry["base_nonce"] is None:
            entry["base_nonce"] = base_nonce
        elif not hmac.compare_digest(base_nonce, entry["base_nonce"]):
            raise ValueError("frame chunks use inconsistent base nonces")
        cipher = AES.new(self.udp_key, AES.MODE_GCM, nonce=_derive_nonce(base_nonce, chunk_index))
        cipher.update(header)
        return cipher.decrypt_and_verify(ciphertext, tag)

    def _set_language(self, language):
        language = str(language or "").strip().lower()
        if language not in self.available_languages:
            raise ValueError("unsupported language")
        self.language = language
        self.overlay_font = _load_overlay_font(language, self.logger)
        self.speech_language = self._resolve_speech_language(language) if self.enable_tts else language

    def _apply_control(self, command):
        if not isinstance(command, dict):
            raise ValueError("invalid command")
        if not verify_secret(command.get("token"), self.control_token):
            raise PermissionError("unauthorized")
        name = command.get("cmd")
        if name == "set_language":
            self._set_language(command.get("value"))
        elif name == "set_all_objects":
            value = command.get("value")
            if not isinstance(value, bool):
                raise ValueError("invalid boolean")
            self.all_objects = value
        elif name == "set_confidence":
            value = float(command.get("value"))
            if not 0.05 <= value <= 0.99:
                raise ValueError("invalid confidence")
            self.confidence_threshold = value
        elif name != "status":
            raise ValueError("unsupported command")
        return {
            "ok": True,
            "language": self.language,
            "all_objects": self.all_objects,
            "confidence": self.confidence_threshold,
            "fps": self.fps,
            "latency_ms": round(self.latency_ms, 2),
        }

    async def _control_handler(self, websocket):
        async for message in websocket:
            try:
                response = self._apply_control(json.loads(message))
            except Exception as exc:
                response = {"ok": False, "error": type(exc).__name__}
            await websocket.send(json.dumps(response, ensure_ascii=False))

    def _control_main(self):
        async def runner():
            try:
                import websockets
            except Exception as exc:
                self.logger.error("WebSocket control unavailable: %s", exc)
                return
            async with websockets.serve(self._control_handler, self.control_host, self.control_port, max_size=8192):
                self.logger.info("WebSocket control listening on %s:%s", self.control_host, self.control_port)
                while not self.control_stop.is_set():
                    await asyncio.sleep(0.25)
        try:
            asyncio.run(runner())
        except Exception:
            self.logger.exception("WebSocket control stopped unexpectedly")

    def _start_control(self):
        if not self.control_enabled:
            return
        self.control_thread = threading.Thread(target=self._control_main, daemon=True)
        self.control_thread.start()

    def _direction_and_proximity(self, bbox, frame_shape):
        center = (float(bbox[0]) + float(bbox[2])) * 0.5
        width = float(frame_shape[1])
        direction = "left" if center < width * 0.3 else "right" if center > width * 0.7 else "center"
        return direction, classify_bbox_proximity(bbox, frame_shape)

    def _should_announce(self, key):
        now = time.monotonic()
        previous = self.last_announcement.get(key)
        if previous is None or now - previous >= self.announcement_cooldown:
            self.last_announcement[key] = now
            return True
        return False

    def _process_frame(self, frame):
        started = time.monotonic()
        results = self.model(frame, verbose=False)
        detections = []
        for result in results:
            for box in result.boxes:
                confidence = float(box.conf[0])
                if confidence < self.confidence_threshold:
                    continue
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                if not self.all_objects and class_name not in self.critical_objects:
                    continue
                detections.append({"class_name": class_name, "bbox": box.xyxy[0].cpu().numpy()})

        if self.tracker:
            tracks = self.tracker.update(detections)
        else:
            tracks = [
                {"id": None, "class_name": detection["class_name"], "bbox": detection["bbox"], "hits": 1}
                for detection in detections
            ]

        announcements = []
        for track in tracks:
            class_name = track["class_name"]
            bbox = track["bbox"]
            direction, proximity = self._direction_and_proximity(bbox, frame.shape)
            direction_key = "in front" if direction == "center" else direction
            spoken_name = self._translate(class_name, self.speech_language)
            spoken_direction = self._phrase(direction_key, self.speech_language)
            announcement_key = f"{class_name}:{direction}:{track.get('id')}"
            if self._should_announce(announcement_key):
                if proximity.label == "immediate":
                    message = f"Warning {spoken_name} {spoken_direction}"
                elif proximity.label == "close":
                    message = f"{spoken_name} {spoken_direction} {self._phrase('close', self.speech_language)}"
                else:
                    message = f"{spoken_name} {spoken_direction}"
                announcements.append((self.critical_objects.get(class_name, 5), message))

            box = np.asarray(bbox).astype(int)
            color = (0, 0, 255) if proximity.label in {"immediate", "close"} else (0, 255, 0)
            cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)
            label = f"{self._translate(class_name)} {direction} {proximity.label}"
            if track.get("id") is not None:
                label += f" #{track['id']}"
            frame = _draw_unicode_text(frame, label, box[0], box[1] - 10, color, self.overlay_font)

        if announcements:
            announcements.sort(key=lambda item: item[0])
            self._speak(announcements[0][1])
        self.latency_ms = (time.monotonic() - started) * 1000.0
        return frame

    def receive_frames(self):
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(0.5)
        self._start_control()
        self.logger.info("Secure UDP vision server listening on %s:%s", self.host, self.port)

        stop_event = threading.Event()
        frame_buffers = {}
        recent_frame_times = []
        last_cleanup = time.monotonic()

        def handle_signal(signum, _frame):
            self.logger.info("Signal %s received", signum)
            stop_event.set()

        signal.signal(signal.SIGINT, handle_signal)
        try:
            signal.signal(signal.SIGTERM, handle_signal)
        except Exception:
            pass

        def health_loop():
            while not stop_event.is_set():
                now = time.monotonic()
                _write_health(
                    self.health_path,
                    {
                        "role": "server",
                        "ts": time.time(),
                        "fps": self.fps,
                        "latency_ms": round(self.latency_ms, 2),
                        "frames_total": self.frame_count,
                        "last_valid_packet_s": round(now - self.last_valid_packet_mono, 2),
                        "last_completed_frame_s": round(now - self.last_frame_mono, 2),
                    },
                    self.logger,
                )
                stop_event.wait(self.health_interval_s)

        if self.health_path:
            threading.Thread(target=health_loop, daemon=True).start()

        try:
            while not stop_event.is_set():
                packet = None
                addr = None
                try:
                    packet, addr = self.sock.recvfrom(65536)
                except socket.timeout:
                    pass

                if packet is not None:
                    if len(packet) < HEADER_SIZE or len(packet) > MAX_UDP_PAYLOAD:
                        continue
                    header = packet[:HEADER_SIZE]
                    try:
                        frame_id, total_chunks, chunk_index, payload_size = unpack_header(header)
                    except ValueError:
                        continue
                    payload = packet[HEADER_SIZE:]

                    if frame_id == AUTH_FRAME_ID and total_chunks == 0 and chunk_index == 0:
                        if payload_size == len(payload) and payload_size > 0:
                            self._handle_auth(header, payload, addr)
                        continue

                    if not valid_frame_shape(total_chunks, chunk_index, payload_size, len(packet)):
                        continue
                    if not self._is_authed(addr):
                        continue
                    if not frame_id_is_newer(frame_id, self.last_completed_frame.get(addr)):
                        continue

                    key = (addr, frame_id)
                    entry = frame_buffers.get(key)
                    if entry is None:
                        self._evict_excess_frames(frame_buffers, addr)
                        entry = {
                            "total": total_chunks,
                            "chunks": {},
                            "created": time.monotonic(),
                            "base_nonce": None,
                            "bytes": 0,
                        }
                        frame_buffers[key] = entry
                    elif entry["total"] != total_chunks:
                        frame_buffers.pop(key, None)
                        continue

                    try:
                        plain = self._decrypt_chunk(header, payload, entry, chunk_index)
                    except Exception:
                        frame_buffers.pop(key, None)
                        continue

                    existing = entry["chunks"].get(chunk_index)
                    if existing is not None:
                        if not hmac.compare_digest(existing, plain):
                            frame_buffers.pop(key, None)
                        continue
                    if entry["bytes"] + len(plain) > MAX_FRAME_BYTES:
                        frame_buffers.pop(key, None)
                        continue
                    entry["chunks"][chunk_index] = plain
                    entry["bytes"] += len(plain)
                    self.last_valid_packet_mono = time.monotonic()

                    if len(entry["chunks"]) == total_chunks:
                        try:
                            data = b"".join(entry["chunks"][index] for index in range(total_chunks))
                        except KeyError:
                            frame_buffers.pop(key, None)
                            continue
                        frame_buffers.pop(key, None)
                        self.last_completed_frame[addr] = frame_id
                        for stale_key in list(frame_buffers):
                            if stale_key[0] == addr and not frame_id_is_newer(stale_key[1], frame_id):
                                frame_buffers.pop(stale_key, None)

                        frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is None:
                            continue
                        self.last_frame_mono = time.monotonic()
                        processed = self._process_frame(frame)
                        self.frame_count += 1
                        now = time.monotonic()
                        recent_frame_times.append(now)
                        recent_frame_times = [stamp for stamp in recent_frame_times if now - stamp < 1.0]
                        self.fps = float(len(recent_frame_times))

                        if not self.headless:
                            processed = _draw_unicode_text(
                                processed,
                                f"FPS: {self.fps:.1f} | Latency: {self.latency_ms:.0f}ms",
                                10,
                                30,
                                (0, 255, 0),
                                self.overlay_font,
                            )
                            cv2.imshow("WVAB - UDP Server", processed)
                            if cv2.waitKey(1) & 0xFF == ord("q"):
                                stop_event.set()

                now = time.monotonic()
                if now - last_cleanup >= 1.0:
                    self._cleanup_security_state(frame_buffers)
                    last_cleanup = now

                frame_idle = now - self.last_frame_mono
                if self.watchdog_server_frame_idle_s > 0 and frame_idle > self.watchdog_server_frame_idle_s:
                    raise RuntimeError(f"watchdog: no completed video frame for {frame_idle:.1f}s")
        finally:
            stop_event.set()
            self.control_stop.set()
            self._stop_tts()
            try:
                self.sock.close()
            except Exception:
                pass
            if self.control_thread and self.control_thread.is_alive():
                self.control_thread.join(timeout=1.0)
            if not self.headless:
                cv2.destroyAllWindows()
            self.logger.info("UDP server stopped")


class UDPCameraClient:
    def __init__(self, server_ip="192.168.4.1", server_port=9999):
        self.server_ip = str(server_ip)
        self.server_port = int(server_port)
        if not 1 <= self.server_port <= 65535:
            raise ValueError("server port must be in 1..65535")

        self.encrypt_udp, self.udp_key, self.require_auth, self.auth_token = _secure_transport_settings()
        self.auth_refresh_s = max(float(os.environ.get("WVAB_UDP_AUTH_REFRESH_S", "30")), 2.0)
        self.health_path = os.environ.get("WVAB_UDP_HEALTH_PATH", "").strip() or None
        self.health_interval_s = max(float(os.environ.get("WVAB_UDP_HEALTH_INTERVAL_S", HEALTH_INTERVAL_DEFAULT_S)), 0.5)
        self.watchdog_check_s = max(float(os.environ.get("WVAB_UDP_WATCHDOG_CHECK_S", WATCHDOG_CHECK_DEFAULT_S)), 0.2)
        self.watchdog_client_send_idle_s = float(
            os.environ.get("WVAB_UDP_WATCHDOG_CLIENT_IDLE_S", WATCHDOG_CLIENT_SEND_IDLE_DEFAULT_S)
        )
        self.logger = _setup_logger()
        self.sock = self._new_socket()
        now = time.monotonic()
        self.last_send_mono = now
        self.last_camera_frame_mono = now
        self.force_auth = True
        self.watchdog_error = None

    @staticmethod
    def _new_socket():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
        return sock

    def _recreate_socket(self):
        try:
            self.sock.close()
        except Exception:
            pass
        self.sock = self._new_socket()
        self.force_auth = True

    def _send_packet(self, packet: bytes):
        try:
            self.sock.sendto(packet, (self.server_ip, self.server_port))
        except OSError:
            self._recreate_socket()
            self.sock.sendto(packet, (self.server_ip, self.server_port))
        self.last_send_mono = time.monotonic()

    def _send_auth(self):
        if not self.require_auth:
            self.force_auth = False
            return
        token = self.auth_token.encode("utf-8")
        if self.encrypt_udp:
            base_nonce = get_random_bytes(NONCE_SIZE)
            payload_size = NONCE_SIZE + TAG_SIZE + len(token)
            header = pack_header(AUTH_FRAME_ID, 0, 0, payload_size)
            cipher = AES.new(self.udp_key, AES.MODE_GCM, nonce=_derive_nonce(base_nonce, 0))
            cipher.update(header)
            ciphertext, tag = cipher.encrypt_and_digest(token)
            payload = base_nonce + tag + ciphertext
        else:
            payload = token
            header = pack_header(AUTH_FRAME_ID, 0, 0, len(payload))
        self._send_packet(header + payload)
        self.force_auth = False

    @staticmethod
    def _camera_source(source):
        text = str(source).strip()
        return int(text) if text.isdigit() else text

    def send_frames(self, camera_source=0):
        camera_source = self._camera_source(camera_source)
        cap = cv2.VideoCapture(camera_source)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera {camera_source}")

        frame_id = 0
        last_auth = 0.0
        camera_failure_since = None
        stop_event = threading.Event()

        def handle_signal(signum, _frame):
            self.logger.info("Signal %s received", signum)
            stop_event.set()

        signal.signal(signal.SIGINT, handle_signal)
        try:
            signal.signal(signal.SIGTERM, handle_signal)
        except Exception:
            pass

        def health_loop():
            while not stop_event.is_set():
                now = time.monotonic()
                _write_health(
                    self.health_path,
                    {
                        "role": "client",
                        "ts": time.time(),
                        "server": f"{self.server_ip}:{self.server_port}",
                        "last_send_s": round(now - self.last_send_mono, 2),
                        "last_camera_frame_s": round(now - self.last_camera_frame_mono, 2),
                    },
                    self.logger,
                )
                stop_event.wait(self.health_interval_s)

        def watchdog_loop():
            while not stop_event.wait(self.watchdog_check_s):
                idle = time.monotonic() - self.last_send_mono
                if self.watchdog_client_send_idle_s > 0 and idle > self.watchdog_client_send_idle_s:
                    self.watchdog_error = f"watchdog: no successful local UDP send for {idle:.1f}s"
                    stop_event.set()
                    return

        if self.health_path:
            threading.Thread(target=health_loop, daemon=True).start()
        if self.watchdog_client_send_idle_s > 0:
            threading.Thread(target=watchdog_loop, daemon=True).start()

        try:
            while not stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    if camera_failure_since is None:
                        camera_failure_since = time.monotonic()
                    if time.monotonic() - camera_failure_since >= 5.0:
                        self.logger.warning("Camera read timeout; reopening source")
                        cap.release()
                        stop_event.wait(0.5)
                        cap = cv2.VideoCapture(camera_source)
                        camera_failure_since = time.monotonic()
                    continue

                camera_failure_since = None
                self.last_camera_frame_mono = time.monotonic()
                frame = cv2.resize(frame, (640, 360))
                encoded, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if not encoded:
                    continue

                data = buffer.tobytes()
                max_plain = MAX_UDP_PAYLOAD - HEADER_SIZE
                if self.encrypt_udp:
                    max_plain -= NONCE_SIZE + TAG_SIZE
                total_chunks = (len(data) + max_plain - 1) // max_plain
                if total_chunks <= 0 or total_chunks > MAX_FRAME_CHUNKS or len(data) > MAX_FRAME_BYTES:
                    self.logger.warning("Encoded frame exceeds protocol bounds; dropping frame")
                    continue

                now = time.monotonic()
                if self.require_auth and (self.force_auth or now - last_auth >= self.auth_refresh_s):
                    self._send_auth()
                    last_auth = now

                base_nonce = get_random_bytes(NONCE_SIZE) if self.encrypt_udp else None
                for chunk_index in range(total_chunks):
                    plain = data[chunk_index * max_plain:(chunk_index + 1) * max_plain]
                    payload_size = len(plain) + (NONCE_SIZE + TAG_SIZE if self.encrypt_udp else 0)
                    header = pack_header(frame_id, total_chunks, chunk_index, payload_size)
                    if self.encrypt_udp:
                        cipher = AES.new(self.udp_key, AES.MODE_GCM, nonce=_derive_nonce(base_nonce, chunk_index))
                        cipher.update(header)
                        ciphertext, tag = cipher.encrypt_and_digest(plain)
                        payload = base_nonce + tag + ciphertext
                    else:
                        payload = plain
                    self._send_packet(header + payload)

                frame_id = 0 if frame_id >= MAX_DATA_FRAME_ID else frame_id + 1
                if not _bool_env("WVAB_UDP_CLIENT_HEADLESS", "0"):
                    cv2.imshow("WVAB - Camera Client", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        stop_event.set()
        finally:
            stop_event.set()
            cap.release()
            try:
                self.sock.close()
            except Exception:
                pass
            if not _bool_env("WVAB_UDP_CLIENT_HEADLESS", "0"):
                cv2.destroyAllWindows()

        if self.watchdog_error:
            raise RuntimeError(self.watchdog_error)


def _build_parser():
    parser = argparse.ArgumentParser(description="WVAB secure low-latency UDP streaming")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    server = subparsers.add_parser("server")
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

    client = subparsers.add_parser("client")
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
    args = _build_parser().parse_args()
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

    config = _load_config(args.config) if args.config else {}
    _apply_config_env(config, args.mode)
    args = _apply_config_args(args, defaults[args.mode], config, args.mode)

    if args.restart_max < 0 or args.restart_delay < 0:
        raise SystemExit("restart-max and restart-delay must be non-negative")
    if args.log_path:
        os.environ["WVAB_UDP_LOG_PATH"] = args.log_path
    if args.log_level:
        os.environ["WVAB_LOG_LEVEL"] = args.log_level
    logger = _setup_logger()

    def run_with_restart(factory, runner, label):
        failures = 0
        while True:
            instance = factory()
            try:
                runner(instance)
                return
            except KeyboardInterrupt:
                return
            except Exception as exc:
                failures += 1
                logger.exception("%s stopped with error: %s", label, exc)
                if not args.auto_restart or failures > args.restart_max:
                    raise
                time.sleep(args.restart_delay)

    if args.mode == "server":
        run_with_restart(
            lambda: UDPVisionServer(
                host=args.host,
                port=args.port,
                model_path=args.model,
                language=args.language,
                labels_path=args.labels,
                headless=args.headless,
            ),
            lambda server: server.receive_frames(),
            "UDP server",
        )
    else:
        run_with_restart(
            lambda: UDPCameraClient(args.server_ip, args.server_port),
            lambda client: client.send_frames(args.camera),
            "UDP client",
        )


if __name__ == "__main__":
    main()
