from google.adk.agents import LlmAgent

from app.agent.recommend.sub_agent.order_agent import prompt
from app.core import load_open_router_model

order_agent = LlmAgent(
    name="order_agent",
    model=load_open_router_model(),
    instruction=prompt.PROMPT,
    description="飲料排序 agent，負責根據使用者偏好對飲料菜單進行智慧排序",
)
