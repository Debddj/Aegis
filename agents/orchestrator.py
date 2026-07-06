import uuid
import json
from google.adk import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from agents.sentry.agent import sentry_agent
from agents.sleuth.agent import sleuth_agent
from agents.medic.agent import medic_agent
from agents.scribe.agent import scribe_agent
from agents.memory.schemas import Anomaly, Diagnosis, RemediationAction, Incident

class AegisPipeline:
    def __init__(self):
        self.sentry = sentry_agent
        self.sleuth = sleuth_agent
        self.medic = medic_agent
        self.scribe = scribe_agent

    async def _run_agent(self, agent, input_str: str) -> str:
        session_service = InMemorySessionService()
        runner = Runner(agent=agent, session_service=session_service, app_name="aegis_app", auto_create_session=True)
        
        output_text = ""
        async for event in runner.run_async(
            user_id="system",
            session_id="default_session",
            new_message=types.Content(parts=[types.Part(text=input_str)])
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        output_text += part.text
        return output_text

    async def handle_anomaly(self, anomaly: Anomaly) -> Incident:
        incident = Incident(id=str(uuid.uuid4()), anomaly=anomaly)

        # 1. Run Sleuth for root-cause diagnosis
        diagnosis_str = await self._run_agent(self.sleuth, anomaly.model_dump_json())
        try:
            # Try to strip markdown code blocks if the agent wrapped the JSON output
            clean_str = diagnosis_str.strip()
            if clean_str.startswith("```json"):
                clean_str = clean_str[7:]
            if clean_str.endswith("```"):
                clean_str = clean_str[:-3]
            clean_str = clean_str.strip()
            
            diagnosis_data = json.loads(clean_str)
            diagnosis = Diagnosis(**diagnosis_data)
        except Exception:
            diagnosis = Diagnosis(
                root_cause=diagnosis_str,
                confidence=0.5,
                correlated_signals=[]
            )
        incident.diagnosis = diagnosis

        # 2. Run Medic to propose remediation
        action_str = await self._run_agent(self.medic, diagnosis.model_dump_json())
        try:
            clean_str = action_str.strip()
            if clean_str.startswith("```json"):
                clean_str = clean_str[7:]
            if clean_str.endswith("```"):
                clean_str = clean_str[:-3]
            clean_str = clean_str.strip()
            
            action_data = json.loads(clean_str)
            action = RemediationAction(**action_data)
        except Exception:
            action = RemediationAction(
                description=f"Manual intervention required: {action_str}",
                command="manual_intervention()",
                risk_tier="high",
                reversible=False
            )
        
        incident.action = action
        if action.risk_tier == "low":
            action.auto_executed = True

        # 3. Run Scribe to write the report
        report = await self._run_agent(self.scribe, incident.model_dump_json())
        incident.report = report

        return incident
