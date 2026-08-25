#!/usr/bin/env python3
"""Record WVAB runtime health and host/process telemetry to CSV.

This tool records evidence; it does not declare a deployment field-safe.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time


FIELDS = [
    "timestamp_utc",
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
    "health_error",
]


def parse_health(path: Path, now_wall: float) -> dict:
    if not path.exists():
        return {"health_error": "missing"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"health_error": f"invalid:{type(exc).__name__}"}
    if not isinstance(payload, dict):
        return {"health_error": "invalid:root"}

    result = {"health_error": ""}
    try:
        result["health_age_s"] = max(0.0, now_wall - float(payload["ts"]))
    except (KeyError, TypeError, ValueError):
        result["health_age_s"] = ""
    for source, target in (
        ("fps", "fps"),
        ("latency_ms", "latency_ms"),
        ("frames_total", "frames_total"),
        ("last_completed_frame_s", "last_completed_frame_s"),
    ):
        value = payload.get(source, "")
        result[target] = value if isinstance(value, (int, float)) else ""
    return result


def read_temperature_c(psutil_module) -> float | str:
    try:
        groups = psutil_module.sensors_temperatures(fahrenheit=False) or {}
    except (AttributeError, OSError):
        return ""
    preferred = ("cpu_thermal", "coretemp", "k10temp", "soc_thermal")
    names = [name for name in preferred if name in groups]
    names.extend(name for name in groups if name not in names)
    for name in names:
        for sensor in groups.get(name, []):
            current = getattr(sensor, "current", None)
            if isinstance(current, (int, float)):
                return round(float(current), 2)
    return ""


def process_metrics(psutil_module, process) -> dict:
    result = {
        "rss_mb": "",
        "cpu_percent": "",
        "system_cpu_percent": round(float(psutil_module.cpu_percent(interval=None)), 2),
        "system_memory_percent": round(float(psutil_module.virtual_memory().percent), 2),
        "temperature_c": read_temperature_c(psutil_module),
    }
    if process is None:
        return result
    try:
        result["rss_mb"] = round(process.memory_info().rss / (1024 * 1024), 2)
        result["cpu_percent"] = round(float(process.cpu_percent(interval=None)), 2)
    except psutil_module.Error:
        pass
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record WVAB health/process/system soak-test evidence to CSV"
    )
    parser.add_argument(
        "--health",
        default="wvab_udp_server_health.json",
        help="WVAB JSON health file to sample",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="CSV output path; default: evidence/soak-<UTC timestamp>.csv",
    )
    parser.add_argument("--pid", type=int, default=None, help="Optional WVAB process PID")
    parser.add_argument("--interval", type=float, default=5.0, help="Sampling interval in seconds")
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Total duration in seconds; 0 records until interrupted",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.interval < 0.5:
        raise SystemExit("--interval must be at least 0.5 seconds")
    if args.duration < 0:
        raise SystemExit("--duration must be non-negative")
    if args.pid is not None and args.pid <= 0:
        raise SystemExit("--pid must be a positive integer")

    try:
        import psutil
    except ImportError as exc:
        raise SystemExit("psutil is required; install requirements.txt") from exc

    health_path = Path(args.health).expanduser().resolve()
    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_path = (Path.cwd() / "evidence" / f"soak-{stamp}.csv").resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    process = None
    if args.pid is not None:
        try:
            process = psutil.Process(args.pid)
            process.cpu_percent(interval=None)
        except psutil.Error as exc:
            raise SystemExit(f"could not open PID {args.pid}: {exc}") from exc
    psutil.cpu_percent(interval=None)

    started = time.monotonic()
    print(f"Recording WVAB soak evidence to {output_path}")
    print(f"Health source: {health_path}")
    if args.duration:
        print(f"Duration: {args.duration:.1f}s; interval: {args.interval:.1f}s")
    else:
        print(f"Interval: {args.interval:.1f}s; press Ctrl+C to stop")

    try:
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            while True:
                now_mono = time.monotonic()
                elapsed = now_mono - started
                if args.duration and elapsed > args.duration and elapsed > 0:
                    break
                now_wall = time.time()
                row = {
                    "timestamp_utc": datetime.fromtimestamp(now_wall, timezone.utc).isoformat(),
                    "elapsed_s": round(elapsed, 3),
                }
                row.update(parse_health(health_path, now_wall))
                row.update(process_metrics(psutil, process))
                writer.writerow({field: row.get(field, "") for field in FIELDS})
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError:
                    pass
                remaining = args.interval
                while remaining > 0:
                    step = min(remaining, 0.25)
                    time.sleep(step)
                    remaining -= step
    except KeyboardInterrupt:
        print("Stopped by user; partial evidence file was preserved.")

    print(f"Evidence saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
