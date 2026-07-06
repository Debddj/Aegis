from google.adk.agents import Agent
from .tools import restart_pod, rollback_model, rebalance_queue
from .risk_policy import classify_risk
from .prompts import MEDIC_SYSTEM_PROMPT

medic_agent = Agent(
    name="medic",
    model="gemini-2.5-flash",
    instruction=MEDIC_SYSTEM_PROMPT,
    tools=[restart_pod, rollback_model, rebalance_queue, classify_risk],
)
