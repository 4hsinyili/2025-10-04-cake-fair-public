from google.adk.agents import LlmAgent, SequentialAgent

from app.agent.recommend.sub_agent.context_agent import prompt as context_prompt
from app.agent.recommend.sub_agent.role_agent import prompt as role_prompt
from app.agent.recommend.sub_agent.text_response_agent import (
    prompt as text_response_prompt,
)
from app.core import load_open_router_model


def create_root_agent():
    """建立並回傳 root_agent 實例"""
    # 建立子代理實例
    context_agent = LlmAgent(
        name="context_agent",
        model=load_open_router_model(),
        instruction=context_prompt.PROMPT,
        description="情境分析 agent，負責分析時間、季節、天氣等環境因素，為飲料推薦提供情境化建議",
    )

    role_agent = LlmAgent(
        name="role_agent",
        model=load_open_router_model(),
        instruction=role_prompt.PROMPT,
        description="角色設計和回應風格分析 agent，負責解析使用者偏好並生成角色提示詞",
    )

    # order_agent = LlmAgent(
    #     name="order_agent",
    #     model=load_open_router_model(),
    #     instruction=order_prompt.PROMPT,
    #     description="飲料排序 agent，負責根據使用者偏好對飲料菜單進行智慧排序",
    # )

    text_response_agent = LlmAgent(
        name="text_response_agent",
        model=load_open_router_model(),
        instruction=text_response_prompt.PROMPT,
        description="文字回應生成 agent，負責整合角色設定和情境，並生成最終推薦文字",
    )

    # 建立根代理
    root_agent = SequentialAgent(
        name="root_agent",
        description="飲料推薦系統主協調者，管理整個推薦流程",
        sub_agents=[
            context_agent,
            role_agent,
            # order_agent,
            text_response_agent,
        ],
    )

    return root_agent


# 建立代理實例
root_agent = create_root_agent()
