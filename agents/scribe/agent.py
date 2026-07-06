from google.adk.agents import Agent

from .prompts import SCRIBE_SYSTEM_PROMPT

scribe_agent = Agent(
    name="scribe",
    model="gemini-2.5-flash",
    instruction=SCRIBE_SYSTEM_PROMPT,
)
