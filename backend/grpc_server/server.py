"""gRPC server implementation for Aegis.

Provides streaming endpoints for real-time pipeline events and metrics.
Run alongside the FastAPI server on a separate port (default: 50051).
"""

import asyncio
import json
import logging
import os
from concurrent import futures
from datetime import datetime, timezone

import httpx
from grpc import aio as grpc_aio

logger = logging.getLogger("aegis.grpc")

# Port for the gRPC server
GRPC_PORT = 50051

SIMULATOR_URL = os.getenv("SIMULATOR_URL", "http://localhost:8100")


class AegisServicer:
    """Implements the AegisService gRPC interface.

    Note: This server uses the raw gRPC API rather than generated stubs
    to avoid requiring a protoc build step for the demo. In production,
    you would run `grpc_tools.protoc` to generate the typed stubs.
    """

    async def TriggerPipeline(self, request, context):
        """Trigger the Aegis pipeline and stream events back to the client."""
        from agents.memory.schemas import Anomaly
        from agents.orchestrator import AegisPipeline

        scenario = request.scenario if hasattr(request, 'scenario') else "latency_spike"
        logger.info("gRPC TriggerPipeline: scenario=%s", scenario)

        # Build anomaly from scenario dynamically using simulator + Sentry
        metrics_context = ""
        try:
            await httpx.post(f"{SIMULATOR_URL}/_inject/{scenario}", timeout=10.0)
            metrics_resp = await httpx.get(f"{SIMULATOR_URL}/metrics", timeout=10.0)
            metrics_resp.raise_for_status()
            metrics_context = metrics_resp.text
        except Exception as exc:
            logger.warning("gRPC: Could not reach simulator to inject/fetch live metrics: %s", exc)

        pipeline = AegisPipeline()

        anomaly = None
        if metrics_context:
            try:
                anomaly = await pipeline.run_sentry(metrics_context)
            except Exception as exc:
                logger.warning("gRPC: Sentry failed to analyze metrics: %s", exc)

        if not anomaly:
            # Fallback to static defaults if simulator or Sentry fails
            scenario_defaults = {
                "latency_spike": ("latency_p95", 675.0, 45.0, 0.85),
                "error_spike": ("error_rate", 0.45, 0.005, 0.90),
                "gpu_oom": ("gpu_memory_used_pct", 0.97, 0.55, 0.92),
                "data_drift": ("data_drift_score", 0.35, 0.05, 0.70),
                "cascading_failure": ("latency_p95", 540.0, 45.0, 0.95),
            }
            defaults = scenario_defaults.get(scenario, scenario_defaults["latency_spike"])
            anomaly = Anomaly(
                service="mock_inference",
                metric=defaults[0],
                observed_value=defaults[1],
                baseline_value=defaults[2],
                severity=defaults[3],
                detected_at=datetime.now(timezone.utc),
            )

        # Stream pipeline events
        yield _make_event("sentry", "sentry", json.dumps(anomaly.model_dump(), default=str))

        incident = await pipeline.handle_anomaly(anomaly)

        if incident.diagnosis:
            yield _make_event(
                "sleuth", "sleuth",
                json.dumps(incident.diagnosis.model_dump(), default=str),
                incident.id,
            )
        if incident.action:
            yield _make_event(
                "medic", "medic",
                json.dumps(incident.action.model_dump(), default=str),
                incident.id,
            )
        if incident.report:
            yield _make_event("scribe", "scribe", incident.report[:2000], incident.id)

        yield _make_event("complete", "orchestrator",
                          json.dumps({"status": incident.status}), incident.id)

    async def StreamMetrics(self, request, context):
        """Stream real-time metrics from the simulator."""
        interval_s = max(1.0, (request.interval_ms if hasattr(request, 'interval_ms') else 2000) / 1000.0)
        logger.info("gRPC StreamMetrics: interval=%.1fs", interval_s)

        while not context.cancelled():
            try:
                resp = httpx.get(f"{SIMULATOR_URL}/metrics", timeout=5.0)
                resp.raise_for_status()
                data = resp.json()

                yield _make_metric_snapshot(data)
            except Exception as exc:
                logger.warning("Metrics fetch failed: %s", exc)

            await asyncio.sleep(interval_s)


def _make_event(event_type: str, agent: str, payload: str, incident_id: str = "") -> dict:
    """Create a PipelineEvent-like dict for streaming."""
    return {
        "event_type": event_type,
        "agent_name": agent,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "incident_id": incident_id,
    }


def _make_metric_snapshot(data: dict) -> dict:
    """Create a MetricSnapshot-like dict from simulator response."""
    return {
        "service": data.get("service", "mock_inference"),
        "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "latency_p95_ms": data.get("latency_p95_ms", 0),
        "error_rate": data.get("error_rate", 0),
        "gpu_memory_used_pct": data.get("gpu_memory_used_pct", 0),
        "throughput_rps": data.get("throughput_rps", 0),
        "data_drift_score": data.get("data_drift_score", 0),
    }


async def serve(port: int = GRPC_PORT):
    """Start the gRPC server."""
    server = grpc_aio.server(futures.ThreadPoolExecutor(max_workers=10))
    # In production, register generated servicer here:
    # streaming_pb2_grpc.add_AegisServiceServicer_to_server(AegisServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    logger.info("gRPC server starting on port %d", port)
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
