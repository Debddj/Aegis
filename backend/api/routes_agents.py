"""Agent management and approval API routes."""

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.db.session import get_db
from backend.db.models import IncidentRecord, ApprovalRequest
from agents.memory.schemas import Anomaly
from agents.orchestrator import AegisPipeline

logger = logging.getLogger("aegis.api.agents")
router = APIRouter()

_pipeline = AegisPipeline()

AVAILABLE_SCENARIOS = ["latency_spike", "error_spike", "gpu_oom", "data_drift", "cascading_failure"]

# Default anomaly parameters per scenario
SCENARIO_DEFAULTS = {
    "latency_spike": {"metric": "latency_p95", "observed_value": 675.0, "baseline_value": 45.0, "severity": 0.85},
    "error_spike": {"metric": "error_rate", "observed_value": 0.45, "baseline_value": 0.005, "severity": 0.90},
    "gpu_oom": {"metric": "gpu_memory_used_pct", "observed_value": 0.97, "baseline_value": 0.55, "severity": 0.92},
    "data_drift": {"metric": "data_drift_score", "observed_value": 0.35, "baseline_value": 0.05, "severity": 0.70},
    "cascading_failure": {"metric": "latency_p95", "observed_value": 540.0, "baseline_value": 45.0, "severity": 0.95},
}


class ScenarioRequest(BaseModel):
    scenario: str = "latency_spike"


class ApprovalDecision(BaseModel):
    approved: bool
    resolved_by: str = "operator"


@router.get("/status")
def agent_status():
    """Return current agent readiness and configuration."""
    return {
        "agents": {
            "sentry": {"status": "ready", "model": "gemini-2.5-flash"},
            "sleuth": {"status": "ready", "model": "gemini-2.5-flash"},
            "medic": {"status": "ready", "model": "gemini-2.5-flash"},
            "scribe": {"status": "ready", "model": "gemini-2.5-flash"},
        },
        "available_scenarios": AVAILABLE_SCENARIOS,
        "pipeline": "operational",
    }


@router.post("/trigger")
async def trigger_scenario(request: ScenarioRequest, db: Session = Depends(get_db)):
    """Trigger the full Aegis pipeline with a named failure scenario."""
    if request.scenario not in SCENARIO_DEFAULTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{request.scenario}'. Available: {AVAILABLE_SCENARIOS}",
        )

    defaults = SCENARIO_DEFAULTS[request.scenario]
    anomaly = Anomaly(
        service="mock_inference",
        metric=defaults["metric"],
        observed_value=defaults["observed_value"],
        baseline_value=defaults["baseline_value"],
        severity=defaults["severity"],
        detected_at=datetime.now(timezone.utc),
    )

    try:
        incident = await _pipeline.handle_anomaly(anomaly)
    except Exception as exc:
        logger.exception("Pipeline failed for scenario %s", request.scenario)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}")

    # Persist incident
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

        # Create approval request if not auto-executed
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
    logger.info("Scenario '%s' → Incident %s (%s)",
                request.scenario, incident.id[:8], incident.status)

    return {
        "id": incident.id,
        "scenario": request.scenario,
        "status": incident.status,
        "diagnosis": incident.diagnosis.root_cause if incident.diagnosis else None,
        "action": incident.action.description if incident.action else None,
        "risk_tier": incident.action.risk_tier.value if incident.action else None,
        "auto_executed": incident.action.auto_executed if incident.action else None,
        "needs_approval": not incident.action.auto_executed if incident.action else False,
    }


@router.get("/approvals")
def list_pending_approvals(db: Session = Depends(get_db)):
    """List all pending approval requests."""
    approvals = db.query(ApprovalRequest).filter(
        ApprovalRequest.status == "pending"
    ).order_by(ApprovalRequest.created_at.desc()).all()

    return [
        {
            "id": a.id,
            "incident_id": a.incident_id,
            "action": a.action_description,
            "command": a.action_command,
            "risk_tier": a.risk_tier,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in approvals
    ]


@router.post("/approve/{incident_id}")
def approve_action(incident_id: str, decision: ApprovalDecision, db: Session = Depends(get_db)):
    """Approve or reject a pending remediation action."""
    approval = db.query(ApprovalRequest).filter(
        ApprovalRequest.incident_id == incident_id,
        ApprovalRequest.status == "pending",
    ).first()
    if not approval:
        raise HTTPException(status_code=404, detail="No pending approval for this incident")

    now = datetime.now(timezone.utc)
    approval.status = "approved" if decision.approved else "rejected"
    approval.resolved_at = now
    approval.resolved_by = decision.resolved_by

    # Update the incident status
    incident = db.query(IncidentRecord).filter(IncidentRecord.id == incident_id).first()
    if incident:
        if decision.approved:
            incident.status = "resolved"
            incident.action_auto_executed = True  # mark as executed after approval
            from agents.medic.tools import execute_remediation
            execute_remediation(incident.action_command)
        else:
            incident.status = "rejected"

    db.commit()
    logger.info("Incident %s %s by %s",
                incident_id[:8], approval.status, decision.resolved_by)

    return {
        "incident_id": incident_id,
        "decision": approval.status,
        "resolved_by": decision.resolved_by,
    }
