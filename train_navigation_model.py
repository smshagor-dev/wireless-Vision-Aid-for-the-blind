#!/usr/bin/env python3
"""Reproducible WVAB YOLO training, validation, and export CLI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from offline_utils import configure_offline_env, ensure_local_model
from training.runtime_validation import (
    require_export_backend,
    require_non_negative,
    require_positive,
    validate_dataset_yaml,
)


def _configure_runtime(allow_online: bool) -> bool:
    if allow_online:
        os.environ["WVAB_OFFLINE"] = "0"
    else:
        os.environ.setdefault("WVAB_OFFLINE", "1")
    return configure_offline_env()


def _load_yolo():
    from ultralytics import YOLO

    return YOLO


def _resolve_model(model_path: str, *, offline: bool) -> str:
    return ensure_local_model(model_path, offline=offline)


def _load_language_map(path: str) -> dict[str, Any]:
    if not path:
        return {}
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"language map not found: {resolved}")
    with resolved.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("language map root must be a JSON object")
    return data


def _save_multilingual_labels(model, labels_out: str, language_map: dict[str, Any]) -> None:
    names = model.names if hasattr(model, "names") else {}
    if isinstance(names, list):
        names = {index: name for index, name in enumerate(names)}

    labels: dict[str, dict[str, dict[str, str]]] = {"classes": {}}
    for index, class_name in names.items():
        entry = {"en": str(class_name)}
        mapped = language_map.get(str(class_name))
        if isinstance(mapped, dict):
            for language, translation in mapped.items():
                if isinstance(language, str) and isinstance(translation, str) and translation.strip():
                    entry[language.strip().lower()] = translation.strip()
        elif isinstance(mapped, str) and mapped.strip():
            entry["custom"] = mapped.strip()
        labels["classes"][str(index)] = entry

    output = Path(labels_out).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(labels, handle, ensure_ascii=False, indent=2)


def _validate_common(args: argparse.Namespace) -> None:
    require_positive("imgsz", args.imgsz)
    require_positive("batch", args.batch)


def run_train(args: argparse.Namespace) -> None:
    _validate_common(args)
    require_positive("epochs", args.epochs)
    require_non_negative("workers", args.workers)
    require_non_negative("patience", args.patience)
    require_positive("lr0", args.lr0)
    require_non_negative("freeze", args.freeze)
    if args.save_period < -1:
        raise ValueError("save-period must be -1 or >= 0")

    validate_dataset_yaml(args.data, require_train=True)
    offline = _configure_runtime(args.allow_online)
    model_path = _resolve_model(args.model, offline=offline)
    YOLO = _load_yolo()
    model = YOLO(model_path)
    model.train(
        data=str(Path(args.data).expanduser().resolve()),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        workers=args.workers,
        patience=args.patience,
        lr0=args.lr0,
        optimizer=args.optimizer,
        freeze=args.freeze,
        cache=args.cache,
        amp=args.amp,
        save_period=args.save_period,
        resume=args.resume,
        seed=args.seed,
        deterministic=args.deterministic,
    )

    best_model_path = Path(args.project) / args.name / "weights" / "best.pt"
    if not best_model_path.exists():
        raise RuntimeError(f"training finished without expected best checkpoint: {best_model_path}")

    trained_model = YOLO(str(best_model_path.resolve()))
    language_map = _load_language_map(args.language_map)
    _save_multilingual_labels(trained_model, args.labels_out, language_map)

    print("Training complete")
    print(f"Best model: {best_model_path.resolve()}")
    print(f"Multilingual labels: {Path(args.labels_out).expanduser().resolve()}")


def run_val(args: argparse.Namespace) -> None:
    _validate_common(args)
    validate_dataset_yaml(args.data, require_train=False)
    offline = _configure_runtime(args.allow_online)
    model_path = _resolve_model(args.model, offline=offline)
    YOLO = _load_yolo()
    model = YOLO(model_path)
    metrics = model.val(
        data=str(Path(args.data).expanduser().resolve()),
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
    )
    print("Validation complete")
    print(metrics)


def run_export(args: argparse.Namespace) -> None:
    require_positive("imgsz", args.imgsz)
    export_format = require_export_backend(args.format, simplify=args.simplify)
    offline = _configure_runtime(args.allow_online)
    model_path = _resolve_model(args.model, offline=offline)
    YOLO = _load_yolo()
    model = YOLO(model_path)
    export_kwargs = {
        "format": export_format,
        "imgsz": args.imgsz,
        "half": args.half,
        "device": args.device,
    }
    if export_format in {"onnx", "engine"}:
        export_kwargs["simplify"] = args.simplify
    output = model.export(**export_kwargs)
    print("Export complete")
    print(f"Exported: {output}")


def _add_online_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-online",
        action="store_true",
        help="Explicitly allow Ultralytics to use network resources. Offline is the default.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WVAB reproducible YOLO training utility")
    sub = parser.add_subparsers(dest="command", required=True)

    train = sub.add_parser("train", help="Train/fine-tune a local model")
    train.add_argument("--data", required=True, help="Local dataset YAML path")
    train.add_argument("--model", default="yolov8n.pt", help="Local base model checkpoint")
    train.add_argument("--epochs", type=int, default=80)
    train.add_argument("--imgsz", type=int, default=640)
    train.add_argument("--batch", type=int, default=16)
    train.add_argument("--device", default="cpu", help="cpu / 0 / 0,1")
    train.add_argument("--project", default="runs/wvab")
    train.add_argument("--name", default="navigation")
    train.add_argument("--workers", type=int, default=4)
    train.add_argument("--patience", type=int, default=30)
    train.add_argument("--lr0", type=float, default=0.01)
    train.add_argument("--optimizer", default="auto", choices=["auto", "SGD", "Adam", "AdamW"])
    train.add_argument("--freeze", type=int, default=0)
    train.add_argument("--cache", action="store_true")
    train.add_argument("--amp", action=argparse.BooleanOptionalAction, default=True)
    train.add_argument("--save-period", type=int, default=-1)
    train.add_argument("--resume", action="store_true")
    train.add_argument("--seed", type=int, default=42)
    train.add_argument("--deterministic", action=argparse.BooleanOptionalAction, default=True)
    train.add_argument("--language-map", default="", help="Optional local JSON translation map")
    train.add_argument("--labels-out", default="runs/wvab/multilingual_labels.json")
    _add_online_flag(train)

    val = sub.add_parser("val", help="Validate a local model")
    val.add_argument("--model", required=True)
    val.add_argument("--data", required=True)
    val.add_argument("--imgsz", type=int, default=640)
    val.add_argument("--batch", type=int, default=16)
    val.add_argument("--device", default="cpu")
    _add_online_flag(val)

    export = sub.add_parser("export", help="Export a local model")
    export.add_argument("--model", required=True)
    export.add_argument("--format", default="onnx", choices=["onnx", "openvino", "engine"])
    export.add_argument("--imgsz", type=int, default=640)
    export.add_argument("--half", action="store_true")
    export.add_argument("--simplify", action="store_true", help="Use onnxslim for ONNX/TensorRT export")
    export.add_argument("--device", default="cpu")
    _add_online_flag(export)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "train":
            run_train(args)
        elif args.command == "val":
            run_val(args)
        elif args.command == "export":
            run_export(args)
        else:
            parser.error("unknown command")
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
