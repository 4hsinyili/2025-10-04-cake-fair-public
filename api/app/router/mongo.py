from fastapi import APIRouter

from app.schema.mongo import ListStorePayload
from app.service.mongo import (
    list_brand_service,
    list_company_service,
    list_drink_tag_service,
    list_drinks_service,
    list_store_service,
)

router = APIRouter(prefix="/mongo", tags=["mongo"])

@router.post("/list/store")
async def list_store_endpoint(
    payload: ListStorePayload
):
    return await list_store_service(payload)

@router.post("/list/drink")
async def list_drink_endpoint(
    payload: ListStorePayload,
    limit: int | None = None
):
    return await list_drinks_service(payload, limit)

@router.get("/store/{store_id}")
async def get_store_endpoint(store_id: str):
    pass

@router.get("/list/company")
async def list_company_endpoint():
    return await list_company_service()

@router.get("/list/brand")
async def list_brand_endpoint():
    return await list_brand_service()

@router.get("/list/drink_tag")
async def list_drink_tag_endpoint():
    return await list_drink_tag_service()
