#!/usr/bin/env python3
"""Build and validate the offline WVAB Android ONNX model.

The source checkpoint is the repository-pinned ``yolov8n.pt``. The resulting
ONNX graph is generated into the Flutter asset directory before an APK build.
No runtime model download is permitted by the Android application.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import onnx
from ultralytics import YOLO, __version__ as ultralytics_version


FLUTTER_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = FLUTTER_ROOT.parents[1]
SOURCE_MODEL = REPO_ROOT / "yolov8n.pt"
ASSET_DIR = FLUTTER_ROOT / "assets" / "models"
OUTPUT_MODEL = ASSET_DIR / "yolov8n_320.onnx"
MANIFEST = FLUTTER_ROOT / ".generated" / "mobile_model_manifest.json"
INPUT_SIZE = 320
EXPECTED_CLASSES = 80
EXPECTED_CHANNELS = 4 + EXPECTED_CLASSES


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def static_shape(value_info: onnx.ValueInfoProto) -> list[int | None]:
    dims: list[int | None] = []
    for dim in value_info.type.tensor_type.shape.dim:
        dims.append(int(dim.dim_value) if dim.HasField("dim_value") and dim.dim_value > 0 else None)
    return dims


def validate_graph(path: Path) -> dict[str, object]:
    model = onnx.load(str(path), load_external_data=False)
    onnx.checker.check_model(model)
    if len(model.graph.input) != 1:
        raise RuntimeError(f"Expected one model input, found {len(model.graph.input)}")
    if not model.graph.output:
        raise RuntimeError("ONNX model has no outputs")

    input_shape = static_shape(model.graph.input[0])
    output_shape = static_shape(model.graph.output[0])
    if input_shape != [1, 3, INPUT_SIZE, INPUT_SIZE]:
        raise RuntimeError(f"Unexpected ONNX input shape: {input_shape}")
    if len(output_shape) != 3 or output_shape[0] != 1:
        raise RuntimeError(f"Unexpected ONNX output rank/shape: {output_shape}")
    if EXPECTED_CHANNELS not in output_shape[1:]:
        raise RuntimeError(
            f"Expected raw YOLO detection output with {EXPECTED_CHANNELS} channels, got {output_shape}"
        )
    return {"input_shape": input_shape, "output_shape": output_shape}


def main() -> None:
    if not SOURCE_MODEL.is_file() or SOURCE_MODEL.stat().st_size < 1_000_000:
        raise SystemExit(f"Pinned source model is missing or invalid: {SOURCE_MODEL}")

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MODEL.unlink(missing_ok=True)

    model = YOLO(str(SOURCE_MODEL))
    exported = Path(
        model.export(
            format="onnx",
            imgsz=INPUT_SIZE,
            batch=1,
            dynamic=False,
            simplify=False,
            half=False,
            opset=17,
            nms=False,
            device="cpu",
        )
    ).resolve()
    if not exported.is_file():
        raise RuntimeError(f"Ultralytics did not produce the expected ONNX file: {exported}")

    if exported != OUTPUT_MODEL.resolve():
        shutil.copyfile(exported, OUTPUT_MODEL)
    if OUTPUT_MODEL.stat().st_size < 1_000_000:
        raise RuntimeError("Generated mobile ONNX model is unexpectedly small")

    graph = validate_graph(OUTPUT_MODEL)
    manifest = {
        "schema_version": 1,
        "source": str(SOURCE_MODEL.relative_to(REPO_ROOT)),
        "source_sha256": sha256(SOURCE_MODEL),
        "asset": str(OUTPUT_MODEL.relative_to(FLUTTER_ROOT)),
        "asset_sha256": sha256(OUTPUT_MODEL),
        "asset_size": OUTPUT_MODEL.stat().st_size,
        "input_size": INPUT_SIZE,
        "classes": EXPECTED_CLASSES,
        "ultralytics": ultralytics_version,
        "onnx": onnx.__version__,
        **graph,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
