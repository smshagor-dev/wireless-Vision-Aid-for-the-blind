import json

import numpy as np
import pytest

from core.config import validate_navigation_config
from core.font_paths import overlay_font_candidates
from core.proximity import classify_bbox_proximity, estimate_metric_distance
from core.safety import SafetyStatePublisher
from core.security import normalize_control_host, resolve_control_token, verify_secret
from mapping.occupancy_grid import OccupancyGrid
from navigation.a_star import a_star
from perception.perception_mapping import detections_to_points
from tools.download_models import sha256_file
from training.runtime_validation import (
    require_non_negative,
    require_positive,
    validate_dataset_yaml,
    validate_export_format,
)


def _valid_config():
    return {
        "system": {"log_dir": "logs", "log_level": "INFO"},
        "camera": {
            "source": 0,
            "width": 640,
            "height": 480,
            "fps": 30,
            "intrinsics": {"fx": 600.0, "fy": 600.0, "cx": 320.0, "cy": 240.0},
        },
        "perception": {
            "yolo_model": "yolov8n.pt",
            "confidence": 0.5,
            "depth": {"backend": "MiDaS_small", "metric_calibrated": False, "scale_m": None},
        },
        "mapping": {"occupancy_grid": {"width_m": 20.0, "height_m": 20.0, "resolution": 0.1}},
        "planning": {"allow_diagonal": True, "smooth_path": True},
        "navigation": {"fallback_goal_relative": [5.0, 0.0], "safety_state_file": "state.json"},
    }


def test_navigation_config_rejects_missing_keys():
    cfg = _valid_config()
    del cfg["camera"]["intrinsics"]["fx"]
    with pytest.raises(RuntimeError, match="camera.intrinsics.fx"):
        validate_navigation_config(cfg)


def test_navigation_config_requires_scale_when_metric_depth_enabled():
    cfg = _valid_config()
    cfg["perception"]["depth"]["metric_calibrated"] = True
    with pytest.raises(RuntimeError, match="scale_m"):
        validate_navigation_config(cfg)


def test_bbox_proximity_is_explicitly_non_metric():
    estimate = classify_bbox_proximity((0, 0, 100, 350), (480, 640, 3))
    assert estimate.label == "immediate"
    assert estimate.meters is None
    assert estimate.source == "bbox-relative"


def test_metric_distance_requires_explicit_calibration_inputs():
    estimate = estimate_metric_distance((0, 0, 100, 300), 600.0, 1.7)
    assert estimate.meters == pytest.approx(3.4)
    assert estimate.source == "pinhole-calibrated"


def test_bengali_font_candidates_include_bundled_font():
    assert overlay_font_candidates("bn")[0].endswith("assets/fonts/NotoSansBengali-Regular.ttf")


def test_arabic_font_candidates_include_bundled_font():
    assert overlay_font_candidates("ar")[0].endswith("assets/fonts/NotoNaskhArabic-Regular.ttf")


def test_control_security_defaults_to_loopback_and_requires_secret():
    assert normalize_control_host(None) == "127.0.0.1"
    assert resolve_control_token("", "udp-secret") == "udp-secret"
    assert verify_secret("udp-secret", "udp-secret") is True
    assert verify_secret("wrong", "udp-secret") is False
    assert verify_secret("anything", "") is False


def test_model_checksum_helper(tmp_path):
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"abc")
    assert sha256_file(sample) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_depth_mapping_handles_unavailable_depth():
    assert detections_to_points([], None, {"fx": 1, "fy": 1, "cx": 0, "cy": 0}) == []


def test_depth_mapping_projects_finite_points():
    depth = np.ones((10, 10), dtype=np.float32)
    detections = [{"bbox": (4, 4, 6, 6), "class_name": "person"}]
    points = detections_to_points(
        detections,
        depth,
        {"fx": 10.0, "fy": 10.0, "cx": 5.0, "cy": 5.0},
        depth_scale=2.0,
    )
    assert points == [(2.0, 0.0)]


def test_safety_state_publisher_is_atomic_and_fail_safe(tmp_path):
    path = tmp_path / "state.json"
    publisher = SafetyStatePublisher(str(path))
    publisher.stop("camera_missing", frame_age_s=2.0)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["state"] == "STOP"
    assert payload["reason"] == "camera_missing"
    assert payload["metadata"]["frame_age_s"] == 2.0


def test_a_star_avoids_occupied_cell():
    grid = OccupancyGrid(width_m=5, height_m=5, resolution=1.0, origin=(0, 0))
    grid.log_odds[2, 2] = 5.0
    path = a_star(grid, (0, 0), (4, 4), allow_diagonal=False)
    assert path
    assert (2, 2) not in path


def test_a_star_returns_empty_when_goal_is_blocked():
    grid = OccupancyGrid(width_m=3, height_m=3, resolution=1.0, origin=(0, 0))
    grid.log_odds[2, 2] = 5.0
    assert a_star(grid, (0, 0), (2, 2), allow_diagonal=True) == []


def test_training_numeric_validation_rejects_invalid_values():
    with pytest.raises(ValueError, match="epochs"):
        require_positive("epochs", 0)
    with pytest.raises(ValueError, match="workers"):
        require_non_negative("workers", -1)


def test_export_format_validation_is_allowlisted():
    assert validate_export_format("OpenVINO") == "openvino"
    assert validate_export_format("engine") == "engine"
    with pytest.raises(ValueError, match="unsupported export format"):
        validate_export_format("saved_model")


def test_dataset_yaml_requires_real_local_splits(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dataset_root = tmp_path / "data" / "custom_wvab"
    (dataset_root / "images" / "train").mkdir(parents=True)
    (dataset_root / "images" / "val").mkdir(parents=True)
    yaml_path = tmp_path / "dataset.yaml"
    yaml_path.write_text(
        "path: data/custom_wvab\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n"
        "  0: person\n",
        encoding="utf-8",
    )
    data = validate_dataset_yaml(str(yaml_path), require_train=True)
    assert data["names"][0] == "person"


def test_dataset_yaml_fails_closed_when_split_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "custom_wvab" / "images" / "train").mkdir(parents=True)
    yaml_path = tmp_path / "dataset.yaml"
    yaml_path.write_text(
        "path: data/custom_wvab\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n"
        "  0: person\n",
        encoding="utf-8",
    )
    with pytest.raises(FileNotFoundError, match="val split"):
        validate_dataset_yaml(str(yaml_path), require_train=True)
