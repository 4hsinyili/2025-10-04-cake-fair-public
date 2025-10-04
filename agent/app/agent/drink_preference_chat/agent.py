from google.adk.agents import LlmAgent

from app.agent.drink_preference_chat import prompt
from app.core import load_open_router_model

root_agent = LlmAgent(
    name="root_agent",
    model=load_open_router_model(),
    instruction=prompt.PROMPT,
    description="root agent for drink preference assistant",
)
