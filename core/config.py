import os
from typing import Any, Iterable


def load_config(path):
    if not path:
        return {}
    try:
        import yaml
    except Exception as exc:
        raise RuntimeError("PyYAML is required for config files. Install pyyaml.") from exc
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise RuntimeError("Config root must be a mapping.")
    return data


def _get_path(data: dict[str, Any], path: Iterable[str]):
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            raise KeyError(".".join(path))
        current = current[key]
    return current


def validate_navigation_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Validate fields required by navigation_pipeline without inventing defaults."""
    required = [
        ("system", "log_dir"),
        ("system", "log_level"),
        ("camera", "source"),
        ("camera", "width"),
        ("camera", "height"),
        ("camera", "fps"),
        ("camera", "intrinsics", "fx"),
        ("camera", "intrinsics", "fy"),
        ("camera", "intrinsics", "cx"),
        ("camera", "intrinsics", "cy"),
        ("perception", "yolo_model"),
        ("perception", "confidence"),
        ("perception", "depth", "backend"),
        ("mapping", "occupancy_grid", "width_m"),
        ("mapping", "occupancy_grid", "height_m"),
        ("mapping", "occupancy_grid", "resolution"),
        ("planning", "allow_diagonal"),
        ("planning", "smooth_path"),
        ("navigation", "fallback_goal_relative"),
        ("navigation", "safety_state_file"),
    ]
    missing = []
    for path in required:
        try:
            _get_path(cfg, path)
        except KeyError:
            missing.append(".".join(path))
    if missing:
        raise RuntimeError("Navigation config missing required keys: " + ", ".join(missing))

    intr = _get_path(cfg, ("camera", "intrinsics"))
    for key in ("fx", "fy"):
        if float(intr[key]) <= 0:
            raise RuntimeError(f"camera.intrinsics.{key} must be > 0")

    depth_cfg = _get_path(cfg, ("perception", "depth"))
    if bool(depth_cfg.get("metric_calibrated", False)):
        scale = depth_cfg.get("scale_m")
        if scale is None or float(scale) <= 0:
            raise RuntimeError("perception.depth.scale_m must be > 0 when metric_calibrated=true")

    fallback = _get_path(cfg, ("navigation", "fallback_goal_relative"))
    if not isinstance(fallback, (list, tuple)) or len(fallback) != 2:
        raise RuntimeError("navigation.fallback_goal_relative must contain [x, y]")
    return cfg
