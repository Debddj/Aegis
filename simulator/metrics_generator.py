"""Synthetic metrics generator for realistic time-series simulation."""

import random
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class MetricsGenerator:
    """Generates realistic time-series metrics with configurable anomaly injection.

    Produces baseline metrics with Gaussian noise, seasonal patterns, and
    responds to injected scenarios by shifting distributions.
    """

    # Baseline values
    base_latency_ms: float = 45.0
    base_error_rate: float = 0.005
    base_gpu_util: float = 0.55
    base_throughput_rps: float = 1200.0
    base_drift_score: float = 0.05

    # Noise parameters
    latency_noise_std: float = 3.0
    error_noise_std: float = 0.002
    gpu_noise_std: float = 0.03
    throughput_noise_std: float = 50.0

    # State
    tick: int = 0
    _anomaly_multipliers: dict = field(default_factory=dict)

    def inject_anomaly(self, metric: str, multiplier: float) -> None:
        """Apply a multiplier to a specific metric to simulate an anomaly."""
        self._anomaly_multipliers[metric] = multiplier

    def clear_anomalies(self) -> None:
        """Reset all anomaly multipliers."""
        self._anomaly_multipliers.clear()

    def generate(self) -> dict:
        """Generate one snapshot of system metrics.

        Returns a dict suitable for feeding to Sentry.
        """
        self.tick += 1
        t = self.tick

        # Add a subtle diurnal pattern (sinusoidal over 288 ticks ≈ 24h at 5min intervals)
        seasonal = 1.0 + 0.1 * math.sin(2 * math.pi * t / 288)

        latency = self.base_latency_ms * seasonal + random.gauss(0, self.latency_noise_std)
        latency *= self._anomaly_multipliers.get("latency", 1.0)
        latency = max(1.0, latency)

        error_rate = self.base_error_rate + random.gauss(0, self.error_noise_std)
        error_rate *= self._anomaly_multipliers.get("error_rate", 1.0)
        error_rate = max(0.0, min(1.0, error_rate))

        gpu_util = self.base_gpu_util + random.gauss(0, self.gpu_noise_std)
        gpu_util *= self._anomaly_multipliers.get("gpu_util", 1.0)
        gpu_util = max(0.0, min(1.0, gpu_util))

        throughput = self.base_throughput_rps * seasonal + random.gauss(0, self.throughput_noise_std)
        # High latency reduces effective throughput
        if latency > self.base_latency_ms * 3:
            throughput *= self.base_latency_ms / latency
        throughput = max(0.0, throughput)

        drift_score = self.base_drift_score + random.gauss(0, 0.005)
        drift_score *= self._anomaly_multipliers.get("drift", 1.0)
        drift_score = max(0.0, drift_score)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tick": t,
            "latency_p95_ms": round(latency, 2),
            "error_rate": round(error_rate, 5),
            "gpu_memory_used_pct": round(gpu_util, 4),
            "throughput_rps": round(throughput, 1),
            "data_drift_score": round(drift_score, 4),
        }
