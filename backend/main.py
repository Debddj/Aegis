# ruff: noqa: E402
"""Aegis Backend — FastAPI application with middleware, logging, and SSE."""

from dotenv import load_dotenv

load_dotenv()  # Initialize environment variables before any other imports

import asyncio
import logging
import sys
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from backend.api import routes_agents, routes_incidents, routes_metrics
from backend.db.session import init_db

# ── Logging setup ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-24s | %(levelname)-5s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("aegis.backend")

# ── App ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Aegis API",
    description="Multi-agent ML operations system for incident detection, diagnosis, and remediation.",
    version="0.2.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ───────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.perf_counter()
    logger.info("[%s] %s %s", request_id, request.method, request.url.path)

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception("[%s] Unhandled error", request_id)
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    elapsed = (time.perf_counter() - start) * 1000
    logger.info("[%s] %s %s → %d (%.1fms)",
                request_id, request.method, request.url.path,
                response.status_code, elapsed)
    return response


# ── Global exception handler ────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {exc}"},
    )


# ── Routers ──────────────────────────────────────────────────────────────
app.include_router(routes_incidents.router, prefix="/incidents", tags=["Incidents"])
app.include_router(routes_agents.router, prefix="/agents", tags=["Agents"])
app.include_router(routes_metrics.router, prefix="/metrics", tags=["Metrics"])


# ── SSE endpoint for real-time agent traces ──────────────────────────────
# Simple in-memory event queue for demo purposes
_event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)


async def push_event(event_type: str, data: dict) -> None:
    """Push an event to the SSE stream (called by the pipeline)."""
    try:
        _event_queue.put_nowait({
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except asyncio.QueueFull:
        pass  # drop events if queue is full


@app.get("/events")
async def event_stream(request: Request):
    """Server-Sent Events endpoint for real-time agent activity."""
    async def generate():
        import json
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(_event_queue.get(), timeout=30.0)
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"]),
                }
            except asyncio.TimeoutError:
                # Send keepalive
                yield {"event": "keepalive", "data": "{}"}

    return EventSourceResponse(generate())


async def poll_telemetry_loop(SessionLocal):
    """Background loop polling simulator telemetry and running Sentry detection."""
    import os
    import uuid
    from datetime import datetime, timezone

    import httpx

    from agents.orchestrator import AegisPipeline
    from backend.db.models import ApprovalRequest, IncidentRecord

    SIMULATOR_URL = os.getenv("SIMULATOR_URL", "http://localhost:8100")
    pipeline = AegisPipeline()

    logger.info("Starting background telemetry polling loop targeting %s...", SIMULATOR_URL)

    while True:
        await asyncio.sleep(5.0)
        try:
            # 1. Fetch current metrics
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{SIMULATOR_URL}/metrics", timeout=5.0)
                if resp.status_code != 200:
                    continue
                metrics_text = resp.text

            # 2. Check for active/recent incidents in the database
            db = SessionLocal()
            try:
                unresolved = db.query(IncidentRecord).filter(IncidentRecord.status == "awaiting_approval").first()
                if unresolved:
                    # Skip running sentry to avoid incident spamming
                    continue

                recent = db.query(IncidentRecord).order_by(IncidentRecord.created_at.desc()).first()
                if recent and recent.created_at:
                    delta = (datetime.now(timezone.utc) - recent.created_at.replace(tzinfo=timezone.utc)).total_seconds()
                    if delta < 60.0:
                        continue
            except Exception as e:
                logger.error("DB check in telemetry loop failed: %s", e)
                continue
            finally:
                db.close()

            # 3. Sentry evaluates metrics
            logger.info("Background Telemetry Polling: Evaluating metrics with Sentry agent...")
            anomaly = await pipeline.run_sentry(metrics_text)

            # 4. Trigger pipeline if severity >= 0.70
            if anomaly.severity >= 0.70:
                logger.warning("Anomaly detected! Severity=%.2f. Triggering full Aegis pipeline...", anomaly.severity)
                incident = await pipeline.handle_anomaly(anomaly)

                # 5. Persist the incident record & approval request
                db = SessionLocal()
                try:
                    record = IncidentRecord(
                        id=incident.id,
                        status=incident.status,
                        anomaly_service=anomaly.service,
                        anomaly_metric=anomaly.metric,
                        anomaly_observed=anomaly.observed_value,
                        anomaly_baseline=anomaly.baseline_value,
                        anomaly_severity=anomaly.severity,
                        anomaly_detected_at=anomaly.detected_at,
                    )
                    if incident.diagnosis:
                        record.diagnosis_root_cause = incident.diagnosis.root_cause
                        record.diagnosis_confidence = incident.diagnosis.confidence
                        record.diagnosis_signals = incident.diagnosis.correlated_signals
                    if incident.action:
                        record.action_description = incident.action.description
                        record.action_command = incident.action.command
                        record.action_risk_tier = incident.action.risk_tier.value
                        record.action_reversible = incident.action.reversible
                        record.action_auto_executed = incident.action.auto_executed

                        if not incident.action.auto_executed:
                            approval = ApprovalRequest(
                                id=str(uuid.uuid4()),
                                incident_id=incident.id,
                                action_command=incident.action.command,
                                action_description=incident.action.description,
                                risk_tier=incident.action.risk_tier.value,
                            )
                            db.add(approval)

                    if incident.report:
                        record.report_markdown = incident.report

                    db.add(record)
                    db.commit()
                    logger.info("Persisted background incident: %s", incident.id[:8])
                except Exception as e:
                    logger.error("Failed to save background incident to DB: %s", e)
                    db.rollback()
                finally:
                    db.close()

        except httpx.HTTPError:
            pass
        except Exception as e:
            logger.exception("Error in background telemetry polling loop: %s", e)


# ── Startup/shutdown ─────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    init_db()
    from agents.orchestrator import register_event_callback
    register_event_callback(push_event)

    # Spawn the background metrics polling loop
    from backend.db.session import SessionLocal
    asyncio.create_task(poll_telemetry_loop(SessionLocal))

    logger.info("Aegis backend started")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}
