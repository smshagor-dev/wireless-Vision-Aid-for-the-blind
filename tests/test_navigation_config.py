import pytest

from core.config import validate_navigation_config


def _config():
    return {
        "system": {"log_dir": "logs", "log_level": "INFO"},
        "camera": {
            "source": 0,
            "width": 640,
            "height": 480,
            "fps": 30,
            "intrinsics": {
                "fx": 600.0,
                "fy": 600.0,
                "cx": 320.0,
                "cy": 240.0,
                "calibrated": False,
            },
        },
        "perception": {
            "yolo_model": "yolov8n.pt",
            "confidence": 0.5,
            "depth": {"backend": "MiDaS_small", "metric_calibrated": False, "scale_m": None},
        },
        "mapping": {
            "occupancy_grid": {"width_m": 20.0, "height_m": 20.0, "resolution": 0.1}
        },
        "planning": {"allow_diagonal": True, "smooth_path": True},
        "navigation": {"fallback_goal_relative": [5.0, 0.0], "safety_state_file": "state.json"},
    }


def test_metric_depth_requires_calibrated_intrinsics():
    cfg = _config()
    cfg["perception"]["depth"].update({"metric_calibrated": True, "scale_m": 5.0})
    with pytest.raises(RuntimeError, match="intrinsics.calibrated"):
        validate_navigation_config(cfg)


def test_metric_depth_accepts_explicit_coherent_calibration():
    cfg = _config()
    cfg["camera"]["intrinsics"]["calibrated"] = True
    cfg["perception"]["depth"].update({"metric_calibrated": True, "scale_m": 5.0})
    assert validate_navigation_config(cfg) is cfg


def test_confidence_must_be_probability():
    cfg = _config()
    cfg["perception"]["confidence"] = 1.5
    with pytest.raises(RuntimeError, match="perception.confidence"):
        validate_navigation_config(cfg)


def test_grid_dimensions_must_be_positive():
    cfg = _config()
    cfg["mapping"]["occupancy_grid"]["resolution"] = 0
    with pytest.raises(RuntimeError, match="occupancy_grid.resolution"):
        validate_navigation_config(cfg)
