#!/usr/bin/env python3
"""Deterministic WVAB host diagnostics.

This tool validates software/runtime prerequisites without requiring Internet
access and without making a field-safety claim. Hardware checks are opt-in.
"""

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
import time

from core.config import load_config, validate_navigation_config
from offline_utils import configure_offline_env, ensure_local_model


ROOT = Path(__file__).resolve().parent
OFFLINE_MODE = configure_offline_env()
MIDAS_PATH = ROOT / "data" / "models" / "midas_v21_small_256.pt"
MIDAS_SHA256 = "70d6b9c891758c67f974a6097fb0c608c7ee67fb81ac3e5588847d5596d56fca"


class Doctor:
    def __init__(self):
        self.results = []

    def _add(self, name, status, message, required=True):
        status = status.upper()
        item = {"name": name, "status": status, "message": str(message), "required": bool(required)}
        self.results.append(item)
        print(f"{status:4} | {name}: {message}")
        return status != "FAIL"

    def passed(self, name, message, required=True):
        return self._add(name, "PASS", message, required)

    def warn(self, name, message):
        return self._add(name, "WARN", message, required=False)

    def fail(self, name, message, required=True):
        return self._add(name, "FAIL", message, required)

    def check_python(self):
        current = sys.version_info[:3]
        if current >= (3, 10, 0):
            return self.passed("Python", ".".join(map(str, current)))
        return self.fail("Python", f"{current[0]}.{current[1]}.{current[2]} detected; Python 3.10+ is required")

    def check_imports(self):
        modules = {
            "cv2": "OpenCV",
            "numpy": "NumPy",
            "ultralytics": "Ultralytics",
            "torch": "PyTorch",
            "torchvision": "TorchVision",
            "timm": "timm",
            "PIL": "Pillow",
            "yaml": "PyYAML",
            "pyttsx3": "pyttsx3",
            "Crypto": "PyCryptodome",
            "websockets": "websockets",
            "psutil": "psutil",
            "prometheus_client": "prometheus-client",
        }
        missing = []
        for module_name, label in modules.items():
            try:
                importlib.import_module(module_name)
            except Exception as exc:
                missing.append(f"{label}: {exc}")
        if missing:
            return self.fail("Runtime imports", "; ".join(missing))
        return self.passed("Runtime imports", f"{len(modules)} base dependencies import successfully")

    def check_offline_policy(self):
        if OFFLINE_MODE and os.environ.get("ULTRALYTICS_OFFLINE") == "1":
            return self.passed("Offline policy", "offline-first mode enabled")
        if not OFFLINE_MODE:
            return self.warn("Offline policy", "WVAB_OFFLINE=0 permits network-backed model operations")
        return self.fail("Offline policy", "offline mode did not configure Ultralytics offline behavior")

    def check_config(self):
        try:
            cfg = validate_navigation_config(load_config(str(ROOT / "config" / "config.yaml")))
        except Exception as exc:
            return self.fail("Navigation config", exc)
        intr = cfg["camera"]["intrinsics"]
        depth = cfg["perception"]["depth"]
        if intr.get("calibrated") or depth.get("metric_calibrated"):
            return self.warn("Navigation config", "metric calibration flags are enabled; verify deployment calibration evidence")
        return self.passed("Navigation config", "valid; metric geometry remains disabled by default")

    def check_yolo_asset(self):
        try:
            model_path = Path(ensure_local_model("yolov8n.pt", offline=True))
        except Exception as exc:
            return self.fail("YOLO asset", exc)
        size = model_path.stat().st_size
        if size < 1_000_000:
            return self.fail("YOLO asset", f"unexpectedly small model file: {size} bytes")
        return self.passed("YOLO asset", f"local model present ({size / 1_000_000:.1f} MB)")

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def check_depth_asset(self):
        if not MIDAS_PATH.exists():
            return self.warn("MiDaS asset", "optional depth model is not provisioned")
        actual = self._sha256(MIDAS_PATH)
        if actual != MIDAS_SHA256:
            return self.fail("MiDaS asset", "checksum mismatch; delete and reprovision with tools/download_models.py")
        return self.passed("MiDaS asset", "optional depth weight checksum verified", required=False)

    @staticmethod
    def _parse_env(path):
        values = {}
        for raw in Path(path).read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
        return values

    @staticmethod
    def _valid_key_hex(value):
        return bool(re.fullmatch(r"(?:[0-9A-Fa-f]{32}|[0-9A-Fa-f]{48}|[0-9A-Fa-f]{64})", value or ""))

    def check_device_pair(self, required=False):
        header = ROOT / "esp32_secrets.h"
        env_file = ROOT / "deployment" / "rpi" / "wvab_edge.env"
        if not header.exists() and not env_file.exists():
            message = "device credentials not generated; run tools/generate_device_secrets.py before ESP32/Pi deployment"
            return self.fail("Device credential pair", message) if required else self.warn("Device credential pair", message)
        if header.exists() != env_file.exists():
            return self.fail("Device credential pair", "only one side of the ESP32/Pi credential pair exists")
        try:
            header_text = header.read_text(encoding="utf-8")
            env = self._parse_env(env_file)
        except Exception as exc:
            return self.fail("Device credential pair", exc)
        if not re.search(r"#define\s+WVAB_SECRETS_CONFIGURED\s+1\b", header_text):
            return self.fail("Device credential pair", "ESP32 header is not marked configured")
        if env.get("WVAB_UDP_AUTH") != "1" or env.get("WVAB_UDP_ENCRYPT") != "1":
            return self.fail("Device credential pair", "UDP authentication/encryption must both be enabled")
        if not self._valid_key_hex(env.get("WVAB_UDP_KEY_HEX")):
            return self.fail("Device credential pair", "Raspberry Pi AES key is missing or malformed")
        if len(env.get("WVAB_UDP_TOKEN", "")) < 16:
            return self.fail("Device credential pair", "Raspberry Pi UDP token is too short")
        if len(env.get("WVAB_WS_TOKEN", "")) < 16:
            return self.fail("Device credential pair", "WebSocket token is too short")
        return self.passed("Device credential pair", "local ESP32/Pi credential files pass structural checks", required=required)

    def check_environment_udp_credentials(self):
        key = os.environ.get("WVAB_UDP_KEY_HEX", "")
        token = os.environ.get("WVAB_UDP_TOKEN", "")
        if not key and not token:
            return self.warn("UDP environment", "no process-level UDP credentials exported")
        if not self._valid_key_hex(key):
            return self.fail("UDP environment", "WVAB_UDP_KEY_HEX is missing or malformed")
        if len(token) < 16:
            return self.fail("UDP environment", "WVAB_UDP_TOKEN must be at least 16 characters")
        return self.passed("UDP environment", "process-level credentials are structurally valid", required=False)

    def check_camera(self, source):
        try:
            cv2 = importlib.import_module("cv2")
            camera_source = int(source) if str(source).isdigit() else source
            cap = cv2.VideoCapture(camera_source)
            if not cap.isOpened():
                cap.release()
                return self.fail("Camera", f"could not open {source}")
            frame = None
            for _ in range(5):
                ok, candidate = cap.read()
                if ok and candidate is not None:
                    frame = candidate
                    break
                time.sleep(0.05)
            cap.release()
            if frame is None:
                return self.fail("Camera", f"opened {source} but no frame was captured")
            return self.passed("Camera", f"captured {frame.shape[1]}x{frame.shape[0]} frame from {source}")
        except Exception as exc:
            return self.fail("Camera", exc)

    def check_full_inference(self):
        try:
            np = importlib.import_module("numpy")
            YOLO = importlib.import_module("ultralytics").YOLO
            model_path = ensure_local_model("yolov8n.pt", offline=True)
            model = YOLO(model_path)
            frame = np.zeros((320, 320, 3), dtype=np.uint8)
            output = model(frame, verbose=False)
            if not output:
                return self.fail("YOLO inference", "model returned no result container")
            return self.passed("YOLO inference", "local model completed deterministic dummy-frame inference")
        except Exception as exc:
            return self.fail("YOLO inference", exc)

    def check_tts_engine(self):
        try:
            pyttsx3 = importlib.import_module("pyttsx3")
            engine = pyttsx3.init()
            engine.stop()
            return self.passed("TTS engine", "engine initialized; audible output was not asserted", required=False)
        except Exception as exc:
            return self.warn("TTS engine", f"engine unavailable on this host: {exc}")

    def summary(self):
        required_failures = [r for r in self.results if r["required"] and r["status"] == "FAIL"]
        warnings = [r for r in self.results if r["status"] == "WARN"]
        passes = [r for r in self.results if r["status"] == "PASS"]
        print("\n" + "=" * 72)
        print(f"WVAB doctor: {len(passes)} passed, {len(warnings)} warnings, {len(required_failures)} required failures")
        if required_failures:
            print("FAIL: required diagnostic checks did not pass.")
        else:
            print("PASS: required software diagnostics passed. This does not establish field safety.")
        print("=" * 72)
        return len(required_failures) == 0


def main():
    parser = argparse.ArgumentParser(description="Run offline-first WVAB host diagnostics")
    parser.add_argument("--camera", help="Optional camera index or trusted local stream URL to verify")
    parser.add_argument("--full", action="store_true", help="Also load YOLO and run a dummy inference")
    parser.add_argument("--tts", action="store_true", help="Also initialize the host TTS engine without speaking")
    parser.add_argument("--deployment", action="store_true", help="Require generated ESP32/Raspberry Pi credential files")
    parser.add_argument("--json-report", help="Optional path for a machine-readable diagnostic report")
    args = parser.parse_args()

    print("WVAB System Doctor")
    print("Offline-first diagnostics; no Internet connectivity check is required.\n")

    doctor = Doctor()
    doctor.check_python()
    doctor.check_imports()
    doctor.check_offline_policy()
    doctor.check_config()
    doctor.check_yolo_asset()
    doctor.check_depth_asset()
    doctor.check_device_pair(required=args.deployment)
    doctor.check_environment_udp_credentials()
    if args.camera is not None:
        doctor.check_camera(args.camera)
    else:
        doctor.warn("Camera", "not checked; pass --camera 0 or a trusted local stream URL")
    if args.full:
        doctor.check_full_inference()
    if args.tts:
        doctor.check_tts_engine()

    ok = doctor.summary()
    if args.json_report:
        report_path = Path(args.json_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps({"ok": ok, "results": doctor.results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Report written to {report_path}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
