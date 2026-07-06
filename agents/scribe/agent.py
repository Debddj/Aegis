from google.adk.agents import Agent
from .tools import save_report, store_in_memory
from .prompts import SCRIBE_SYSTEM_PROMPT

scribe_agent = Agent(
    name="scribe",
    model="gemini-2.0-flash",
    instruction=SCRIBE_SYSTEM_PROMPT,
    tools=[save_report, store_in_memory],
)
