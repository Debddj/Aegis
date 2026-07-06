from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class RiskTier(str, Enum):
    LOW = "low"          # auto-executable, reversible
    MEDIUM = "medium"    # needs approval, reversible
    HIGH = "high"        # needs approval, potentially destructive


class Anomaly(BaseModel):
    service: str
    metric: str
    observed_value: float
    baseline_value: float
    severity: float
    detected_at: datetime


class Diagnosis(BaseModel):
    root_cause: str
    confidence: float
    correlated_signals: list[str]
    related_incidents: list[str] = []


class RemediationAction(BaseModel):
    description: str
    command: str
    risk_tier: RiskTier
    reversible: bool
    auto_executed: bool = False


class Incident(BaseModel):
    id: str
    anomaly: Anomaly
    diagnosis: Optional[Diagnosis] = None
    action: Optional[RemediationAction] = None
    report: Optional[str] = None
    status: str = "open"
    created_at: datetime = datetime.now(timezone.utc)
