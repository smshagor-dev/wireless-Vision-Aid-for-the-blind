#!/usr/bin/env python3
"""Export a local WVAB YOLO model to explicitly requested accelerator formats."""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path

from offline_utils import configure_offline_env, ensure_local_model
from training.runtime_validation import require_positive, validate_export_format


def _configure_runtime(allow_online: bool) -> bool:
    if allow_online:
        os.environ["WVAB_OFFLINE"] = "0"
    else:
        os.environ.setdefault("WVAB_OFFLINE", "1")
    return configure_offline_env()


def _load_yolo():
    from ultralytics import YOLO

    return YOLO


def _require_export_backend(export_format: str) -> None:
    if export_format == "openvino" and importlib.util.find_spec("openvino") is None:
        raise RuntimeError(
            "OpenVINO export requested but openvino is not installed. "
            "Install requirements-accelerators.txt first."
        )
    if export_format == "engine":
        if importlib.util.find_spec("tensorrt") is None:
            raise RuntimeError("TensorRT export requested but tensorrt is not installed")
        try:
            import torch
        except Exception as exc:
            raise RuntimeError("PyTorch is required for TensorRT export") from exc
        if not torch.cuda.is_available():
            raise RuntimeError("TensorRT export requires a CUDA-capable runtime")


def export_model(model_path: str, export_format: str, *, imgsz: int, half: bool, device: str):
    normalized = validate_export_format(export_format)
    _require_export_backend(normalized)
    YOLO = _load_yolo()
    model = YOLO(model_path)
    return model.export(format=normalized, imgsz=imgsz, half=half, device=device)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WVAB explicit accelerator model exporter")
    parser.add_argument("--model", default=os.environ.get("WVAB_MODEL", "yolov8n.pt"))
    parser.add_argument(
        "--format",
        dest="formats",
        action="append",
        choices=["onnx", "openvino", "engine"],
        help="Export format. Repeat to export multiple formats. Default: openvino.",
    )
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--half", action="store_true")
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--allow-online",
        action="store_true",
        help="Explicitly allow network resources. Offline/local-model mode is the default.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        require_positive("imgsz", args.imgsz)
        offline = _configure_runtime(args.allow_online)
        model_path = ensure_local_model(args.model, offline=offline)
        formats = args.formats or ["openvino"]
        outputs = []
        for export_format in formats:
            output = export_model(
                model_path,
                export_format,
                imgsz=args.imgsz,
                half=args.half,
                device=args.device,
            )
            outputs.append((export_format, output))
        print(f"Source model: {Path(model_path).resolve() if Path(model_path).exists() else model_path}")
        for export_format, output in outputs:
            print(f"{export_format}: {output}")
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
