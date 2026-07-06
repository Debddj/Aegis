from google.adk.agents import Agent

from .prompts import MEDIC_SYSTEM_PROMPT
from .tools import rebalance_queue, restart_pod, rollback_model

medic_agent = Agent(
    name="medic",
    model="gemini-2.5-flash",
    instruction=MEDIC_SYSTEM_PROMPT,
    tools=[restart_pod, rollback_model, rebalance_queue],
)
