from google.adk.agents import LlmAgent

from app.agent.recommend.sub_agent.text_response_agent import prompt
from app.core import load_open_router_model

text_response_agent = LlmAgent(
    name="text_response_agent",
    model=load_open_router_model(),
    instruction=prompt.PROMPT,
    description="文字回應生成 agent，負責整合角色設定和飲料排序，生成最終推薦文字",
)
