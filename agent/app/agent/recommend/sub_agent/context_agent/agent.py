from google.adk.agents import LlmAgent

from app.agent.recommend.sub_agent.context_agent import prompt
from app.core import load_open_router_model

context_agent = LlmAgent(
    name="context_agent",
    model=load_open_router_model(),
    instruction=prompt.PROMPT,
    description="情境分析 agent，負責分析時間、季節、天氣等環境因素，為飲料推薦提供情境化建議",
)
