#!/usr/bin/env python3
"""Summarize WVAB soak CSV evidence without making safety claims."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import statistics


NUMERIC_FIELDS = (
    "elapsed_s",
    "health_age_s",
    "fps",
    "latency_ms",
    "frames_total",
    "last_completed_frame_s",
    "rss_mb",
    "cpu_percent",
    "system_cpu_percent",
    "system_memory_percent",
    "temperature_c",
)


def numeric(values):
    result = []
    for value in values:
        if value in (None, ""):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            result.append(number)
    return result


def percentile(values, fraction):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * float(fraction)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def rounded(value):
    return None if value is None else round(float(value), 3)


def summarize_rows(rows):
    if not rows:
        raise ValueError("evidence CSV contains no samples")

    columns = {field: numeric(row.get(field) for row in rows) for field in NUMERIC_FIELDS}
    elapsed = columns["elapsed_s"]
    latency = columns["latency_ms"]
    fps = columns["fps"]
    rss = columns["rss_mb"]
    health_age = columns["health_age_s"]
    frame_idle = columns["last_completed_frame_s"]
    temperature = columns["temperature_c"]
    errors = [row.get("health_error", "").strip() for row in rows]

    result = {
        "samples": len(rows),
        "duration_s": rounded(max(elapsed) - min(elapsed)) if elapsed else None,
        "health_error_samples": sum(1 for item in errors if item),
        "latency_ms": {
            "p50": rounded(percentile(latency, 0.50)),
            "p95": rounded(percentile(latency, 0.95)),
            "p99": rounded(percentile(latency, 0.99)),
            "max": rounded(max(latency)) if latency else None,
        },
        "fps": {
            "min": rounded(min(fps)) if fps else None,
            "median": rounded(statistics.median(fps)) if fps else None,
            "max": rounded(max(fps)) if fps else None,
        },
        "health": {
            "max_record_age_s": rounded(max(health_age)) if health_age else None,
            "max_completed_frame_idle_s": rounded(max(frame_idle)) if frame_idle else None,
        },
        "memory": {
            "rss_first_mb": rounded(rss[0]) if rss else None,
            "rss_last_mb": rounded(rss[-1]) if rss else None,
            "rss_max_mb": rounded(max(rss)) if rss else None,
            "rss_growth_mb": rounded(rss[-1] - rss[0]) if len(rss) >= 2 else None,
        },
        "temperature_c": {
            "max": rounded(max(temperature)) if temperature else None,
            "median": rounded(statistics.median(temperature)) if temperature else None,
        },
    }
    return result


def load_rows(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_parser():
    parser = argparse.ArgumentParser(description="Summarize WVAB soak evidence CSV")
    parser.add_argument("csv", help="CSV produced by tools/soak_monitor.py")
    parser.add_argument("--json", dest="json_path", default=None, help="Optional JSON output path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    path = Path(args.csv).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"evidence CSV not found: {path}")
    try:
        summary = summarize_rows(load_rows(path))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    text = json.dumps(summary, indent=2, sort_keys=True)
    print(text)
    if args.json_path:
        destination = Path(args.json_path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text + "\n", encoding="utf-8")
        print(f"Summary saved: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
