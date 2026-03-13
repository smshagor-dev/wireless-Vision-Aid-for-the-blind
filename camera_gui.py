# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 

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
import logging
from logging.handlers import RotatingFileHandler
import math

import cv2
import numpy as np
from PIL import Image, ImageTk
from PIL import ImageDraw, ImageFont
import pyttsx3
try:
    import psutil
except Exception:
    psutil = None
try:
    from perception.depth_estimator import DepthEstimator
    from perception.perception_mapping import update_grid_from_frame
    from mapping.occupancy_grid import OccupancyGrid
    from mapping.slam import VisualOdometry
    from navigation.planner import PathPlanner
except Exception:
    DepthEstimator = None
    update_grid_from_frame = None
    OccupancyGrid = None
    VisualOdometry = None
    PathPlanner = None
from offline_utils import configure_offline_env, ensure_local_model

OFFLINE_MODE = configure_offline_env()
try:
    from ultralytics import YOLO
except Exception:
    YOLO = None
try:
    import torch
except Exception:
    torch = None

from core.config import load_config

COLORS = {
    "background": "#0B0F16",
    "panel": "#111827",
    "border": "#1F2937",
    "accent": "#22D3EE",
    "success": "#22C55E",
    "warning": "#FACC15",
    "danger": "#EF4444",
    "danger_dark": "#991B1B",
    "text": "#E5E7EB",
    "muted": "#94A3B8",
}


class Panel(tk.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        tk.Label(
            self,
            text=title,
            fg=COLORS["muted"],
            bg=COLORS["panel"],
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=12, pady=(8, 6))


class TopBar(tk.Frame):
    def __init__(self, parent, status_var, model_var, gpu_var, uptime_var):
        super().__init__(parent, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        tk.Label(
            self,
            text="WVAB Autonomous Navigation Dashboard",
            fg=COLORS["text"],
            bg=COLORS["panel"],
            font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT, padx=12, pady=10)

        right = tk.Frame(self, bg=COLORS["panel"])
        right.pack(side=tk.RIGHT, padx=12)
        self._pill(right, status_var, COLORS["success"])
        self._pill(right, model_var, COLORS["accent"])
        self._pill(right, gpu_var, COLORS["accent"])
        self._pill(right, uptime_var, COLORS["accent"])

    def _pill(self, parent, var, color):
        lbl = tk.Label(parent, textvariable=var, fg=color, bg=COLORS["panel"], font=("Segoe UI", 9, "bold"))
        lbl.pack(side=tk.LEFT, padx=6)
        return lbl


class ModelStatusPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Model & Stream Status")
        self.yolo_var = tk.StringVar(value="YOLO Model: -")
        self.depth_var = tk.StringVar(value="Depth Model: -")
        self.stream_var = tk.StringVar(value="Streaming: -")
        for var in (self.yolo_var, self.depth_var, self.stream_var):
            tk.Label(self, textvariable=var, fg=COLORS["text"], bg=COLORS["panel"], font=("Segoe UI", 10)).pack(
                anchor="w", padx=12, pady=4
            )


class ObjectListPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Detected Objects")
        self.listbox = tk.Listbox(self, bg=COLORS["panel"], fg=COLORS["text"], highlightthickness=0, relief="flat")
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))


class DepthPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Depth Map")
        self.preview = tk.Label(self, text="Depth Visualization", fg=COLORS["muted"], bg=COLORS["panel"])
        self.preview.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))


class CameraPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Live Camera Feed")
        self.preview = tk.Label(self, bg="black")
        self.preview.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))


class NavigationPanel(Panel):
    def __init__(self, parent, start_cb, pause_cb, stop_cb, emergency_cb):
        super().__init__(parent, "Navigation Controls")
        grid = tk.Frame(self, bg=COLORS["panel"])
        grid.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        for i in range(2):
            grid.grid_columnconfigure(i, weight=1)
        tk.Button(grid, text="START", bg=COLORS["success"], fg="white", command=start_cb).grid(
            row=0, column=0, padx=6, pady=6, sticky="ew"
        )
        tk.Button(grid, text="PAUSE", bg=COLORS["warning"], fg="#111827", command=pause_cb).grid(
            row=0, column=1, padx=6, pady=6, sticky="ew"
        )
        tk.Button(grid, text="STOP", bg=COLORS["danger"], fg="white", command=stop_cb).grid(
            row=1, column=0, padx=6, pady=6, sticky="ew"
        )
        tk.Button(grid, text="EMERGENCY STOP", bg=COLORS["danger_dark"], fg="white", command=emergency_cb).grid(
            row=1, column=1, padx=6, pady=6, sticky="ew"
        )


class MetricsPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Metrics")
        self.metrics_var = tk.StringVar(value="Camera FPS: - | SLAM FPS: - | CPU: - | GPU: - | RAM: -")
        tk.Label(self, textvariable=self.metrics_var, fg=COLORS["text"], bg=COLORS["panel"], font=("Segoe UI", 10)).pack(
            anchor="w", padx=12, pady=6
        )


class GoalPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Goal Status")
        self.goal_var = tk.StringVar(value="Goal: (5.0, 0.0)")
        self.dist_var = tk.StringVar(value="Distance: 4.2m")
        self.state_var = tk.StringVar(value="State: NAVIGATING")
        for var in (self.goal_var, self.dist_var, self.state_var):
            tk.Label(self, textvariable=var, fg=COLORS["text"], bg=COLORS["panel"], font=("Segoe UI", 10)).pack(
                anchor="w", padx=12, pady=4
            )


class MapPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Localization & Map")
        self.map_preview = tk.Label(self, text="Occupancy Grid + Path Overlay", fg=COLORS["muted"], bg=COLORS["panel"])
        self.map_preview.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))


class StatusBar(Panel):
    def __init__(self, parent, audio_var=None):
        super().__init__(parent, "System Status")
        self.leds = {}
        for label in ("AI ACTIVE", "SLAM ACTIVE", "DOCKER READY", "STREAMING ACTIVE"):
            row = tk.Frame(self, bg=COLORS["panel"])
            row.pack(anchor="w", padx=12, pady=2, fill=tk.X)
            led = tk.Canvas(row, width=10, height=10, bg=COLORS["panel"], highlightthickness=0)
            led.create_oval(1, 1, 9, 9, fill=COLORS["success"], outline="")
            led.pack(side=tk.LEFT)
            tk.Label(row, text=label, fg=COLORS["success"], bg=COLORS["panel"], font=("Segoe UI", 9, "bold")).pack(
                side=tk.LEFT, padx=6
            )
            self.leds[label] = led
        self.risk_var = tk.StringVar(value="Status: NORMAL")
        tk.Label(self, textvariable=self.risk_var, fg=COLORS["warning"], bg=COLORS["panel"], font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=12, pady=(6, 2)
        )
        self.audio_var = audio_var if audio_var is not None else tk.StringVar(value='Audio: "..."')
        tk.Label(self, textvariable=self.audio_var, fg=COLORS["accent"], bg=COLORS["panel"], font=("Segoe UI", 10)).pack(
            anchor="w", padx=12, pady=(8, 4)
        )


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
        self.config = self._load_config()

        self.model_path = model_path
        self.language = (language or "en").strip().lower()
        self.speech_language = self.language
        self.labels_path = labels_path
        self.logger = self._setup_logger()
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
        self.default_focal_length_px = float(self._cfg("camera.focal_length_px", 700.0))
        self.depth_scale_m = float(self._cfg("perception.depth.scale_m", 5.0))
        self.goal_distance_m = float(self._cfg("navigation.goal_distance_m", 5.0))
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
        self.start_time = time.time()
        self.paused = False
        self.status_var = tk.StringVar(value="Initializing...")
        self.sys_status_var = tk.StringVar(value="OFFLINE")
        self.uptime_var = tk.StringVar(value="00:00:00")
        self.model_status_var = tk.StringVar(value="Model: Not loaded")
        self.gpu_var = tk.StringVar(value="GPU: N/A")
        self.audio_msg_var = tk.StringVar(value='Audio: "..."')

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
        self.unicode_overlay_ok = self.overlay_font is not None
        self.overlay_language = self.language if self.unicode_overlay_ok else "en"
        self.depth_estimator = DepthEstimator(model_name="midas_small", device="auto", logger=self.logger, trust_repo=True) if DepthEstimator else None
        self.depth_error_shown = False
        if self.depth_estimator and getattr(self.depth_estimator, "model", None) is None:
            err = getattr(self.depth_estimator, "last_error", None)
            if err:
                self.status_var.set(f"Depth unavailable: {err}")
                self.depth_error_shown = True
        self.depth_every_n = 6
        self.map_every_n = 4
        self.map_frame_count = 0
        self.depth_frame_count = 0
        self.last_depth_map = None
        self.occupancy_grid = None
        self.visual_odometry = None
        self.path_planner = None
        self.last_pose = (0.0, 0.0, 0.0)
        self.last_path = []
        self.last_slam_fps = 0.0
        if OccupancyGrid and VisualOdometry and PathPlanner:
            self.occupancy_grid = OccupancyGrid(width_m=20.0, height_m=20.0, resolution=0.1, origin=(-10.0, -10.0))
            self.visual_odometry = VisualOdometry(600.0, 600.0, 320.0, 180.0)
            self.path_planner = PathPlanner(allow_diagonal=True, smooth=True)

        self._build_ui()
        # Start in windowed mode; allow users to toggle manually if desired.
        self.root.attributes("-fullscreen", False)
        self.source_var.set(str(camera_source))
        self._load_model()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.auto_restart = True

    def _build_ui(self):
        self.root.configure(bg=COLORS["background"])
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.bind("<Configure>", self._on_resize)

        self.preview_target_w = 960
        self.preview_target_h = 540

        TopBar(self.root, self.sys_status_var, self.model_status_var, self.gpu_var, self.uptime_var).grid(
            row=0, column=0, sticky="ew", padx=16, pady=(16, 8)
        )

        main = tk.Frame(self.root, bg=COLORS["background"])
        main.grid(row=1, column=0, sticky="nsew", padx=16)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=3)
        main.grid_columnconfigure(2, weight=1)
        main.grid_rowconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=0)

        left = tk.Frame(main, bg=COLORS["background"], width=260)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_propagate(False)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        self.model_panel = ModelStatusPanel(left)
        self.model_panel.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.object_panel = ObjectListPanel(left)
        self.object_panel.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.depth_panel = DepthPanel(left)
        self.depth_panel.grid(row=2, column=0, sticky="ew")
        self.detect_box = self.object_panel.listbox

        center = tk.Frame(main, bg=COLORS["background"])
        center.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        center.grid_rowconfigure(0, weight=1)
        center.grid_columnconfigure(0, weight=1)

        self.camera_panel = CameraPanel(center)
        self.camera_panel.grid(row=0, column=0, sticky="nsew")
        self.preview = self.camera_panel.preview

        right = tk.Frame(main, bg=COLORS["background"], width=280)
        right.grid(row=0, column=2, sticky="nsew")
        right.grid_propagate(False)
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        NavigationPanel(
            right,
            start_cb=self.start_camera,
            pause_cb=self.toggle_pause,
            stop_cb=self.stop_camera,
            emergency_cb=self.emergency_stop,
        ).grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.metrics_panel = MetricsPanel(right)
        self.metrics_panel.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.metrics_var = self.metrics_panel.metrics_var
        self.goal_panel = GoalPanel(right)
        self.goal_panel.grid(row=2, column=0, sticky="nsew")

        bottom = tk.Frame(self.root, bg=COLORS["background"])
        bottom.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 16))
        bottom.grid_columnconfigure(0, weight=2)
        bottom.grid_columnconfigure(1, weight=1)

        self.map_panel = MapPanel(bottom)
        self.map_panel.grid(row=0, column=0, sticky="ew")
        self.map_preview = self.map_panel.map_preview
        self.status_bar = StatusBar(bottom, audio_var=self.audio_msg_var)
        self.status_bar.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        self.status_var = tk.StringVar(value="Idle")
        self.object_var = tk.StringVar(value="Objects: No real objects yet")

        controls = tk.Frame(
            self.root,
            bg=COLORS["panel"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        controls.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))
        tk.Label(
            controls,
            text="WVAB Control Bar",
            fg=COLORS["muted"],
            bg=COLORS["panel"],
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=10)
        tk.Label(
            controls,
            text="Camera Source (0 / URL):",
            fg=COLORS["muted"],
            bg=COLORS["panel"],
        ).pack(side=tk.LEFT, padx=(6, 0))
        self.source_var = tk.StringVar(value="0")
        tk.Entry(
            controls,
            textvariable=self.source_var,
            width=32,
            bg=COLORS["background"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        ).pack(side=tk.LEFT, padx=6, pady=8)

        btn_style = {
            "bg": COLORS["border"],
            "fg": COLORS["text"],
            "activebackground": COLORS["accent"],
            "activeforeground": "#0B0F16",
            "relief": "flat",
            "padx": 10,
            "pady": 4,
        }
        primary_style = {**btn_style, "bg": COLORS["accent"], "fg": "#0B0F16"}
        danger_style = {**btn_style, "bg": COLORS["danger"], "fg": "white"}

        tk.Button(controls, text="Real Test (5s)", command=self.start_real_test, **primary_style).pack(
            side=tk.LEFT, padx=4, pady=6
        )
        tk.Button(controls, text="Snapshot", command=self.save_snapshot, **btn_style).pack(
            side=tk.LEFT, padx=4, pady=6
        )
        tk.Button(controls, text="Record", command=self.toggle_recording, **btn_style).pack(
            side=tk.LEFT, padx=4, pady=6
        )
        self.ml_btn = tk.Button(controls, text="ML: OFF", command=self.toggle_ml, **btn_style)
        self.ml_btn.pack(side=tk.LEFT, padx=4, pady=6)
        self.audio_btn = tk.Button(controls, text="Audio: ON", command=self.toggle_audio, **btn_style)
        self.audio_btn.pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(controls, text="Test Audio", command=self.test_audio, **btn_style).pack(
            side=tk.LEFT, padx=4, pady=6
        )
        tk.Label(controls, text="Lang:", fg=COLORS["muted"], bg=COLORS["panel"]).pack(side=tk.LEFT, padx=(10, 3))
        self.lang_var = tk.StringVar(value=self.language)
        self.lang_menu = tk.OptionMenu(controls, self.lang_var, *self.available_languages, command=self.set_language)
        self.lang_menu.configure(bg=COLORS["border"], fg=COLORS["text"], activebackground=COLORS["accent"])
        self.lang_menu.pack(side=tk.LEFT, padx=2, pady=6)
        tk.Button(controls, text="Exit", command=self.on_close, **danger_style).pack(side=tk.RIGHT, padx=8, pady=6)

    def _load_config(self):
        try:
            return load_config("config/config.yaml")
        except Exception:
            return {}

    def _cfg(self, path, default=None):
        data = self.config
        for key in path.split("."):
            if not isinstance(data, dict):
                return default
            data = data.get(key)
        return default if data is None else data

    def _on_resize(self, _event):
        if self.preview is None:
            return
        w = max(self.preview.winfo_width(), 1)
        h = max(self.preview.winfo_height(), 1)
        if w > 1 and h > 1:
            self.preview_target_w = w
            self.preview_target_h = h

    def _load_model(self):
        if YOLO is None:
            self.status_var.set("Ultralytics not installed. ML disabled.")
            self.ml_enabled = False
            self.ml_btn.configure(text="ML: OFF")
            self.model_status_var.set("Model: Unavailable")
            if hasattr(self, "model_panel"):
                self.model_panel.yolo_var.set("YOLO Model: Unavailable")
            return
        try:
            self.model = YOLO(ensure_local_model(self.model_path, offline=OFFLINE_MODE))
            self.ml_enabled = True
            self.ml_btn.configure(text="ML: ON")
            if torch and torch.cuda.is_available():
                self.yolo_device = "cuda"
            else:
                self.yolo_device = "cpu"
            self.object_labels = self._build_object_labels()
            self.status_var.set(f"ML model loaded: {self.model_path}")
            self.model_status_var.set(f"Model: {os.path.basename(self.model_path)}")
            if hasattr(self, "model_panel"):
                self.model_panel.yolo_var.set(f"YOLO Model: {os.path.basename(self.model_path)}")
            self.session_summary["model_loaded"] = True
            self.session_summary["defined_objects"] = len(self.object_labels)
        except Exception as exc:
            self.model = None
            self.ml_enabled = False
            self.ml_btn.configure(text="ML: OFF")
            self.status_var.set(f"Model load failed: {exc}")
            self.model_status_var.set("Model: Load failed")
            if hasattr(self, "model_panel"):
                self.model_panel.yolo_var.set("YOLO Model: Load failed")

    def _load_multilingual_labels(self, path):
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            self.logger.exception("Failed to load labels file '%s'", path)
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
        return requested_language

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
        self.overlay_font = self._load_overlay_font()
        self.unicode_overlay_ok = self.overlay_font is not None
        self.overlay_language = self.language if self.unicode_overlay_ok else "en"
        installed = self._detect_tts_languages()
        if self.language not in installed:
            self.status_var.set(
                f"Language set to: {self.language} (voice not installed, will attempt with default voice)"
            )
        else:
            self.status_var.set(f"Language set to: {self.language}")

    def translate_class_name(self, class_name, fallback_name, lang=None):
        lang = (lang or self.language).strip().lower()
        entry = self.multilingual_labels.get(class_name)
        if isinstance(entry, dict):
            return entry.get(lang, entry.get("en", fallback_name))
        return fallback_name

    def _localized_direction(self, direction, lang=None):
        lang = (lang or self.language).strip().lower()
        phrases = self.multilingual_labels.get("__phrases__", {})
        if isinstance(phrases, dict):
            lang_map = phrases.get(lang, {})
            if isinstance(lang_map, dict):
                maybe = lang_map.get(direction)
                if isinstance(maybe, str) and maybe.strip():
                    return maybe
        dmap = {
            "en": {"left": "left", "right": "right", "in front": "ahead"},
            "ru": {"left": "слева", "right": "справа", "in front": "спереди"},
            "bn": {"left": "বামে", "right": "ডানে", "in front": "সামনে"},
        }
        table = dmap.get(lang, dmap["en"])
        return table.get(direction, direction)

    def _localized_distance(self, distance, lang=None):
        lang = (lang or self.language).strip().lower()
        phrases = self.multilingual_labels.get("__phrases__", {})
        if isinstance(phrases, dict):
            lang_map = phrases.get(lang, {})
            if isinstance(lang_map, dict):
                maybe = lang_map.get(distance)
                if isinstance(maybe, str) and maybe.strip():
                    return maybe
        dmap = {
            "en": {"too far": "far", "close": "close", "very close": "very close"},
            "ru": {"too far": "далеко", "close": "близко", "very close": "очень близко"},
            "bn": {"too far": "দূরে", "close": "কাছে", "very close": "খুব কাছে"},
        }
        table = dmap.get(lang, dmap["en"])
        return table.get(distance, distance)

    def _build_localized_object_phrase(self, object_name, direction, distance, lang=None):
        lang = (lang or self.language).strip().lower()
        if isinstance(distance, tuple):
            distance_label, _distance_m = distance
        else:
            distance_label, _distance_m = distance, None
        text = f"{object_name} {self._localized_direction(direction, lang=lang)}"
        if _distance_m is not None:
            if _distance_m <= 1.0:
                text = f"{text} {self._localized_distance('very close', lang=lang)} {self._localized_number(1, lang)} {self._localized_meter(lang)}"
            else:
                bucket = self._bucket_distance_m(_distance_m)
                if bucket is not None:
                    text = f"{text} {self._localized_number(bucket, lang)} {self._localized_meter(lang)}"
        else:
            fallback_bucket = None
            if distance_label == "very close":
                text = f"{text} {self._localized_distance('very close', lang=lang)} {self._localized_number(1, lang)} {self._localized_meter(lang)}"
            elif distance_label == "close":
                fallback_bucket = 5
            elif distance_label == "too far":
                fallback_bucket = 15
            if fallback_bucket is not None:
                text = f"{text} {self._localized_number(fallback_bucket, lang)} {self._localized_meter(lang)}"
            elif distance_label in ("close", "very close"):
                text = f"{text} {self._localized_distance(distance_label, lang=lang)}"
        return text

    def _localized_meter(self, lang):
        lang = (lang or self.language).strip().lower()
        meter_map = {
            "en": "meter",
            "ru": "метр",
            "bn": "মিটার",
            "hi": "मीटर",
            "es": "metro",
            "fr": "mètre",
            "ar": "متر",
        }
        return meter_map.get(lang, "meter")

    def _localized_number(self, value, lang):
        lang = (lang or self.language).strip().lower()
        num_map = {
            "en": {1: "1", 5: "5", 10: "10", 15: "15", 20: "20", 25: "25", 30: "30", 40: "40", 50: "50", 75: "75", 100: "100"},
            "ru": {1: "adin", 5: "peyet", 10: "decit", 15: "pitnatchet", 20: "dbaset", 25: "dbasetpeyet", 30: "treeset", 40: "sorok", 50: "pitdisat", 75: "siyamdisatpayat", 100: "sto"},
            "bn": {1: "এক", 5: "পাঁচ", 10: "দশ", 15: "পনেরো", 20: "বিশ", 25: "পঁচিশ", 30: "ত্রিশ", 40: "চল্লিশ", 50: "পঞ্চাশ", 75: "পঁচাত্তর", 100: "একশ"},
            "hi": {1: "एक", 5: "पांच", 10: "दस", 15: "पंद्रह", 20: "बीस", 25: "पच्चीस", 30: "तीस", 40: "चालीस", 50: "पचास", 75: "पचहत्तर", 100: "सौ"},
            "es": {1: "uno", 5: "cinco", 10: "diez", 15: "quince", 20: "veinte", 25: "veinticinco", 30: "treinta", 40: "cuarenta", 50: "cincuenta", 75: "setenta y cinco", 100: "cien"},
            "fr": {1: "un", 5: "cinq", 10: "dix", 15: "quinze", 20: "vingt", 25: "vingt-cinq", 30: "trente", 40: "quarante", 50: "cinquante", 75: "soixante-quinze", 100: "cent"},
            "ar": {1: "واحد", 5: "خمسة", 10: "عشرة", 15: "خمسة عشر", 20: "عشرون", 25: "خمسة وعشرون", 30: "ثلاثون", 40: "أربعون", 50: "خمسون", 75: "خمسة وسبعون", 100: "مئة"},
        }
        return num_map.get(lang, num_map["en"]).get(value, str(value))

    def _build_speech_phrase(self, detection, lang=None):
        lang = (lang or self.language).strip().lower()
        class_name, _pretty_name, direction, distance_label, _conf, _bbox, distance_m = detection
        default_name = self.object_labels.get(class_name, class_name.replace("_", " ").strip().title())
        name = self.translate_class_name(class_name, default_name, lang=lang)
        dir_text = self._localized_direction(direction, lang=lang)
        meter_text = self._localized_meter(lang)
        if distance_m is not None and distance_m <= 1.0:
            dist_text = self._localized_distance("very close", lang=lang)
            return f"{name} {dir_text} {dist_text} {self._localized_number(1, lang)} {meter_text}"
        if distance_m is not None:
            bucket = self._bucket_distance_m(distance_m)
            if bucket is not None:
                return f"{name} {dir_text} {self._localized_number(bucket, lang)} {meter_text}"
        if distance_label == "very close":
            dist_text = self._localized_distance("very close", lang=lang)
            return f"{name} {dir_text} {dist_text} {self._localized_number(1, lang)} {meter_text}"
        if distance_label == "close":
            return f"{name} {dir_text} {self._localized_number(5, lang)} {meter_text}"
        if distance_label == "too far":
            return f"{name} {dir_text} {self._localized_number(15, lang)} {meter_text}"
        return f"{name} {dir_text}"

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
                os.path.join(os.path.dirname(__file__), "assets", "fonts", "NotoSansBengali-Regular.ttf"),
                "C:/Windows/Fonts/Nirmala.ttf",
                "C:/Windows/Fonts/kalpurush.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansBengaliUI-Regular.ttf",
            ]
        elif lang.startswith("hi"):
            font_candidates += [
                os.path.join(os.path.dirname(__file__), "assets", "fonts", "NotoSansDevanagari-Regular.ttf"),
                "C:/Windows/Fonts/Mangal.ttf",
                "C:/Windows/Fonts/Nirmala.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
            ]
        elif lang.startswith("ar"):
            font_candidates += [
                os.path.join(os.path.dirname(__file__), "assets", "fonts", "NotoNaskhArabic-Regular.ttf"),
                "C:/Windows/Fonts/arialuni.ttf",
                "C:/Windows/Fonts/Traditional Arabic.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
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
            cv2.putText(frame, self._overlay_safe_text(text), (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 2)
            return frame
        try:
            mask = self.overlay_font.getmask(text)
            if mask is None or mask.getbbox() is None:
                cv2.putText(frame, self._overlay_safe_text(text), (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 2)
                return frame
        except Exception:
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
                self.logger.exception("[AUDIO][GUI] speech failed")
                self._set_status_threadsafe("Audio failed. Check TTS/voices or audio device.")
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

    def _set_status_threadsafe(self, text):
        try:
            self.root.after(0, lambda: self.status_var.set(text))
        except Exception:
            pass

    def test_audio(self):
        if not self.audio_enabled:
            self.status_var.set("Audio is OFF. Turn it ON first.")
            return
        self.status_var.set("Audio test queued")
        self.speak_priority("Audio test")

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
        self.sys_status_var.set("ONLINE")
        self.last_loop_time = time.time()
        try:
            self.update_frame()
        except Exception as exc:
            self.logger.exception("Camera loop error: %s", exc)
            if self.auto_restart:
                self.root.after(500, self.start_camera)

    def stop_camera(self):
        self.camera_running = False
        self.sys_status_var.set("OFFLINE")
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

    def _bucket_distance_m(self, distance_m):
        if distance_m is None:
            return None
        if distance_m <= 5.0:
            return 5
        if distance_m <= 10.0:
            return 10
        if distance_m <= 15.0:
            return 15
        if distance_m <= 20.0:
            return 20
        if distance_m <= 25.0:
            return 25
        if distance_m <= 30.0:
            return 30
        if distance_m <= 40.0:
            return 40
        if distance_m <= 50.0:
            return 50
        if distance_m <= 75.0:
            return 75
        if distance_m <= 100.0:
            return 100
        return 100

    def _detect_real_objects(self, frame):
        if not self.ml_enabled or self.model is None:
            return frame, []

        detections = []
        frame_keys = set()
        speech_candidates = []
        frame_h, frame_w = frame.shape[:2]
        # Use full-resolution frame to avoid bbox scale mismatch and improve accuracy
        infer_frame = frame
        device = self.yolo_device or "cpu"
        conf_thresh = float(self._cfg("camera.yolo.conf", 0.5))
        imgsz = int(self._cfg("camera.yolo.imgsz", 640))
        try:
            results = self.model(infer_frame, imgsz=imgsz, verbose=False, device=device)
        except Exception:
            results = self.model(infer_frame, imgsz=imgsz, verbose=False)
        for result in results:
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf < conf_thresh:
                    continue

                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]

                bbox = box.xyxy[0].cpu().numpy().astype(int)
                direction = self._object_direction(bbox, frame_w)
                distance, distance_m = self._object_distance(class_name, bbox, frame_w, frame_h)
                default_name = self.object_labels.get(
                    class_name, class_name.replace("_", " ").strip().title()
                )
                pretty_name = self.translate_class_name(class_name, default_name, lang=self.overlay_language)
                distance_suffix = f", {distance_m:.1f}m" if distance_m is not None else ""

                label = (
                    f"{pretty_name} {conf:.2f} "
                    f"{self._localized_direction(direction, lang=self.overlay_language)} "
                    f"{self._localized_distance(distance, lang=self.overlay_language)}{distance_suffix}"
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
            return "Stop"
        if center >= 2.0:
            if left + 0.3 < right:
                return "Left"
            if right + 0.3 < left:
                return "Right"
            return "Slow"
        if left + 0.2 < right:
            return "Left"
        if right + 0.2 < left:
            return "Right"
        return "Straight"

    def _translate_movement_instruction(self, instruction):
        mapping = {
            "Stop": {
                "en": "Stop",
                "ru": "СТОП",
                "bn": "থামুন",
                "hi": "रुकें",
                "es": "Alto",
                "fr": "Stop",
                "ar": "توقف",
            },
            "Left": {
                "en": "Left",
                "ru": "НАЛЕВО",
                "bn": "বামে",
                "hi": "बाएं",
                "es": "Izquierda",
                "fr": "À gauche",
                "ar": "يسار",
            },
            "Right": {
                "en": "Right",
                "ru": "НАПРАВО",
                "bn": "ডানে",
                "hi": "दाएं",
                "es": "Derecha",
                "fr": "À droite",
                "ar": "يمين",
            },
            "Slow": {
                "en": "Slow",
                "ru": "МЕДЛЕННЕЕ",
                "bn": "ধীরে",
                "hi": "धीरे",
                "es": "Despacio",
                "fr": "Lent",
                "ar": "ببطء",
            },
            "Straight": {
                "en": "Straight",
                "ru": "ПРЯМО",
                "bn": "সোজা",
                "hi": "सीधा",
                "es": "Recto",
                "fr": "Tout droit",
                "ar": "مستقيم",
            },
        }
        entry = mapping.get(instruction)
        if entry:
            return entry.get(self.language, entry.get("en", instruction))
        return instruction

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
            self.speak(self._translate_movement_instruction(instruction))

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

        if isinstance(self.detect_box, tk.Listbox):
            self.detect_box.delete(0, tk.END)
            for line in lines:
                self.detect_box.insert(tk.END, line)
        else:
            self.detect_box.configure(state=tk.NORMAL)
            self.detect_box.delete("1.0", tk.END)
            self.detect_box.insert(tk.END, "\n".join(lines))
            self.detect_box.configure(state=tk.DISABLED)

    def update_frame(self):
        if not self.camera_running or self.cap is None:
            return
        if self.paused:
            self.root.after(100, self.update_frame)
            return
        try:
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
            self._update_depth_preview(frame)
            self._update_map(frame, detections)
            frame = self._update_overlay_info(frame)
            if detections:
                first = detections[0]
                self.last_detect_text = self._build_localized_object_phrase(
                    first[1], first[2], (first[3], first[6]), lang=self.overlay_language
                )
                speech_text = self._build_speech_phrase(first, lang=self.language)
                self.maybe_speak_display_text(speech_text)
            else:
                self.last_detect_text = "No real objects yet"
            if detections and any(d[2] in ("very close", "close") for d in detections):
                if hasattr(self, "status_bar"):
                    self.status_bar.risk_var.set("⚠ OBSTACLE AHEAD")
            else:
                if hasattr(self, "status_bar"):
                    self.status_bar.risk_var.set("Status: NORMAL")
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
            target_w = max(int(self.preview_target_w), 1)
            target_h = max(int(self.preview_target_h), 1)
            display = cv2.resize(display, (target_w, target_h))
            image = Image.fromarray(display)
            image_tk = ImageTk.PhotoImage(image=image)
            self.preview.image_tk = image_tk
            self.preview.configure(image=image_tk)

            cpu = psutil.cpu_percent(interval=None) if psutil else None
            ram = psutil.virtual_memory().percent if psutil else None
            cam_fps = self.last_fps
            slam_fps = f"{self.last_slam_fps:.1f}" if self.last_slam_fps > 0 else "-"
            gpu = self._read_gpu_usage()
            self.metrics_var.set(
                f"Camera FPS: {cam_fps:.1f} | SLAM FPS: {slam_fps} | CPU: {cpu if cpu is not None else 'N/A'}% | GPU: {gpu} | RAM: {ram if ram is not None else 'N/A'}%"
            )
            self.object_var.set(f"Objects: {self.last_detect_text}")
            self.audio_msg_var.set(f'Audio: "{speech_text if detections else self.last_detect_text}"')
            self.sys_status_var.set("ONLINE")
            self.uptime_var.set(self._format_uptime(time.time() - self.start_time))
            self.root.after(15, self.update_frame)
        except Exception as exc:
            self.logger.exception("Update loop error: %s", exc)
            if self.auto_restart:
                self.root.after(500, self.update_frame)

    def _update_depth_preview(self, frame):
        if self.depth_estimator is None:
            return
        self.depth_frame_count += 1
        if self.depth_frame_count % self.depth_every_n != 0:
            return
        try:
            depth_map = self.depth_estimator.predict(frame)
            self.last_depth_map = depth_map
            if depth_map is None:
                if not self.depth_error_shown:
                    err = getattr(self.depth_estimator, "last_error", None)
                    msg = "Depth unavailable"
                    if err:
                        msg = f"Depth unavailable: {err}"
                    self.status_var.set(msg)
                    self.depth_error_shown = True
                depth_color = np.zeros((140, 240, 3), dtype=np.uint8)
                depth_color[:] = (25, 25, 25)
                cv2.putText(
                    depth_color,
                    "Depth unavailable",
                    (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )
            elif float(np.std(depth_map)) < 1e-6:
                depth_color = np.zeros((140, 240, 3), dtype=np.uint8)
                depth_color[:] = (25, 25, 25)
                cv2.putText(
                    depth_color,
                    "Depth unavailable",
                    (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )
            else:
                depth_norm = (depth_map * 255.0).clip(0, 255).astype(np.uint8)
                depth_color = cv2.applyColorMap(depth_norm, cv2.COLORMAP_TURBO)
            preview = cv2.resize(depth_color, (240, 140))
            preview = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(preview)
            image_tk = ImageTk.PhotoImage(image=image)
            self.depth_panel.preview.image_tk = image_tk
            self.depth_panel.preview.configure(image=image_tk)
        except Exception:
            return

    def _update_map(self, frame, detections):
        if not self.occupancy_grid or not update_grid_from_frame:
            img = np.zeros((160, 360, 3), dtype=np.uint8)
            img[:] = (20, 20, 24)
            cv2.putText(
                img,
                "Map unavailable",
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (180, 180, 180),
                1,
                cv2.LINE_AA,
            )
            image = Image.fromarray(img)
            image_tk = ImageTk.PhotoImage(image=image)
            self.map_panel.map_preview.image_tk = image_tk
            self.map_panel.map_preview.configure(image=image_tk)
            return
        self.map_frame_count += 1
        if self.map_frame_count % self.map_every_n != 0:
            return
        h, w = frame.shape[:2]
        fx = self.default_focal_length_px
        fy = self.default_focal_length_px
        cx = w / 2.0
        cy = h / 2.0
        intrinsics = {"fx": fx, "fy": fy, "cx": cx, "cy": cy}
        try:
            if self.last_depth_map is None and self.depth_estimator:
                self.last_depth_map = self.depth_estimator.predict(frame)
            if self.last_depth_map is None:
                img = np.zeros((160, 360, 3), dtype=np.uint8)
                img[:] = (20, 20, 24)
                cv2.putText(
                    img,
                    "Depth unavailable",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (180, 180, 180),
                    1,
                    cv2.LINE_AA,
                )
                image = Image.fromarray(img)
                image_tk = ImageTk.PhotoImage(image=image)
                self.map_panel.map_preview.image_tk = image_tk
                self.map_panel.map_preview.configure(image=image_tk)
                return
            update_grid_from_frame(
                [{"bbox": det[0], "class_name": det[1]} for det in detections],
                self.last_depth_map,
                self.occupancy_grid,
                intrinsics=intrinsics,
                depth_scale_m=self.depth_scale_m,
            )
            if self.visual_odometry:
                t0 = time.time()
                self.last_pose, _ = self.visual_odometry.update(frame, depth_map=self.last_depth_map)
                dt = max(time.time() - t0, 1e-6)
                self.last_slam_fps = 1.0 / dt
            if self.path_planner:
                start = self.occupancy_grid.world_to_grid(self.last_pose[0], self.last_pose[1])
                goal = self.occupancy_grid.world_to_grid(self.last_pose[0] + self.goal_distance_m, self.last_pose[1])
                self.last_path = self.path_planner.plan(self.occupancy_grid, start, goal)
            prob = self.occupancy_grid.to_prob()
            grid = (prob * 255.0).astype(np.uint8)
            img = cv2.cvtColor(grid, cv2.COLOR_GRAY2RGB)
            h, w = img.shape[:2]

            # Subtle grid overlay
            step = 10
            for x in range(0, w, step):
                cv2.line(img, (x, 0), (x, h), (40, 40, 48), 1)
            for y in range(0, h, step):
                cv2.line(img, (0, y), (w, y), (40, 40, 48), 1)

            # Draw path overlay if available
            if self.last_path:
                for i in range(1, len(self.last_path)):
                    x1, y1 = self.last_path[i - 1]
                    x2, y2 = self.last_path[i]
                    cv2.line(img, (x1, y1), (x2, y2), (0, 255, 255), 2)

            # Draw start and goal markers
            if self.last_path:
                sx, sy = self.last_path[0]
                gx, gy = self.last_path[-1]
                cv2.circle(img, (sx, sy), 4, (0, 255, 0), -1)
                cv2.circle(img, (gx, gy), 4, (255, 80, 80), -1)
            # Draw current pose at center
            cx = int(w / 2)
            cy = int(h / 2)
            cv2.circle(img, (cx, cy), 3, (120, 200, 255), -1)

            # Add legend
            cv2.rectangle(img, (6, 6), (120, 46), (15, 15, 18), -1)
            cv2.putText(img, "Path", (12, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
            cv2.putText(img, "Start", (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            cv2.putText(img, "Goal", (12, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 80, 80), 1)

            img = cv2.resize(img, (360, 160), interpolation=cv2.INTER_NEAREST)
            image = Image.fromarray(img)
            image_tk = ImageTk.PhotoImage(image=image)
            self.map_panel.map_preview.image_tk = image_tk
            self.map_panel.map_preview.configure(image=image_tk)
        except Exception:
            return

    def _update_overlay_info(self, frame):
        state_text = "ONLINE"
        nav_text = self.last_movement_announcement or "GO STRAIGHT"
        frame = self._draw_unicode_text(frame, f"FPS {self.last_fps:.1f}", 10, 25, (0, 255, 0))
        frame = self._draw_unicode_text(frame, f"STATE {state_text}", 10, 50, (0, 255, 0))
        self._draw_nav_arrow(frame, nav_text)
        return frame

    def _draw_nav_arrow(self, frame, nav_text):
        h, w = frame.shape[:2]
        center = (int(w * 0.5), int(h * 0.15))
        length = int(min(w, h) * 0.08)
        if "LEFT" in nav_text.upper():
            end = (center[0] - length, center[1])
        elif "RIGHT" in nav_text.upper():
            end = (center[0] + length, center[1])
        else:
            end = (center[0], center[1] + length)
        cv2.arrowedLine(frame, center, end, (0, 255, 255), 3, tipLength=0.4)

    def _read_gpu_usage(self):
        try:
            import subprocess
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                stderr=subprocess.DEVNULL,
            )
            val = out.decode("utf-8", "ignore").strip().splitlines()[0]
            return f"{val}%"
        except Exception:
            return "N/A"

    def _format_uptime(self, seconds):
        seconds = int(max(seconds, 0))
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def toggle_pause(self):
        self.paused = not self.paused
        state = "Paused" if self.paused else "Running"
        self.status_var.set(f"{state}")

    def pause_navigation(self):
        self.toggle_pause()

    def emergency_stop(self):
        self.stop_camera()

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

    def _setup_logger(self):
        log_path = os.environ.get("WVAB_GUI_LOG_PATH", "wvab_gui.log")
        level = os.environ.get("WVAB_LOG_LEVEL", "INFO").upper()
        logger = logging.getLogger("wvab_gui")
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


def run_camera_gui(
    camera_source=0,
    model_path=os.environ.get("WVAB_MODEL", "yolov8n.pt"),
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
    run_camera_gui(camera_source=0, model_path=os.environ.get("WVAB_MODEL", "yolov8n.pt"), language="en")


if __name__ == "__main__":
    main()
