"""此模組提供處理網域 (Domain) 相關的服務層邏輯。

包含了對單一或多個網域進行探索 (Search) 與提取 (Extract) 的叫用 (Defer) 函式，
以及執行 (Invoke) 網域註冊與提取的函式。
"""

import traceback

from fastapi import HTTPException
from pydantic import BaseModel

from app.driver import get_mongo_driver
from app.middleware.log import get_logger
from app.schema.agent import SimplifiedDrinkItem, SimplifiedDrinkResponse
from app.schema.db import DrinkTagDoc
from app.schema.mongo import Brand, Company, ListStorePayload

logger = get_logger(__name__)


async def list_store_service(payload: ListStorePayload):
    """列出所有 Store

    Args:
        payload (ListStorePayload): 查詢參數

    Returns:
        list: Store 列表
    """
    try:
        mongo_driver = await get_mongo_driver()
        stores = await mongo_driver.find_drink_stores_with_menu(
            longitude=payload.location[0],
            latitude=payload.location[1],
            drink_tags=payload.drink_tags,
            brands=payload.brands,
            review_count_range=payload.review_count_range,
            rating_range=payload.rating_range,
            distance_range=payload.distance_range,
            platform=payload.platform,
        )
        return {"data": stores}
    except Exception as e:
        logger.error(f"Error in list_store_service: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def list_drinks_service(payload: ListStorePayload, limit: int | None = 100):
    """列出符合條件的飲料菜單項目

    Args:
        payload (ListStorePayload): 查詢參數
        limit (int | None): 限制結果數量

    Returns:
        dict: 包含飲料菜單項目列表的字典
        每個菜單項目都附帶所屬店家的完整資訊
    """
    try:
        mongo_driver = await get_mongo_driver()
        drinks = await mongo_driver.find_drinks(
            longitude=payload.location[0],
            latitude=payload.location[1],
            drink_tags=payload.drink_tags,
            brands=payload.brands,
            review_count_range=payload.review_count_range,
            rating_range=payload.rating_range,
            distance_range=payload.distance_range,
            platform=payload.platform,
            limit=limit,
        )
        return {"data": drinks}
    except Exception as e:
        logger.error(f"Error in list_drinks_service: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

class ListCompanyResponse(BaseModel):
    data: list[Company]

async def list_company_service():
    mongo_driver = await get_mongo_driver()
    companies = await mongo_driver.find(
        collection_name="company",
    )
    return ListCompanyResponse(data=companies)

class ListDrinkTagResponse(BaseModel):
    data: list[DrinkTagDoc]

async def list_drink_tag_service():
    mongo_driver = await get_mongo_driver()
    # get all items with count greater than 5 and sort by count desc
    drink_tags = await mongo_driver.find(
        collection_name="drink_tag",
        filter_={"count": {"$gt": 5}},
        sort=[("count", -1)],
        limit=1000
    )
    drink_tags.sort(key=lambda x: len(x["name"]))
    return ListDrinkTagResponse(data=drink_tags)

class ListBrandResponse(BaseModel):
    data: list[Brand]

async def list_brand_service():
    mongo_driver = await get_mongo_driver()
    brands = await mongo_driver.find(
        collection_name="brand",
        filter_={
            "has_chain": True,
            "chain_count": {"$gt": 1},
            "platforms": "ubereats"
        },
        sort=[("chain_count", -1)],
        limit=1000
    )
    return ListBrandResponse(data=brands)


def _build_store_url(store_id: str, platform: str) -> str:
    """建立店家網址
    
    Args:
        store_id: 店家 ID
        platform: 平台名稱
    
    Returns:
        完整的店家網址
    """
    if platform == "ubereats":
        return f"https://www.ubereats.com/tw/store/{store_id}"
    elif platform == "foodpanda":
        return f"https://www.foodpanda.com.tw/restaurant/{store_id}"
    else:
        return ""


def _convert_to_simplified_drinks(raw_drinks: list[dict[str, object]]) -> list[SimplifiedDrinkItem]:
    """將完整的飲料資料轉換成簡化版本
    
    Args:
        raw_drinks: 從 MongoDB 查詢的完整飲料資料
    
    Returns:
        簡化版的飲料資料列表
    """
    simplified_drinks = []
    
    for drink in raw_drinks:
        # 提取店家資料
        store_data = drink.get("store", {})
        store_name = store_data.get("name", "")
        store_id = store_data.get("store_id", "")
        platform = store_data.get("platforms", "ubereats")
        
        # 建立簡化版的飲料資料
        simplified_drink = SimplifiedDrinkItem(
            name=drink.get("name", ""),
            description=drink.get("description"),
            image_url=None,  # 目前資料庫中沒有圖片網址，需要後續補充
            store_name=store_name,
            store_id=store_id,
            store_url=_build_store_url(store_id, platform)
        )
        simplified_drinks.append(simplified_drink)
    
    return simplified_drinks


async def list_simplified_drinks_service(payload: ListStorePayload, limit: int | None = None) -> SimplifiedDrinkResponse:
    """列出符合條件的飲料菜單項目（簡化版）
    
    此函式只回傳推薦系統必要的欄位，大幅減少資料大小和 token 用量。
    
    Args:
        payload (ListStorePayload): 查詢參數
        limit (int | None): 限制結果數量
    
    Returns:
        SimplifiedDrinkResponse: 包含簡化飲料資料列表的回應
    """
    try:
        mongo_driver = await get_mongo_driver()
        # 使用現有的 find_drinks 方法取得完整資料
        raw_drinks = await mongo_driver.find_drinks(
            longitude=payload.location[0],
            latitude=payload.location[1],
            drink_tags=payload.drink_tags,
            brands=payload.brands,
            review_count_range=payload.review_count_range,
            rating_range=payload.rating_range,
            distance_range=payload.distance_range,
            platform=payload.platform,
            limit=limit,
        )
        
        # 轉換成簡化版本
        simplified_drinks = _convert_to_simplified_drinks(raw_drinks)
        
        return SimplifiedDrinkResponse(data=simplified_drinks)
    except Exception as e:
        logger.error(f"Error in list_simplified_drinks_service: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error")
