"""Failure scenario definitions for the Aegis simulator."""

from dataclasses import dataclass, field


@dataclass
class FailureScenario:
    """A failure scenario that can be injected into the simulator."""
    name: str
    description: str
    state_mutations: dict = field(default_factory=dict)
    duration_seconds: int = 300  # default 5 minutes
    cascading_effects: list[str] = field(default_factory=list)


# ── Scenario registry ────────────────────────────────────────────────────

SCENARIOS = {
    "latency_spike": FailureScenario(
        name="latency_spike",
        description="Simulates a sudden latency increase caused by a model rollout. "
                    "P95 latency jumps from ~45ms to ~675ms.",
        state_mutations={
            "latency_multiplier": 15.0,
        },
        cascading_effects=[
            "Throughput drops as requests queue behind slow inference.",
            "Client-side timeouts may begin triggering error_rate increase.",
        ],
    ),
    "error_spike": FailureScenario(
        name="error_spike",
        description="Simulates a surge in 5xx errors from the inference service, "
                    "typically caused by OOM kills or bad model weights.",
        state_mutations={
            "error_rate": 0.45,
        },
        cascading_effects=[
            "Upstream services see degraded response quality.",
            "Retry storms may amplify load.",
        ],
    ),
    "gpu_oom": FailureScenario(
        name="gpu_oom",
        description="Simulates GPU memory exhaustion with fragmentation. "
                    "GPU usage at 97%, memory fragmented, latency elevated.",
        state_mutations={
            "gpu_memory_used_pct": 0.97,
            "gpu_memory_fragmented": True,
            "latency_multiplier": 8.0,
        },
        cascading_effects=[
            "New batch requests may be rejected.",
            "Latency degrades as GPU memory thrashes.",
            "OOM kills may follow if not remediated.",
        ],
    ),
    "data_drift": FailureScenario(
        name="data_drift",
        description="Simulates input data distribution shift (PSI=0.35, threshold is 0.10). "
                    "Model predictions become unreliable.",
        state_mutations={
            "data_drift_score": 0.35,
        },
        cascading_effects=[
            "Model accuracy degrades silently.",
            "Downstream decision quality drops.",
        ],
    ),
    "cascading_failure": FailureScenario(
        name="cascading_failure",
        description="Simulates a multi-system failure: elevated latency + errors + "
                    "GPU stress + data drift. The worst-case scenario.",
        state_mutations={
            "latency_multiplier": 12.0,
            "error_rate": 0.30,
            "gpu_memory_used_pct": 0.92,
            "gpu_memory_fragmented": True,
            "data_drift_score": 0.22,
        },
        duration_seconds=600,
        cascading_effects=[
            "All service health indicators degrade simultaneously.",
            "Automated remediation may need to triage multiple signals.",
            "Human escalation likely required.",
        ],
    ),
}


def get_scenario(name: str) -> FailureScenario | None:
    """Look up a scenario by name."""
    return SCENARIOS.get(name)


def list_scenarios() -> list[str]:
    """Return all available scenario names."""
    return list(SCENARIOS.keys())
