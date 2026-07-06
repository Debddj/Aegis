"""Sentry tools — fetch live metrics from the simulator and compute deviations."""

import httpx
import json
import logging

logger = logging.getLogger("aegis.sentry.tools")

# Configurable baselines for deviation calculation
BASELINES = {
    "latency_p95_ms": 45.0,
    "error_rate": 0.005,
    "gpu_memory_used_pct": 0.55,
    "data_drift_score": 0.05,
    "throughput_rps": 1200.0,
}

SIMULATOR_URL = "http://localhost:8100"


def fetch_recent_metrics(service_name: str) -> str:
    """Fetch recent latency, throughput, error rate, GPU, and drift metrics for a service.

    Connects to the simulator's /metrics endpoint and returns the current
    system health snapshot as a JSON string.
    """
    try:
        resp = httpx.get(f"{SIMULATOR_URL}/metrics", timeout=10.0)
        resp.raise_for_status()
        metrics = resp.json()
        logger.info("Fetched metrics for %s: latency=%.1fms, error_rate=%.4f",
                     service_name,
                     metrics.get("latency_p95_ms", 0),
                     metrics.get("error_rate", 0))
        return json.dumps(metrics, indent=2)
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch metrics from simulator: %s", exc)
        return json.dumps({
            "error": f"Could not reach simulator at {SIMULATOR_URL}: {exc}",
            "service": service_name,
        })


def compute_baseline_deviation(metric_name: str, current_value: float) -> str:
    """Compute the deviation of a metric from its historical baseline.

    Returns a structured analysis including the baseline value, absolute
    deviation, percentage change, and a severity classification.
    """
    baseline = BASELINES.get(metric_name)
    if baseline is None:
        return json.dumps({
            "metric": metric_name,
            "current_value": current_value,
            "error": f"No baseline found for metric '{metric_name}'",
        })

    if baseline == 0:
        pct_change = float("inf") if current_value != 0 else 0.0
    else:
        pct_change = ((current_value - baseline) / baseline) * 100

    abs_deviation = current_value - baseline

    # Determine severity based on direction of deviation.
    # Latency, errors, GPU usage, and drift are anomalous when they increase.
    # Throughput is anomalous when it decreases.
    is_anomaly = False
    if metric_name == "throughput_rps":
        if pct_change < 0:
            is_anomaly = True
    else:
        if pct_change > 0:
            is_anomaly = True

    if is_anomaly:
        abs_pct = abs(pct_change)
        if abs_pct > 200:
            severity = "critical"
        elif abs_pct > 100:
            severity = "high"
        elif abs_pct > 50:
            severity = "medium"
        else:
            severity = "low"
    else:
        severity = "low"

    result = {
        "metric": metric_name,
        "current_value": current_value,
        "baseline_value": baseline,
        "absolute_deviation": round(abs_deviation, 4),
        "percentage_change": round(pct_change, 2),
        "severity": severity,
    }
    logger.info("Deviation for %s: %.2f%% (%s)", metric_name, pct_change, severity)
    return json.dumps(result, indent=2)
