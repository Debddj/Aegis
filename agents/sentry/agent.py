from google.adk.agents import Agent
from .tools import fetch_recent_metrics, compute_baseline_deviation
from .prompts import SENTRY_SYSTEM_PROMPT

sentry_agent = Agent(
    name="sentry",
    model="gemini-2.0-flash",
    instruction=SENTRY_SYSTEM_PROMPT,
    tools=[fetch_recent_metrics, compute_baseline_deviation],
)
