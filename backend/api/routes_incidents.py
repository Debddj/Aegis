"""Incident management API routes."""

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.db.session import get_db
from backend.db.models import IncidentRecord
from agents.memory.schemas import Anomaly
from agents.orchestrator import AegisPipeline

logger = logging.getLogger("aegis.api.incidents")
router = APIRouter()

# Shared pipeline instance
_pipeline = AegisPipeline()


class TriggerRequest(BaseModel):
    """Request body for triggering the pipeline with a raw anomaly."""
    service: str = "mock_inference"
    metric: str = "latency_p95"
    observed_value: float = 350.0
    baseline_value: float = 45.0
    severity: float = 0.85


@router.get("/")
def list_incidents(
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """List all incidents with optional status filter and pagination."""
    query = db.query(IncidentRecord).order_by(IncidentRecord.created_at.desc())
    if status:
        query = query.filter(IncidentRecord.status == status)
    incidents = query.offset(skip).limit(limit).all()

    return [
        {
            "id": inc.id,
            "status": inc.status,
            "service": inc.anomaly_service,
            "metric": inc.anomaly_metric,
            "severity": inc.anomaly_severity,
            "risk_tier": inc.action_risk_tier,
            "auto_executed": inc.action_auto_executed,
            "created_at": inc.created_at.isoformat() if inc.created_at else None,
        }
        for inc in incidents
    ]


@router.get("/{incident_id}")
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    """Get full incident detail including diagnosis, action, and report."""
    inc = db.query(IncidentRecord).filter(IncidentRecord.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    return {
        "id": inc.id,
        "status": inc.status,
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
        "anomaly": {
            "service": inc.anomaly_service,
            "metric": inc.anomaly_metric,
            "observed_value": inc.anomaly_observed,
            "baseline_value": inc.anomaly_baseline,
            "severity": inc.anomaly_severity,
            "detected_at": inc.anomaly_detected_at.isoformat() if inc.anomaly_detected_at else None,
        },
        "diagnosis": {
            "root_cause": inc.diagnosis_root_cause,
            "confidence": inc.diagnosis_confidence,
            "correlated_signals": inc.diagnosis_signals or [],
        } if inc.diagnosis_root_cause else None,
        "action": {
            "description": inc.action_description,
            "command": inc.action_command,
            "risk_tier": inc.action_risk_tier,
            "reversible": inc.action_reversible,
            "auto_executed": inc.action_auto_executed,
        } if inc.action_command else None,
        "report": inc.report_markdown,
    }


@router.post("/trigger")
async def trigger_incident(request: TriggerRequest, db: Session = Depends(get_db)):
    """Trigger the full Aegis pipeline with a manual anomaly."""
    anomaly = Anomaly(
        service=request.service,
        metric=request.metric,
        observed_value=request.observed_value,
        baseline_value=request.baseline_value,
        severity=request.severity,
        detected_at=datetime.now(timezone.utc),
    )

    try:
        incident = await _pipeline.handle_anomaly(anomaly)
    except Exception as exc:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}")

    # Persist to DB
    record = IncidentRecord(
        id=incident.id,
        status=incident.status,
        created_at=incident.created_at,
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
    if incident.report:
        record.report_markdown = incident.report

    db.add(record)
    db.commit()
    logger.info("Incident %s persisted to DB", incident.id[:8])

    return {
        "id": incident.id,
        "status": incident.status,
        "diagnosis": incident.diagnosis.root_cause if incident.diagnosis else None,
        "action": incident.action.description if incident.action else None,
        "risk_tier": incident.action.risk_tier.value if incident.action else None,
        "auto_executed": incident.action.auto_executed if incident.action else None,
    }
