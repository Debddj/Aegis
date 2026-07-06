from google.adk.agents import Agent

from .prompts import SENTRY_SYSTEM_PROMPT
from .tools import compute_baseline_deviation, fetch_recent_metrics

sentry_agent = Agent(
    name="sentry",
    model="gemini-2.5-flash",
    instruction=SENTRY_SYSTEM_PROMPT,
    tools=[fetch_recent_metrics, compute_baseline_deviation],
)
