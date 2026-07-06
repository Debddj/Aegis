from google.adk.agents import Agent

from .prompts import SLEUTH_SYSTEM_PROMPT
from .tools import correlate_logs, get_recent_deploys, query_incident_memory

sleuth_agent = Agent(
    name="sleuth",
    model="gemini-2.5-flash",
    instruction=SLEUTH_SYSTEM_PROMPT,
    tools=[correlate_logs, get_recent_deploys, query_incident_memory],
)
