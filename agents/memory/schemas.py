from pydantic import BaseModel
from datetime import datetime
from enum import Enum

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
    diagnosis: Diagnosis | None = None
    action: RemediationAction | None = None
    report: str | None = None
    status: str = "open"
