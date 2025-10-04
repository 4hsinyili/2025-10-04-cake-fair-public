from fastapi import APIRouter

from app.schema.agent import ChatPayload, RecommendPayload
from app.service.agent import chat_service, recommend_with_ranking_service, test_service

router = APIRouter(prefix="/agent", tags=["agent"])

@router.post("/chat/{chat_type}")
async def chat_endpoint(chat_type: str, payload: ChatPayload):
    # 直接返回 StreamingResponse，不需要額外的 async with
    return await chat_service(chat_type, payload)

@router.post("/recommend")
async def recommend_endpoint(payload: RecommendPayload):
    return await recommend_with_ranking_service(payload)

@router.post("/test")
async def test_endpoint():
    return await test_service()