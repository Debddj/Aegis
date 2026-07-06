"""Sleuth tools — correlate logs, query deploys, and search incident memory."""

import json
import logging

import httpx

from backend.config import settings

logger = logging.getLogger("aegis.sleuth.tools")

SIMULATOR_URL = settings.simulator_url


def correlate_logs(service_name: str) -> str:
    """Correlate log signals across services during the incident window.

    Queries the simulator's /state and /metrics endpoints to build a
    cross-service correlation report showing which metrics are anomalous
    and what state changes may have caused them.
    """
    try:
        state_resp = httpx.get(f"{SIMULATOR_URL}/state", timeout=10.0)
        state_resp.raise_for_status()
        state = state_resp.json()

        metrics_resp = httpx.get(f"{SIMULATOR_URL}/metrics", timeout=10.0)
        metrics_resp.raise_for_status()
        metrics = metrics_resp.json()

        # Build correlation report
        signals = []

        latency = metrics.get("latency_p95_ms", 0)
        baseline_latency = metrics.get("baseline", {}).get("latency_ms", 45)
        if latency > baseline_latency * 2:
            signals.append(f"ANOMALY: latency_p95={latency:.1f}ms (baseline {baseline_latency}ms)")

        if metrics.get("error_rate", 0) > 0.05:
            signals.append(f"ANOMALY: error_rate={metrics['error_rate']:.4f} (threshold 0.05)")

        if state.get("gpu_memory_fragmented"):
            signals.append(f"ANOMALY: GPU memory fragmented, usage={state.get('gpu_memory_used_pct', 0):.0%}")

        drift = metrics.get("data_drift_score", 0)
        if drift > 0.1:
            signals.append(f"ANOMALY: data_drift_score={drift:.4f} (threshold 0.10)")

        if state.get("active_scenario"):
            signals.append(f"CONTEXT: active_scenario={state['active_scenario']}")

        if state.get("scenario_injected_at"):
            signals.append(f"CONTEXT: scenario_injected_at={state['scenario_injected_at']}")

        throughput = metrics.get("throughput_rps", 1200)
        signals.append(f"INFO: throughput={throughput:.0f} rps")
        signals.append(f"INFO: total_requests={state.get('request_count', 0)}, errors={state.get('error_count', 0)}")

        report = {
            "service": service_name,
            "correlated_signals": signals,
            "signal_count": len(signals),
            "timestamp": metrics.get("timestamp"),
        }
        logger.info("Log correlation for %s found %d signals", service_name, len(signals))
        return json.dumps(report, indent=2)

    except httpx.HTTPError as exc:
        logger.error("Failed to correlate logs: %s", exc)
        return json.dumps({
            "service": service_name,
            "error": f"Could not reach simulator: {exc}",
            "correlated_signals": [],
        })


def get_recent_deploys(service_name: str) -> str:
    """Get the recent deployments for a service from the simulator's deploy history.

    Returns a list of recent deployments including IDs, timestamps, and types.
    """
    try:
        resp = httpx.get(f"{SIMULATOR_URL}/deploys", timeout=10.0)
        resp.raise_for_status()
        deploys = resp.json().get("deploys", [])

        # Filter by service if specified
        relevant = [d for d in deploys if d.get("service", "") == service_name or service_name == "all"]
        if not relevant:
            relevant = deploys  # fall back to all deploys if no match

        result = {
            "service": service_name,
            "recent_deploys": relevant[-5:],  # last 5
            "total_deploys": len(relevant),
        }
        logger.info("Found %d deploys for %s", len(relevant), service_name)
        return json.dumps(result, indent=2)

    except httpx.HTTPError as exc:
        logger.error("Failed to fetch deploys: %s", exc)
        return json.dumps({
            "service": service_name,
            "error": f"Could not reach simulator: {exc}",
            "recent_deploys": [],
        })


def query_incident_memory(query: str) -> str:
    """Query ChromaDB incident memory for historical similar incidents.

    Searches the vector store for past incidents that match the query string
    and returns the most similar results with their metadata.
    """
    try:
        from agents.memory.vector_store import incident_store
        results = incident_store.search_similar(query, k=3)
        logger.info("Memory search returned %d results for: %s", len(results), query[:80])
        return json.dumps({
            "query": query,
            "results": results,
            "result_count": len(results),
        }, indent=2)
    except Exception as exc:
        logger.warning("Incident memory query failed: %s", exc)
        return json.dumps({
            "query": query,
            "results": [],
            "result_count": 0,
            "note": "No historical incident memory available yet.",
        })
