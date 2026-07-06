import pytest
from agents.orchestrator import AegisPipeline
from agents.memory.schemas import Anomaly
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_latency_spike_triggers_auto_remediation():
    pipeline = AegisPipeline()
    anomaly = Anomaly(
        service="mock_inference",
        metric="latency_ms",
        observed_value=750,
        baseline_value=50,
        severity=0.9,
        detected_at=datetime.now(timezone.utc),
    )
    incident = await pipeline.handle_anomaly(anomaly)
    assert incident.diagnosis is not None
    assert incident.action is not None
    assert incident.report is not None
