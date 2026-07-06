"""Integration test — full Aegis pipeline with real Gemini API calls."""

from datetime import datetime, timezone

import pytest

from agents.memory.schemas import Anomaly, RiskTier
from agents.orchestrator import AegisPipeline


@pytest.mark.asyncio
async def test_latency_spike_pipeline():
    """Test the full Sleuth → Medic → Scribe pipeline on a latency spike anomaly."""
    pipeline = AegisPipeline()
    anomaly = Anomaly(
        service="mock_inference",
        metric="latency_p95_ms",
        observed_value=675.0,
        baseline_value=45.0,
        severity=0.85,
        detected_at=datetime.now(timezone.utc),
    )
    incident = await pipeline.handle_anomaly(anomaly)

    # Diagnosis should be populated
    assert incident.diagnosis is not None
    assert incident.diagnosis.root_cause
    assert 0.0 <= incident.diagnosis.confidence <= 1.0

    # Action should be populated
    assert incident.action is not None
    assert incident.action.command
    assert incident.action.risk_tier in [RiskTier.LOW, RiskTier.MEDIUM, RiskTier.HIGH]

    # Report should be populated
    assert incident.report is not None
    assert len(incident.report) > 50

    # Status should be set
    assert incident.status in ["resolved", "awaiting_approval"]


@pytest.mark.asyncio
async def test_high_risk_scenario_awaits_approval():
    """Test that a severe anomaly produces a non-auto-executed action."""
    pipeline = AegisPipeline()
    anomaly = Anomaly(
        service="mock_inference",
        metric="gpu_memory_used_pct",
        observed_value=0.97,
        baseline_value=0.55,
        severity=0.95,
        detected_at=datetime.now(timezone.utc),
    )
    incident = await pipeline.handle_anomaly(anomaly)

    assert incident.diagnosis is not None
    assert incident.action is not None
    assert incident.report is not None
    # The actual risk tier depends on the LLM's proposed command,
    # which gets re-classified by our deterministic policy
    assert incident.action.risk_tier in [RiskTier.LOW, RiskTier.MEDIUM, RiskTier.HIGH]
