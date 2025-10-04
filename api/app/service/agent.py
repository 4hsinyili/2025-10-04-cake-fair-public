"""此模組提供處理網域 (Domain) 相關的服務層邏輯。

包含了對單一或多個網域進行探索 (Search) 與提取 (Extract) 的叫用 (Defer) 函式，
以及執行 (Invoke) 網域註冊與提取的函式。
"""

import json

import nanoid
from fastapi.responses import StreamingResponse

from app.driver import get_httpx_client
from app.middleware.log import get_logger
from app.schema.agent import (
    ChatMessage,
    ChatPayload,
    RecommendationResponse,
    RecommendPayload,
)
from app.schema.mongo import ListStorePayload
from app.schema.util import to_dict
from app.service.mongo import list_drinks_service

logger = get_logger(__name__)

# 建立 streaming generator
async def stream_generator(payload: ChatPayload):
    async with await run_adk_app(
        app_name=payload.app_name,
        user_id=payload.user_id,
        session_id=payload.session_id,
        message=payload.message,
    ) as response:
        async for chunk in response.aiter_lines():
            yield chunk

def chats_to_message(chats: list[ChatMessage]) -> str:
    """將多個 ChatMessage 轉換為單一字串訊息"""
    return "\n".join([f"{chat.role}: {chat.content}" for chat in chats])

async def recommend_with_ranking_service(payload: RecommendPayload) -> RecommendationResponse:
    """推薦服務（結構化回應）
    
    提供完整的結構化回應，包含推薦文字和排序後的飲料列表。
    適用於需要對飲料進行排序和進一步處理的場景。
    
    Args:
        payload: 推薦請求參數
        
    Returns:
        RecommendationResponse: 包含推薦文字和排序飲料列表的完整回應
    """
    # 取得簡化版的飲料資料
    list_store_payload = ListStorePayload(
        location=payload.location,
        drink_tags=payload.drink_tags,
        brands=payload.brands,
    )
    drinks_response = await list_drinks_service(list_store_payload, limit=100)  # 限制數量以避免 token 過多
    drinks = [
        {
            "name": item["name"],
            "store_name": item["store_name"],
            "description": item.get("description", ""),
        }
        for item in drinks_response["data"][:3]
    ]
    response_preference = chats_to_message(payload.response_preference_chats)

    prompt = f"""
# 使用者的回應風格偏好
{response_preference}

# 飲料清單
{[to_dict(drink) for drink in drinks]}

請依據以上資料，推薦適合的飲料給使用者。
    """
    chat_payload = ChatPayload(
        app_name=payload.app_name,
        user_id=payload.user_id,
        session_id=payload.session_id,
        chat_type=payload.app_name,
        message=ChatMessage(
            role="user",
            content=prompt)
    )
    
    await init_adk_session(
        app_name=payload.app_name,
        user_id=payload.user_id,
        session_id=payload.session_id,
    )
    
    # 執行 ADK 應用程式 (非串流模式)
    response = await run_adk_app(
        app_name=payload.app_name,
        user_id=payload.user_id,
        session_id=payload.session_id,
        message=chat_payload.message,
        stream=False,
    )
    
    if response.status_code != 200:
        logger.error(f"ADK response error: {response.status_code} - {response.text}")
        return {
            "message": "抱歉，系統發生錯誤，可能是因為 LLM 服務呼叫太過頻繁，請稍後再試。如果持續發生，請聯絡開發者",
            "drinks": drinks_response["data"],
        }
    response_data = response.json()
    raw_message: str = response_data[-1]["content"]["parts"][0]["text"]
    try:
        message = json.loads(raw_message)["state"]["final_recommendation"]
    except Exception:
        message = raw_message.split('"""')[1].strip('"""').strip() if '"""' in raw_message else raw_message.strip()
        message = raw_message.split("'''")[1].strip("'''").strip() if "'''" in raw_message else raw_message.strip()
    return {
        "message": message,
        "drinks": drinks_response["data"],
    }




async def chat_service(chat_type: str, payload: ChatPayload):
    """與聊天機器人互動的服務

    Args:
        chat_type (str): 聊天類型
        payload (ChatPayload): 使用者訊息

    Returns:
        StreamingResponse: 來自 ADK 的串流回應
    """
    await init_adk_session(
        app_name=payload.app_name,
        user_id=payload.user_id,
        session_id=payload.session_id,
    )
    return StreamingResponse(stream_generator(payload), media_type="text/event-stream")


async def test_service():
    session_id = nanoid.generate(size=10)
    user_id = session_id
    app_name = "multi"
    await init_adk_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    response = await run_adk_app(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        message=ChatMessage(role="user", content="42, monkey"),
        stream=False,
    )
    data = response.json()
    print(data)
    httpx_client = await get_httpx_client()
    response = await httpx_client.get(
        url=f"http://localhost:3002/apps/{app_name}/users/{user_id}/sessions/{session_id}",
    )
    session_data = response.json()
    print(session_data)
    return {
        "response": data,
        "session": session_data,
    }


async def init_adk_session(app_name: str, user_id: str, session_id: str):
    """取得 ADK Session

    Args:
        app_name (str): 應用程式名稱
        user_id (str): 使用者 ID
        session_id (str): 會話 ID

    Returns:
        dict: ADK Session 資訊
    """
    httpx_client = await get_httpx_client()
    response = await httpx_client.get(
        url=f"http://localhost:3002/apps/{app_name}/users/{user_id}/sessions/{session_id}",
    )
    if response.status_code == 404:
        response = await httpx_client.post(
            url=f"http://localhost:3002/apps/{app_name}/users/{user_id}/sessions/{session_id}",
        )
    return response.json()

async def run_adk_app(app_name: str, user_id: str, session_id: str, message: ChatMessage, stream: bool = True):
    """執行 ADK 應用程式

    Args:
        app_name (str): 應用程式名稱
        user_id (str): 使用者 ID
        session_id (str): 會話 ID
        message (ChatMessage): 使用者訊息
        stream (bool, optional): 是否啟用串流. Defaults to True.
    Returns:
        httpx.Response: ADK streaming response
    """
    httpx_client = await get_httpx_client()
    # 使用 httpx_client.stream() 並返回 context manager'
    if stream:
        return httpx_client.stream(
            method="POST",
            url="http://localhost:3002/run",
            json={
                "appName": app_name,
                "userId": user_id,
                "sessionId": session_id,
                "newMessage": {
                    "parts": [
                        {
                            "text": message.content,
                        }
                    ],
                    "role": message.role,
                },
                "streaming": stream,
            },
        )
    else:
        response = await httpx_client.post(
            url="http://localhost:3002/run",
            json={
                "appName": app_name,
                "userId": user_id,
                "sessionId": session_id,
                "newMessage": {
                    "parts": [
                        {
                            "text": message.content,
                        }
                    ],
                    "role": message.role,
                },
                "streaming": stream,
            },
        )
        return response