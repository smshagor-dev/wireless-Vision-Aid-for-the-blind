#!/usr/bin/env python3
"""Local/IP-camera WVAB assistive vision runtime.

Secure remote ESP32 transport is implemented by udp_streaming.py. This module
intentionally has no remote control socket and does not report uncalibrated
bounding-box heuristics as metric distance.
"""

import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import queue
import signal
import threading
import time

import cv2
import numpy as np
import pyttsx3
from PIL import Image, ImageDraw, ImageFont

from core.font_paths import overlay_font_candidates
from core.object_policy import CriticalObjectPolicy, label_candidates
from core.proximity import classify_bbox_proximity
from offline_utils import configure_offline_env, ensure_local_model

OFFLINE_MODE = configure_offline_env()
from ultralytics import YOLO


def _bool_env(name, default="0"):
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _setup_logger():
    path = os.environ.get("WVAB_LOG_PATH", "wvab_server.log")
    level = os.environ.get("WVAB_LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger("wvab_vision")
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, level, logging.INFO))
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler = RotatingFileHandler(path, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


class VisionAidServer:
    def __init__(
        self,
        camera_url=0,
        model_path="yolov8n.pt",
        language="en",
        labels_path="multilingual_labels.common.json",
        headless=None,
        enable_tts=None,
        confidence=None,
    ):
        self.logger = _setup_logger()
        self.camera_url = self._normalize_camera_source(camera_url)
        self.model = YOLO(ensure_local_model(model_path, offline=OFFLINE_MODE))
        self.labels_path = labels_path
        self.multilingual_labels = self._load_multilingual_labels(labels_path)
        self.available_languages = self._detect_languages(self.multilingual_labels)
        self.language = "en"
        self.set_language(language)
        self.overlay_font = self._load_overlay_font()

        if confidence is None:
            confidence = float(os.environ.get("WVAB_CONFIDENCE", "0.5"))
        self.confidence_threshold = float(confidence)
        if not 0.05 <= self.confidence_threshold <= 0.99:
            raise ValueError("confidence must be between 0.05 and 0.99")

        if headless is None:
            headless = not _bool_env("WVAB_DISPLAY", "1")
        self.headless = bool(headless)
        self.stream_timeout_s = float(os.environ.get("WVAB_CAMERA_TIMEOUT_S", "5"))
        self.announcement_cooldown_s = float(os.environ.get("WVAB_ANNOUNCE_COOLDOWN_S", "2.0"))
        self.last_announcement = {}
        self.running = False

        self.priority = CriticalObjectPolicy()

        if enable_tts is None:
            enable_tts = _bool_env("WVAB_TTS", "1")
        self.enable_tts = bool(enable_tts)
        self.tts_engine = None
        self.tts_queue = queue.Queue(maxsize=1)
        self.tts_stop = threading.Event()
        self.tts_thread = None
        if self.enable_tts:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", int(os.environ.get("WVAB_TTS_RATE", "175")))
                self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
                self.tts_thread.start()
            except Exception as exc:
                self.logger.warning("TTS unavailable on this host: %s", exc)
                self.enable_tts = False
                self.tts_engine = None

    @staticmethod
    def _normalize_camera_source(source):
        if isinstance(source, int):
            return source
        text = str(source).strip()
        return int(text) if text.isdigit() else text

    def _load_multilingual_labels(self, path):
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            self.logger.warning("Could not load labels file %s: %s", path, exc)
            return {}

    @staticmethod
    def _detect_languages(labels):
        languages = {"en"}
        for value in labels.values() if isinstance(labels, dict) else []:
            if isinstance(value, dict):
                languages.update(str(key).lower() for key in value if isinstance(key, str) and key.strip())
        return sorted(languages)

    def set_language(self, language):
        requested = str(language or "en").strip().lower()
        if requested not in self.available_languages:
            self.logger.warning("Unsupported label language '%s'; using English", requested)
            requested = "en"
        self.language = requested
        if hasattr(self, "overlay_font"):
            self.overlay_font = self._load_overlay_font()

    def _translate(self, class_name):
        for candidate in label_candidates(class_name):
            entry = self.multilingual_labels.get(candidate)
            if isinstance(entry, dict):
                return entry.get(self.language, entry.get("en", candidate.replace("_", " ")))
        return str(class_name or "object").replace("_", " ")

    def _phrase(self, key):
        phrases = self.multilingual_labels.get("__phrases__", {})
        if isinstance(phrases, dict):
            language_table = phrases.get(self.language, {})
            if isinstance(language_table, dict):
                value = language_table.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        fallback = {
            "left": "left",
            "right": "right",
            "in front": "ahead",
            "close": "close",
            "very close": "very close",
        }
        return fallback.get(key, key)

    def _load_overlay_font(self):
        env_path = os.environ.get("WVAB_FONT_PATH", "").strip() or None
        for path in overlay_font_candidates(self.language, env_path):
            if not os.path.exists(path):
                continue
            try:
                return ImageFont.truetype(path, 18)
            except Exception:
                continue
        try:
            return ImageFont.load_default()
        except Exception:
            return None

    def _draw_text(self, frame, text, x, y, color_bgr):
        if self.overlay_font is None:
            ascii_text = text.encode("ascii", "ignore").decode("ascii") or "object"
            cv2.putText(
                frame,
                ascii_text,
                (max(2, x), max(15, y)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color_bgr,
                2,
            )
            return frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        draw = ImageDraw.Draw(image)
        draw.text(
            (max(2, x), max(2, y)),
            text,
            font=self.overlay_font,
            fill=(int(color_bgr[2]), int(color_bgr[1]), int(color_bgr[0])),
        )
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    @staticmethod
    def _direction(bbox, frame_width):
        center = (float(bbox[0]) + float(bbox[2])) * 0.5
        if center < frame_width * 0.33:
            return "left"
        if center > frame_width * 0.67:
            return "right"
        return "in front"

    def process_detections(self, results, frame):
        frame_width = frame.shape[1]
        detections = []
        for result in results:
            for box in result.boxes:
                confidence = float(box.conf[0])
                if confidence < self.confidence_threshold:
                    continue
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                bbox = box.xyxy[0].cpu().numpy()
                proximity = classify_bbox_proximity(bbox, frame.shape)
                direction = self._direction(bbox, frame_width)
                detections.append(
                    {
                        "class": class_name,
                        "label": self._translate(class_name),
                        "confidence": confidence,
                        "direction": direction,
                        "proximity": proximity.label,
                        "bbox": bbox,
                    }
                )
        return detections

    def _should_announce(self, detection):
        key = f"{detection['class']}|{detection['direction']}|{detection['proximity']}"
        now = time.time()
        last = self.last_announcement.get(key, 0.0)
        if now - last < self.announcement_cooldown_s:
            return False
        self.last_announcement[key] = now
        return True

    @staticmethod
    def _proximity_rank(label):
        return {"immediate": 0, "close": 1, "medium": 2, "far": 3}.get(label, 4)

    def announce_best_detection(self, detections):
        ordered = sorted(
            detections,
            key=lambda item: (
                self._proximity_rank(item["proximity"]),
                self.priority.get(item["class"], 5),
                -item["confidence"],
            ),
        )
        item = next((candidate for candidate in ordered if self._should_announce(candidate)), None)
        if item is None:
            return
        direction = self._phrase(item["direction"])
        label = item["label"]
        if item["proximity"] == "immediate":
            self.speak(f"Warning {label} {direction} {self._phrase('very close')}", urgent=True)
        elif item["proximity"] == "close":
            self.speak(f"{label} {direction} {self._phrase('close')}")
        else:
            self.speak(f"{label} {direction}")

    def draw_detections(self, frame, detections):
        for item in detections:
            bbox = np.asarray(item["bbox"]).astype(int)
            danger = item["proximity"] in {"immediate", "close"}
            color = (0, 0, 255) if danger else (0, 255, 0)
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            label = (
                f"{item['label']} {item['confidence']:.2f} "
                f"({item['direction']}, {item['proximity']})"
            )
            frame = self._draw_text(frame, label, bbox[0], bbox[1] - 20, color)
        return frame

    def _tts_worker(self):
        stale_s = float(os.environ.get("WVAB_TTS_STALE_MS", "900")) / 1000.0
        while not self.tts_stop.is_set():
            try:
                text, created, urgent = self.tts_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if stale_s > 0 and time.time() - created > stale_s:
                continue
            try:
                if urgent:
                    self.tts_engine.stop()
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception:
                self.logger.exception("TTS error")

    def speak(self, text, urgent=False):
        if not self.enable_tts:
            return
        payload = (text, time.time(), bool(urgent))
        try:
            self.tts_queue.put_nowait(payload)
        except queue.Full:
            try:
                self.tts_queue.get_nowait()
                self.tts_queue.put_nowait(payload)
            except Exception:
                pass

    def stop_tts(self):
        self.tts_stop.set()
        if self.tts_thread and self.tts_thread.is_alive():
            self.tts_thread.join(timeout=1.0)
        if self.tts_engine is not None:
            try:
                self.tts_engine.stop()
            except Exception:
                pass

    def run_with_opencv_stream(self):
        cap = cv2.VideoCapture(self.camera_url)
        if not cap.isOpened():
            self.stop_tts()
            raise RuntimeError("Could not open configured camera source")

        self.running = True
        failed_since = None
        stop_event = threading.Event()

        def handle_signal(signum, _frame):
            self.logger.info("Signal %s received; stopping vision runtime", signum)
            stop_event.set()

        signal.signal(signal.SIGINT, handle_signal)
        try:
            signal.signal(signal.SIGTERM, handle_signal)
        except (AttributeError, ValueError):
            pass

        self.logger.info("Vision runtime started")
        try:
            while self.running and not stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    failed_since = failed_since or time.time()
                    if time.time() - failed_since >= self.stream_timeout_s:
                        raise RuntimeError("Camera stream timed out")
                    stop_event.wait(0.05)
                    continue
                failed_since = None

                results = self.model(frame, imgsz=320, verbose=False)
                detections = self.process_detections(results, frame)
                self.announce_best_detection(detections)

                if not self.headless:
                    annotated = self.draw_detections(frame.copy(), detections)
                    cv2.imshow("WVAB - Local Vision", annotated)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
        finally:
            self.running = False
            cap.release()
            if not self.headless:
                cv2.destroyAllWindows()
            self.stop_tts()
            self.logger.info("Vision runtime stopped")

    def run_with_mjpeg_stream(self):
        """Compatibility alias; OpenCV handles trusted MJPEG URLs directly."""
        return self.run_with_opencv_stream()


def main():
    parser = argparse.ArgumentParser(description="Run WVAB on a local or trusted IP camera source")
    parser.add_argument(
        "--camera",
        default=os.environ.get("WVAB_CAMERA", "0"),
        help="Camera index or trusted local stream URL",
    )
    parser.add_argument("--model", default=os.environ.get("WVAB_MODEL", "yolov8n.pt"))
    parser.add_argument("--language", default=os.environ.get("WVAB_LANGUAGE", "en"))
    parser.add_argument("--labels", default="multilingual_labels.common.json")
    parser.add_argument(
        "--confidence",
        type=float,
        default=float(os.environ.get("WVAB_CONFIDENCE", "0.5")),
    )
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-tts", action="store_true")
    args = parser.parse_args()

    server = VisionAidServer(
        camera_url=args.camera,
        model_path=args.model,
        language=args.language,
        labels_path=args.labels,
        headless=args.headless,
        enable_tts=not args.no_tts,
        confidence=args.confidence,
    )
    server.run_with_opencv_stream()


if __name__ == "__main__":
    main()
