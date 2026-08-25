"""Canonical object-name normalization and assistive hazard priority policy."""

from __future__ import annotations

import re


def normalize_class_name(name: str) -> str:
    """Normalize model labels across COCO/custom naming conventions."""
    text = str(name or "").strip().lower().replace("&", " and ")
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    aliases = {
        "trafficlight": "traffic_light",
        "stopsign": "stop_sign",
        "roadcone": "road_cone",
        "pottedplant": "potted_plant",
    }
    return aliases.get(text, text)


# Lower number = higher spoken priority. The policy intentionally includes the
# custom WVAB mobility classes that are absent from generic COCO.
MOBILITY_PRIORITIES = {
    "person": 1,
    "car": 1,
    "truck": 1,
    "bus": 1,
    "motorcycle": 1,
    "bicycle": 2,
    "stairs": 2,
    "curb": 2,
    "pothole": 2,
    "pole": 2,
    "road_cone": 2,
    "crosswalk": 3,
    "traffic_light": 3,
    "stop_sign": 3,
    "door": 3,
    "chair": 4,
    "bench": 4,
    "potted_plant": 4,
}


class CriticalObjectPolicy(dict):
    """Dict-compatible priority map with normalized lookup semantics.

    `UDPVisionServer` historically uses both `name in critical_objects` and
    `critical_objects.get(name, default)`. Subclassing dict preserves that API
    while making custom `traffic_light` and COCO `traffic light` equivalent.
    """

    def __init__(self, priorities=None):
        source = MOBILITY_PRIORITIES if priorities is None else priorities
        super().__init__((normalize_class_name(key), int(value)) for key, value in source.items())

    def __contains__(self, key):
        return super().__contains__(normalize_class_name(key))

    def __getitem__(self, key):
        return super().__getitem__(normalize_class_name(key))

    def get(self, key, default=None):
        return super().get(normalize_class_name(key), default)


def label_candidates(name: str):
    """Return normalized + COCO-space variants for multilingual label lookup."""
    raw = str(name or "").strip()
    normalized = normalize_class_name(raw)
    space_variant = normalized.replace("_", " ")
    candidates = []
    for candidate in (raw, normalized, space_variant):
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates
