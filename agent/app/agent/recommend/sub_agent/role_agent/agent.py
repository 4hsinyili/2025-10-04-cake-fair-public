from google.adk.agents import LlmAgent

from app.agent.recommend.sub_agent.role_agent import prompt
from app.core import load_open_router_model

role_agent = LlmAgent(
    name="role_agent",
    model=load_open_router_model(),
    instruction=prompt.PROMPT,
    description="角色設計和回應風格分析 agent，負責解析使用者偏好並生成角色提示詞",
)
