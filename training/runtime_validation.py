from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


SUPPORTED_EXPORT_FORMATS = {"onnx", "openvino", "engine"}


def require_positive(name: str, value: int | float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be > 0")


def require_non_negative(name: str, value: int | float) -> None:
    if value < 0:
        raise ValueError(f"{name} must be >= 0")


def resolve_existing_path(path: str, label: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"{label} not found: {resolved}")
    return resolved


def validate_dataset_yaml(path: str, *, require_train: bool = False) -> dict[str, Any]:
    yaml_path = resolve_existing_path(path, "dataset YAML")
    with yaml_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("dataset YAML root must be a mapping")

    names = data.get("names")
    if not isinstance(names, (dict, list)) or not names:
        raise ValueError("dataset YAML must define non-empty names")

    dataset_root = Path(data.get("path", ".")).expanduser()
    if not dataset_root.is_absolute():
        # Ultralytics resolves dataset path relative to the working directory for
        # this repository. Make that expectation explicit and deterministic.
        dataset_root = (Path.cwd() / dataset_root).resolve()

    required_splits = ["val"]
    if require_train:
        required_splits.insert(0, "train")
    for split in required_splits:
        split_value = data.get(split)
        if not isinstance(split_value, str) or not split_value.strip():
            raise ValueError(f"dataset YAML must define {split}")
        split_path = Path(split_value).expanduser()
        if not split_path.is_absolute():
            split_path = dataset_root / split_path
        if not split_path.exists():
            raise FileNotFoundError(
                f"dataset {split} split not found: {split_path}. "
                "Provision/prepare the dataset before training or validation."
            )

    return data


def validate_export_format(export_format: str) -> str:
    normalized = export_format.strip().lower()
    if normalized not in SUPPORTED_EXPORT_FORMATS:
        allowed = ", ".join(sorted(SUPPORTED_EXPORT_FORMATS))
        raise ValueError(f"unsupported export format '{export_format}'; choose one of: {allowed}")
    return normalized
