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


# ── Startup/shutdown ─────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    init_db()
    from agents.orchestrator import register_event_callback
    register_event_callback(push_event)
    logger.info("Aegis backend started")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}
