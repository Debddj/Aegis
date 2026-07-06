"""Aegis Pipeline Orchestrator — wires Sentry → Sleuth → Medic → Scribe."""

import uuid
import json
import asyncio
import logging
from datetime import datetime, timezone

from google.adk import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from agents.sentry.agent import sentry_agent
from agents.sleuth.agent import sleuth_agent
from agents.medic.agent import medic_agent
from agents.scribe.agent import scribe_agent
from agents.memory.schemas import Anomaly, Diagnosis, RemediationAction, Incident, RiskTier
from agents.medic.risk_policy import classify_risk

logger = logging.getLogger("aegis.orchestrator")

# Timeout for any single LLM agent call (seconds)
AGENT_TIMEOUT_SECONDS = 120


def _strip_markdown_json(raw: str) -> str:
    """Strip markdown code fences from LLM JSON output."""
    s = raw.strip()
    if s.startswith("```json"):
        s = s[7:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


class AegisPipeline:
    """Orchestrates the 4-agent incident response pipeline."""

    def __init__(self):
        self.sentry = sentry_agent
        self.sleuth = sleuth_agent
        self.medic = medic_agent
        self.scribe = scribe_agent
        # Shared session service — reused across calls for efficiency
        self._session_service = InMemorySessionService()

    async def _run_agent(self, agent, input_str: str) -> str:
        """Run a single agent with timeout and error handling."""
        # Unique session per call to avoid state collisions
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        runner = Runner(
            agent=agent,
            session_service=self._session_service,
            app_name="aegis_app",
            auto_create_session=True,
        )

        output_text = ""
        try:
            async with asyncio.timeout(AGENT_TIMEOUT_SECONDS):
                async for event in runner.run_async(
                    user_id="system",
                    session_id=session_id,
                    new_message=types.Content(
                        parts=[types.Part(text=input_str)]
                    ),
                ):
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                output_text += part.text
        except asyncio.TimeoutError:
            logger.error(
                "Agent %s timed out after %ds",
                agent.name, AGENT_TIMEOUT_SECONDS,
            )
            raise RuntimeError(
                f"Agent '{agent.name}' timed out after {AGENT_TIMEOUT_SECONDS}s"
            )
        except Exception:
            logger.exception("Agent %s failed", agent.name)
            raise

        logger.info(
            "Agent %s completed — output length: %d chars",
            agent.name, len(output_text),
        )
        return output_text

    async def run_sentry(self, metrics_context: str) -> Anomaly:
        """Run Sentry to analyze metrics and produce an anomaly report."""
        logger.info("▶ Running Sentry (monitoring)…")
        raw = await self._run_agent(self.sentry, metrics_context)

        try:
            data = json.loads(_strip_markdown_json(raw))
            anomaly = Anomaly(**data)
        except Exception:
            logger.warning("Sentry output was not valid JSON — using defaults")
            anomaly = Anomaly(
                service="unknown",
                metric="unknown",
                observed_value=0.0,
                baseline_value=0.0,
                severity=0.5,
                detected_at=datetime.now(timezone.utc),
            )
        return anomaly

    async def handle_anomaly(self, anomaly: Anomaly) -> Incident:
        """Run the full Sleuth → Medic → Scribe pipeline on a known anomaly."""
        incident_id = str(uuid.uuid4())
        incident = Incident(
            id=incident_id,
            anomaly=anomaly,
            created_at=datetime.now(timezone.utc),
        )
        logger.info("═══ Incident %s opened for %s/%s ═══",
                     incident_id[:8], anomaly.service, anomaly.metric)

        # ── 1. Sleuth: root-cause diagnosis ─────────────────────────────
        logger.info("▶ Running Sleuth (diagnosis)…")
        try:
            diagnosis_str = await self._run_agent(
                self.sleuth, anomaly.model_dump_json()
            )
            diagnosis_data = json.loads(_strip_markdown_json(diagnosis_str))
            diagnosis = Diagnosis(**diagnosis_data)
        except Exception as exc:
            logger.warning("Sleuth parse failed (%s) — using raw text", exc)
            diagnosis = Diagnosis(
                root_cause=diagnosis_str if 'diagnosis_str' in dir() else str(exc),
                confidence=0.5,
                correlated_signals=[],
            )
        incident.diagnosis = diagnosis
        logger.info("  Root cause (%.0f%% confidence): %s",
                     diagnosis.confidence * 100, diagnosis.root_cause[:120])

        # ── 2. Medic: propose remediation ────────────────────────────────
        logger.info("▶ Running Medic (remediation)…")
        try:
            action_str = await self._run_agent(
                self.medic, diagnosis.model_dump_json()
            )
            action_data = json.loads(_strip_markdown_json(action_str))
            action = RemediationAction(**action_data)
        except Exception as exc:
            logger.warning("Medic parse failed (%s) — fallback to manual", exc)
            action = RemediationAction(
                description=f"Manual intervention required: {action_str if 'action_str' in dir() else str(exc)}",
                command="manual_intervention()",
                risk_tier=RiskTier.HIGH,
                reversible=False,
            )

        # Re-classify risk using our deterministic policy (don't trust LLM)
        action.risk_tier = classify_risk(action.command)
        incident.action = action

        # Auto-execute only low-risk actions
        if action.risk_tier == RiskTier.LOW:
            action.auto_executed = True
            logger.info("  ✓ Auto-executing (low risk): %s", action.command)
            from agents.medic.tools import execute_remediation
            remediation_result = execute_remediation(action.command)
            logger.info("  Remediation result: %s", remediation_result)
        else:
            logger.info("  ⏳ Awaiting approval (%s risk): %s",
                         action.risk_tier.value, action.command)

        # ── 3. Scribe: write postmortem ──────────────────────────────────
        logger.info("▶ Running Scribe (reporting)…")
        try:
            report = await self._run_agent(
                self.scribe, incident.model_dump_json()
            )
        except Exception as exc:
            logger.warning("Scribe failed (%s) — using placeholder", exc)
            report = f"# Incident {incident_id}\n\nReport generation failed: {exc}"
        incident.report = report
        incident.status = "resolved" if action.auto_executed else "awaiting_approval"

        # Save and store report programmatically
        from agents.scribe.tools import save_report, store_in_memory
        save_report(report, incident_id)
        # Index in incident history memory
        store_in_memory(incident.model_dump_json())

        logger.info("═══ Incident %s → %s ═══", incident_id[:8], incident.status)
        return incident

    async def run_full_pipeline(self, metrics_context: str) -> Incident:
        """Run the complete Sentry → Sleuth → Medic → Scribe pipeline."""
        anomaly = await self.run_sentry(metrics_context)
        return await self.handle_anomaly(anomaly)
