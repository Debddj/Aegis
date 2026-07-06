"""Mock ML inference service with failure injection for Aegis demos."""

import asyncio
import random
import time
import logging
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("aegis.simulator")

app = FastAPI(title="Aegis Mock Inference Service", version="0.2.0")

# ---------------------------------------------------------------------------
# Mutable global state — each scenario mutates these knobs
# ---------------------------------------------------------------------------
STATE: dict = {
    "latency_multiplier": 1.0,
    "error_rate": 0.0,
    "gpu_memory_used_pct": 0.55,
    "gpu_memory_fragmented": False,
    "data_drift_score": 0.05,        # PSI — normal < 0.1
    "active_scenario": None,
    "scenario_injected_at": None,
    "request_count": 0,
    "error_count": 0,
}

BASELINE = {
    "latency_ms": 45.0,
    "error_rate": 0.005,
    "gpu_memory_used_pct": 0.55,
    "data_drift_score": 0.05,
    "throughput_rps": 1200.0,
}

# Track recent deploys for Sleuth to query
DEPLOY_HISTORY: list[dict] = []

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/predict")
async def predict(payload: dict):
    """Simulate an ML inference call with configurable latency and errors."""
    STATE["request_count"] += 1

    # Non-blocking sleep to simulate latency
    latency_s = 0.05 * STATE["latency_multiplier"]
    await asyncio.sleep(latency_s)

    if random.random() < STATE["error_rate"]:
        STATE["error_count"] += 1
        return JSONResponse(status_code=500, content={"error": "internal_error"})

    return {
        "prediction": round(random.random(), 4),
        "latency_ms": round(latency_s * 1000, 1),
    }


@app.get("/metrics")
async def get_metrics():
    """Return current system metrics — polled by Sentry tools."""
    latency = BASELINE["latency_ms"] * STATE["latency_multiplier"]
    # Add small Gaussian noise to make metrics look realistic
    latency += random.gauss(0, 2)

    error_rate = STATE["error_rate"] + random.gauss(0, 0.001)
    error_rate = max(0.0, min(1.0, error_rate))

    gpu_mem = STATE["gpu_memory_used_pct"] + random.gauss(0, 0.02)
    gpu_mem = max(0.0, min(1.0, gpu_mem))

    throughput = BASELINE["throughput_rps"]
    if STATE["latency_multiplier"] > 5:
        throughput = throughput / STATE["latency_multiplier"]

    return {
        "service": "mock_inference",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latency_p95_ms": round(max(0, latency), 2),
        "error_rate": round(error_rate, 4),
        "gpu_memory_used_pct": round(gpu_mem, 3),
        "gpu_memory_fragmented": STATE["gpu_memory_fragmented"],
        "data_drift_score": round(STATE["data_drift_score"] + random.gauss(0, 0.005), 4),
        "throughput_rps": round(max(0, throughput), 1),
        "request_count": STATE["request_count"],
        "error_count": STATE["error_count"],
        "baseline": BASELINE,
    }


@app.get("/state")
async def get_state():
    """Return raw internal state — used by Sleuth for correlation."""
    return {
        **STATE,
        "deploy_history": DEPLOY_HISTORY[-10:],  # last 10 deploys
    }


@app.get("/deploys")
async def get_deploys():
    """Return deployment history."""
    return {"deploys": DEPLOY_HISTORY}


@app.post("/_inject/{scenario}")
async def inject(scenario: str):
    """Inject a failure scenario into the mock service."""
    now = datetime.now(timezone.utc).isoformat()
    STATE["scenario_injected_at"] = now
    STATE["active_scenario"] = scenario

    if scenario == "latency_spike":
        STATE["latency_multiplier"] = 15.0
        DEPLOY_HISTORY.append({
            "id": "model-rollout-v2",
            "service": "mock_inference",
            "timestamp": now,
            "type": "model_update",
        })
        logger.warning("INJECTED: latency_spike — latency_multiplier=15.0")

    elif scenario == "error_spike":
        STATE["error_rate"] = 0.45
        logger.warning("INJECTED: error_spike — error_rate=0.45")

    elif scenario == "gpu_oom":
        STATE["gpu_memory_used_pct"] = 0.97
        STATE["gpu_memory_fragmented"] = True
        STATE["latency_multiplier"] = 8.0
        DEPLOY_HISTORY.append({
            "id": "model-rollout-v2-large",
            "service": "mock_inference",
            "timestamp": now,
            "type": "model_update",
        })
        logger.warning("INJECTED: gpu_oom — GPU memory at 97%%, fragmented")

    elif scenario == "data_drift":
        STATE["data_drift_score"] = 0.35
        logger.warning("INJECTED: data_drift — PSI=0.35")

    elif scenario == "cascading_failure":
        STATE["latency_multiplier"] = 12.0
        STATE["error_rate"] = 0.30
        STATE["gpu_memory_used_pct"] = 0.92
        STATE["gpu_memory_fragmented"] = True
        STATE["data_drift_score"] = 0.22
        logger.warning("INJECTED: cascading_failure — all metrics degraded")

    elif scenario == "reset":
        STATE["latency_multiplier"] = 1.0
        STATE["error_rate"] = 0.0
        STATE["gpu_memory_used_pct"] = 0.55
        STATE["gpu_memory_fragmented"] = False
        STATE["data_drift_score"] = 0.05
        STATE["active_scenario"] = None
        STATE["scenario_injected_at"] = None
        STATE["request_count"] = 0
        STATE["error_count"] = 0
        logger.info("RESET: all metrics restored to baseline")

    else:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown scenario: {scenario}"},
        )

    return {"status": "injected", "scenario": scenario, "timestamp": now}


@app.get("/health")
async def health():
    return {"status": "ok", "active_scenario": STATE.get("active_scenario")}
