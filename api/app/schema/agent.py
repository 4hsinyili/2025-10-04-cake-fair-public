from typing import Literal

from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str

@dataclass(slots=True)
class ChatPayload:
    app_name: str
    user_id: str
    session_id: str
    chat_type: Literal["drink_preference_chat", "response_preference_chat", "recommend"]
    message: ChatMessage
    
@dataclass(slots=True)
class RecommendPayload:
    location: tuple[float, float]
    drink_tags: list[str]
    brands: list[str]
    response_preference_chats: list[ChatMessage]
    user_id: str
    session_id: str
    drink_preference_chats: list[ChatMessage] = Field(default_factory=list)
    app_name: str = "recommend"

@dataclass(slots=True)
class SimplifiedDrinkItem:
    """簡化版的飲料資料模型，只包含推薦必要欄位"""
    name: str
    store_name: str

@dataclass(slots=True)
class SimplifiedDrinkResponse:
    """簡化版的飲料列表回應"""
    data: list[SimplifiedDrinkItem]

@dataclass(slots=True)
class RecommendationResponse:
    """推薦服務的完整回應"""
    message: str  # ADK 生成的推薦文字
    drinks: list[SimplifiedDrinkItem]  # 排序後的飲料列表