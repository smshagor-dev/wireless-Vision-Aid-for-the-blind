"""
WVAB YOLO training utility with multilingual label support.

Examples:
  Train:
    python train_navigation_model.py train --data data/wvab.yaml --model yolov8n.pt --epochs 80

  Validate:
    python train_navigation_model.py val --model runs/wvab/navigation/weights/best.pt --data data/wvab.yaml

  Export:
    python train_navigation_model.py export --model runs/wvab/navigation/weights/best.pt --format onnx
"""

import argparse
import json
import os
from typing import Dict, Any

from ultralytics import YOLO


def _load_language_map(path: str) -> Dict[str, Any]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_multilingual_labels(model: YOLO, labels_out: str, language_map: Dict[str, Any]) -> None:
    names = model.names if hasattr(model, "names") else {}
    if isinstance(names, list):
        names = {i: n for i, n in enumerate(names)}

    labels = {"classes": {}}
    for idx, class_name in names.items():
        entry = {"en": str(class_name)}
        if str(class_name) in language_map:
            mapped = language_map[str(class_name)]
            if isinstance(mapped, dict):
                entry.update(mapped)
            elif isinstance(mapped, str):
                entry["custom"] = mapped
        labels["classes"][str(idx)] = entry

    os.makedirs(os.path.dirname(labels_out) or ".", exist_ok=True)
    with open(labels_out, "w", encoding="utf-8") as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)


def run_train(args: argparse.Namespace) -> None:
    model = YOLO(args.model)
    model.train(
        data=args.data,
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
    )

    best_model_path = os.path.join(args.project, args.name, "weights", "best.pt")
    trained_model = YOLO(best_model_path if os.path.exists(best_model_path) else args.model)
    lang_map = _load_language_map(args.language_map)
    _save_multilingual_labels(trained_model, args.labels_out, lang_map)

    print("=" * 60)
    print("Training complete")
    print(f"Best model: {best_model_path}")
    print(f"Multilingual labels: {args.labels_out}")
    print("=" * 60)


def run_val(args: argparse.Namespace) -> None:
    model = YOLO(args.model)
    metrics = model.val(data=args.data, imgsz=args.imgsz, batch=args.batch, device=args.device)
    print("=" * 60)
    print("Validation complete")
    print(metrics)
    print("=" * 60)


def run_export(args: argparse.Namespace) -> None:
    model = YOLO(args.model)
    output = model.export(format=args.format, imgsz=args.imgsz, half=args.half, device=args.device)
    print("=" * 60)
    print("Export complete")
    print(f"Exported: {output}")
    print("=" * 60)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WVAB YOLO trainer with multilingual support")
    sub = parser.add_subparsers(dest="command", required=True)

    train = sub.add_parser("train", help="Train/fine-tune a model")
    train.add_argument("--data", required=True, help="Dataset YAML path")
    train.add_argument("--model", default="yolov8n.pt", help="Base model checkpoint")
    train.add_argument("--epochs", type=int, default=80, help="Training epochs")
    train.add_argument("--imgsz", type=int, default=640, help="Image size")
    train.add_argument("--batch", type=int, default=16, help="Batch size")
    train.add_argument("--device", default="cpu", help="cpu / 0 / 0,1")
    train.add_argument("--project", default="runs/wvab", help="Output project directory")
    train.add_argument("--name", default="navigation", help="Run name")
    train.add_argument("--workers", type=int, default=4, help="Dataloader workers")
    train.add_argument("--patience", type=int, default=30, help="Early stopping patience")
    train.add_argument("--lr0", type=float, default=0.01, help="Initial learning rate")
    train.add_argument("--optimizer", default="auto", help="Optimizer: auto/SGD/Adam/AdamW")
    train.add_argument("--freeze", type=int, default=0, help="Freeze first N layers")
    train.add_argument("--cache", default=False, action="store_true", help="Cache images")
    train.add_argument("--amp", default=True, action="store_true", help="Mixed precision")
    train.add_argument("--save-period", type=int, default=-1, help="Checkpoint save period")
    train.add_argument("--resume", default=False, action="store_true", help="Resume last training")
    train.add_argument(
        "--language-map",
        default="",
        help="Optional JSON: class_name -> {'bn': '...', 'es': '...'}",
    )
    train.add_argument(
        "--labels-out",
        default="runs/wvab/multilingual_labels.json",
        help="Output JSON for multilingual class labels",
    )

    val = sub.add_parser("val", help="Validate a model")
    val.add_argument("--model", required=True, help="Model path to validate")
    val.add_argument("--data", required=True, help="Dataset YAML path")
    val.add_argument("--imgsz", type=int, default=640, help="Image size")
    val.add_argument("--batch", type=int, default=16, help="Batch size")
    val.add_argument("--device", default="cpu", help="cpu / 0 / 0,1")

    export = sub.add_parser("export", help="Export model")
    export.add_argument("--model", required=True, help="Model path to export")
    export.add_argument("--format", default="onnx", help="Export format (onnx/engine/openvino/...)")
    export.add_argument("--imgsz", type=int, default=640, help="Image size")
    export.add_argument("--half", default=False, action="store_true", help="FP16 export when supported")
    export.add_argument("--device", default="cpu", help="cpu / 0")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "train":
        run_train(args)
    elif args.command == "val":
        run_val(args)
    elif args.command == "export":
        run_export(args)
    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    main()
