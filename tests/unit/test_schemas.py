"""Tests for Pydantic schema models."""

import pytest
from datetime import datetime, timezone
from agents.memory.schemas import Anomaly, Diagnosis, RemediationAction, Incident, RiskTier


class TestAnomaly:
    def test_valid_anomaly(self):
        a = Anomaly(
            service="inference-svc",
            metric="latency_p95",
            observed_value=350.0,
            baseline_value=45.0,
            severity=0.85,
            detected_at=datetime.now(timezone.utc),
        )
        assert a.service == "inference-svc"
        assert a.severity == 0.85

    def test_anomaly_serialization_roundtrip(self):
        a = Anomaly(
            service="test",
            metric="error_rate",
            observed_value=0.5,
            baseline_value=0.01,
            severity=0.9,
            detected_at=datetime(2026, 7, 6, 14, 0, 0, tzinfo=timezone.utc),
        )
        data = a.model_dump_json()
        a2 = Anomaly.model_validate_json(data)
        assert a2.service == a.service
        assert a2.observed_value == a.observed_value


class TestRiskTier:
    def test_enum_values(self):
        assert RiskTier.LOW == "low"
        assert RiskTier.MEDIUM == "medium"
        assert RiskTier.HIGH == "high"

    def test_enum_from_string(self):
        assert RiskTier("low") == RiskTier.LOW


class TestRemediationAction:
    def test_valid_action(self):
        action = RemediationAction(
            description="Restart pod",
            command="restart_pod(inference-svc-3)",
            risk_tier=RiskTier.LOW,
            reversible=True,
        )
        assert action.auto_executed is False

    def test_action_with_string_risk_tier(self):
        action = RemediationAction(
            description="Rollback",
            command="rollback_model(v1)",
            risk_tier="high",
            reversible=True,
        )
        assert action.risk_tier == RiskTier.HIGH


class TestIncident:
    def test_minimal_incident(self):
        anomaly = Anomaly(
            service="test",
            metric="latency",
            observed_value=100.0,
            baseline_value=10.0,
            severity=0.8,
            detected_at=datetime.now(timezone.utc),
        )
        incident = Incident(id="test-123", anomaly=anomaly)
        assert incident.status == "open"
        assert incident.diagnosis is None
        assert incident.action is None
        assert incident.report is None

    def test_full_incident(self):
        anomaly = Anomaly(
            service="svc", metric="m", observed_value=1.0,
            baseline_value=0.1, severity=0.9,
            detected_at=datetime.now(timezone.utc),
        )
        diagnosis = Diagnosis(
            root_cause="test cause",
            confidence=0.95,
            correlated_signals=["signal1"],
        )
        action = RemediationAction(
            description="Fix it",
            command="restart_pod(x)",
            risk_tier=RiskTier.LOW,
            reversible=True,
            auto_executed=True,
        )
        incident = Incident(
            id="full-test",
            anomaly=anomaly,
            diagnosis=diagnosis,
            action=action,
            report="# Report",
            status="resolved",
        )
        assert incident.status == "resolved"
        assert incident.action.auto_executed is True
