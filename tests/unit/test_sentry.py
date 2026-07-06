"""Tests for Sentry tools — metric fetching and baseline deviation."""

import json

import pytest

from agents.sentry.tools import BASELINES, compute_baseline_deviation


class TestComputeBaselineDeviation:
    """Test the deviation calculation logic (no network calls)."""

    def test_normal_latency_is_low_severity(self):
        result = json.loads(compute_baseline_deviation("latency_p95_ms", 50.0))
        assert result["severity"] == "low"
        assert result["baseline_value"] == 45.0

    def test_2x_latency_is_medium_severity(self):
        result = json.loads(compute_baseline_deviation("latency_p95_ms", 90.0))
        assert result["severity"] == "medium"
        assert result["percentage_change"] == pytest.approx(100.0, abs=1)

    def test_3x_latency_is_high_severity(self):
        result = json.loads(compute_baseline_deviation("latency_p95_ms", 135.0))
        assert result["severity"] == "high"
        assert result["percentage_change"] == pytest.approx(200.0, abs=1)

    def test_15x_latency_is_critical_severity(self):
        result = json.loads(compute_baseline_deviation("latency_p95_ms", 675.0))
        assert result["severity"] == "critical"
        assert result["percentage_change"] > 200

    def test_error_rate_spike(self):
        result = json.loads(compute_baseline_deviation("error_rate", 0.45))
        assert result["severity"] == "critical"
        assert result["baseline_value"] == 0.005

    def test_gpu_memory_spike(self):
        result = json.loads(compute_baseline_deviation("gpu_memory_used_pct", 0.97))
        assert result["severity"] == "medium"  # ~76% increase from 0.55

    def test_unknown_metric_returns_error(self):
        result = json.loads(compute_baseline_deviation("nonexistent_metric", 42.0))
        assert "error" in result

    def test_negative_deviation(self):
        """A metric below baseline should show negative percentage."""
        result = json.loads(compute_baseline_deviation("latency_p95_ms", 20.0))
        assert result["percentage_change"] < 0
        assert result["severity"] == "low"

    def test_zero_current_value(self):
        result = json.loads(compute_baseline_deviation("error_rate", 0.0))
        assert result["percentage_change"] == pytest.approx(-100.0, abs=1)

    def test_all_baselines_have_entries(self):
        """Verify that BASELINES dict is populated."""
        assert len(BASELINES) >= 4
        assert "latency_p95_ms" in BASELINES
        assert "error_rate" in BASELINES
