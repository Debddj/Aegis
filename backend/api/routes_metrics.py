"""Metrics API routes — proxy to simulator and serve historical data."""

import logging
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.models import MetricSnapshot
from backend.db.session import get_db

logger = logging.getLogger("aegis.api.metrics")
router = APIRouter()

SIMULATOR_URL = "http://localhost:8100"


@router.get("/summary")
def get_metrics_summary():
    """Fetch current system metrics from the simulator."""
    try:
        resp = httpx.get(f"{SIMULATOR_URL}/metrics", timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch metrics from simulator: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach simulator at {SIMULATOR_URL}: {exc}",
        )


@router.get("/snapshot")
def take_snapshot(db: Session = Depends(get_db)):
    """Take a point-in-time metric snapshot and persist it to the DB."""
    try:
        resp = httpx.get(f"{SIMULATOR_URL}/metrics", timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Simulator unreachable: {exc}")

    snapshot = MetricSnapshot(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        service=data.get("service", "mock_inference"),
        latency_p95_ms=data.get("latency_p95_ms"),
        error_rate=data.get("error_rate"),
        gpu_memory_used_pct=data.get("gpu_memory_used_pct"),
        throughput_rps=data.get("throughput_rps"),
        data_drift_score=data.get("data_drift_score"),
        raw_data=data,
    )
    db.add(snapshot)
    db.commit()

    return {"id": snapshot.id, "timestamp": snapshot.timestamp.isoformat(), "data": data}


@router.get("/history")
def get_metric_history(
    limit: int = 100,
    service: str | None = None,
    db: Session = Depends(get_db),
):
    """Return historical metric snapshots with optional filtering."""
    query = db.query(MetricSnapshot).order_by(MetricSnapshot.timestamp.desc())
    if service:
        query = query.filter(MetricSnapshot.service == service)
    snapshots = query.limit(limit).all()

    return [
        {
            "id": s.id,
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            "service": s.service,
            "latency_p95_ms": s.latency_p95_ms,
            "error_rate": s.error_rate,
            "gpu_memory_used_pct": s.gpu_memory_used_pct,
            "throughput_rps": s.throughput_rps,
            "data_drift_score": s.data_drift_score,
        }
        for s in snapshots
    ]


@router.get("/state")
def get_simulator_state():
    """Proxy the simulator's internal state for debugging."""
    try:
        resp = httpx.get(f"{SIMULATOR_URL}/state", timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Simulator unreachable: {exc}")
