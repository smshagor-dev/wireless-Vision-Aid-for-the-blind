from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class ProximityEstimate:
    label: str
    meters: Optional[float]
    source: str


def classify_bbox_proximity(
    bbox: Sequence[float],
    frame_shape: Sequence[int],
) -> ProximityEstimate:
    """Return a qualitative proximity class without pretending it is metric depth."""
    if len(bbox) < 4 or len(frame_shape) < 2:
        raise ValueError("bbox and frame_shape are invalid")
    frame_height = float(frame_shape[0])
    if frame_height <= 0:
        raise ValueError("frame height must be positive")
    bbox_height = max(0.0, float(bbox[3]) - float(bbox[1]))
    ratio = bbox_height / frame_height
    if ratio > 0.60:
        label = "immediate"
    elif ratio > 0.40:
        label = "close"
    elif ratio > 0.20:
        label = "medium"
    else:
        label = "far"
    return ProximityEstimate(label=label, meters=None, source="bbox-relative")


def estimate_metric_distance(
    bbox: Sequence[float],
    focal_length_px: float,
    object_height_m: float,
) -> ProximityEstimate:
    """Estimate pinhole-camera distance only when explicit calibration is supplied."""
    pixel_height = max(0.0, float(bbox[3]) - float(bbox[1]))
    if pixel_height <= 0:
        raise ValueError("bounding box height must be positive")
    if focal_length_px <= 0 or object_height_m <= 0:
        raise ValueError("focal length and object height must be positive")
    meters = (float(object_height_m) * float(focal_length_px)) / pixel_height
    if meters < 1.0:
        label = "immediate"
    elif meters < 2.0:
        label = "close"
    elif meters < 4.0:
        label = "medium"
    else:
        label = "far"
    return ProximityEstimate(label=label, meters=meters, source="pinhole-calibrated")
