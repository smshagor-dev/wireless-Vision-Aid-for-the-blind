import pytest

from tools.summarize_soak import percentile, summarize_rows


def test_percentile_interpolates_deterministically():
    values = [10, 20, 30, 40, 50]
    assert percentile(values, 0.50) == 30
    assert percentile(values, 0.95) == pytest.approx(48)
    assert percentile(values, 0.99) == pytest.approx(49.6)


def test_soak_summary_reports_latency_memory_and_health():
    rows = [
        {
            "elapsed_s": "0",
            "health_age_s": "0.2",
            "fps": "12",
            "latency_ms": "100",
            "frames_total": "10",
            "last_completed_frame_s": "0.1",
            "rss_mb": "100",
            "cpu_percent": "20",
            "system_cpu_percent": "30",
            "system_memory_percent": "40",
            "temperature_c": "50",
            "health_error": "",
        },
        {
            "elapsed_s": "10",
            "health_age_s": "0.5",
            "fps": "10",
            "latency_ms": "200",
            "frames_total": "100",
            "last_completed_frame_s": "0.3",
            "rss_mb": "110",
            "cpu_percent": "30",
            "system_cpu_percent": "40",
            "system_memory_percent": "45",
            "temperature_c": "55",
            "health_error": "",
        },
        {
            "elapsed_s": "20",
            "health_age_s": "2.0",
            "fps": "8",
            "latency_ms": "300",
            "frames_total": "180",
            "last_completed_frame_s": "1.5",
            "rss_mb": "125",
            "cpu_percent": "40",
            "system_cpu_percent": "50",
            "system_memory_percent": "50",
            "temperature_c": "60",
            "health_error": "",
        },
    ]

    summary = summarize_rows(rows)
    assert summary["samples"] == 3
    assert summary["duration_s"] == 20
    assert summary["latency_ms"]["p50"] == 200
    assert summary["latency_ms"]["p95"] == 290
    assert summary["fps"]["min"] == 8
    assert summary["fps"]["median"] == 10
    assert summary["memory"]["rss_growth_mb"] == 25
    assert summary["health"]["max_completed_frame_idle_s"] == 1.5
    assert summary["temperature_c"]["max"] == 60


def test_soak_summary_counts_health_parse_failures_without_crashing():
    rows = [
        {"elapsed_s": "0", "health_error": "missing"},
        {"elapsed_s": "5", "health_error": "invalid:JSONDecodeError"},
    ]
    summary = summarize_rows(rows)
    assert summary["samples"] == 2
    assert summary["health_error_samples"] == 2
    assert summary["latency_ms"]["p99"] is None
    assert summary["memory"]["rss_growth_mb"] is None


def test_soak_summary_rejects_empty_evidence():
    with pytest.raises(ValueError, match="no samples"):
        summarize_rows([])
