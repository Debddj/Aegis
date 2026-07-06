"""SQLAlchemy ORM models for Aegis — backed by SQLite."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IncidentRecord(Base):
    """Persisted incident with full lifecycle data."""
    __tablename__ = "incidents"

    id = Column(String, primary_key=True)
    status = Column(String, default="open", nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Anomaly data
    anomaly_service = Column(String, nullable=False, index=True)
    anomaly_metric = Column(String, nullable=False)
    anomaly_observed = Column(Float, nullable=False)
    anomaly_baseline = Column(Float, nullable=False)
    anomaly_severity = Column(Float, nullable=False)
    anomaly_detected_at = Column(DateTime, nullable=False)

    # Diagnosis
    diagnosis_root_cause = Column(Text)
    diagnosis_confidence = Column(Float)
    diagnosis_signals = Column(JSON)  # list[str] stored as JSON

    # Remediation
    action_description = Column(Text)
    action_command = Column(String)
    action_risk_tier = Column(String)
    action_reversible = Column(Boolean)
    action_auto_executed = Column(Boolean, default=False)

    # Report
    report_markdown = Column(Text)

    def __repr__(self):
        return f"<Incident {self.id[:8]}… status={self.status} service={self.anomaly_service}>"


class MetricSnapshot(Base):
    """Point-in-time metric reading from the simulator."""
    __tablename__ = "metric_snapshots"

    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    service = Column(String, nullable=False, index=True)
    latency_p95_ms = Column(Float)
    error_rate = Column(Float)
    gpu_memory_used_pct = Column(Float)
    throughput_rps = Column(Float)
    data_drift_score = Column(Float)
    raw_data = Column(JSON)  # full metrics payload


class ApprovalRequest(Base):
    """Tracks human approval requests for medium/high risk actions."""
    __tablename__ = "approval_requests"

    id = Column(String, primary_key=True)
    incident_id = Column(String, nullable=False, index=True)
    action_command = Column(String, nullable=False)
    action_description = Column(Text)
    risk_tier = Column(String, nullable=False)
    status = Column(String, default="pending", index=True)  # pending, approved, rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
