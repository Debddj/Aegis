"""Tests for the simulator — metrics generator and failure scenarios."""

import pytest
from simulator.metrics_generator import MetricsGenerator
from simulator.failure_scenarios import SCENARIOS, get_scenario, list_scenarios


class TestMetricsGenerator:
    def test_generates_valid_metrics(self):
        gen = MetricsGenerator()
        m = gen.generate()
        assert "latency_p95_ms" in m
        assert "error_rate" in m
        assert "gpu_memory_used_pct" in m
        assert "throughput_rps" in m
        assert "data_drift_score" in m
        assert m["tick"] == 1

    def test_tick_increments(self):
        gen = MetricsGenerator()
        gen.generate()
        m2 = gen.generate()
        assert m2["tick"] == 2

    def test_baseline_latency_range(self):
        gen = MetricsGenerator()
        # Generate many samples and check they're near the baseline
        latencies = [gen.generate()["latency_p95_ms"] for _ in range(100)]
        avg = sum(latencies) / len(latencies)
        assert 30 < avg < 60  # should be near 45ms

    def test_anomaly_injection_increases_latency(self):
        gen = MetricsGenerator()
        gen.inject_anomaly("latency", 15.0)
        m = gen.generate()
        assert m["latency_p95_ms"] > 200  # 45 * 15 = 675, minus noise

    def test_clear_anomalies_restores_baseline(self):
        gen = MetricsGenerator()
        gen.inject_anomaly("latency", 15.0)
        gen.generate()
        gen.clear_anomalies()
        # Generate several samples to confirm restoration
        latencies = [gen.generate()["latency_p95_ms"] for _ in range(50)]
        avg = sum(latencies) / len(latencies)
        assert avg < 100  # should be near 45ms again

    def test_metrics_values_are_bounded(self):
        gen = MetricsGenerator()
        for _ in range(100):
            m = gen.generate()
            assert m["latency_p95_ms"] >= 1.0
            assert 0.0 <= m["error_rate"] <= 1.0
            assert 0.0 <= m["gpu_memory_used_pct"] <= 1.0
            assert m["throughput_rps"] >= 0.0
            assert m["data_drift_score"] >= 0.0


class TestFailureScenarios:
    def test_all_scenarios_defined(self):
        expected = {"latency_spike", "error_spike", "gpu_oom", "data_drift", "cascading_failure"}
        assert set(SCENARIOS.keys()) == expected

    def test_get_scenario_returns_correct_type(self):
        s = get_scenario("latency_spike")
        assert s is not None
        assert s.name == "latency_spike"
        assert "latency_multiplier" in s.state_mutations

    def test_get_unknown_scenario_returns_none(self):
        assert get_scenario("nonexistent") is None

    def test_list_scenarios(self):
        names = list_scenarios()
        assert len(names) == 5
        assert "latency_spike" in names

    def test_cascading_failure_has_multiple_mutations(self):
        s = get_scenario("cascading_failure")
        assert len(s.state_mutations) >= 4
        assert s.duration_seconds > 300  # should be longer than default

    def test_all_scenarios_have_descriptions(self):
        for name, scenario in SCENARIOS.items():
            assert scenario.description, f"Scenario {name} missing description"
            assert len(scenario.description) > 20
