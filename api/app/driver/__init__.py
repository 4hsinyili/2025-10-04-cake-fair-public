"""Driver 模組

此模組提供了統一的驅動管理系統，包括：
- Driver: 抽象基類，定義所有驅動的通用介面
- DriverConfig: 統一的驅動配置管理
- DriverContainer: 驅動容器，管理所有驅動的生命週期

具體驅動實作：
- HttpxDriver: HTTPX 客戶端驅動
- StorageDriver: Google Cloud Storage 驅動
- MongoDriver: MongoDB 驅動

使用範例：
    from app.driver import DriverContainer, DriverConfig

    config = DriverConfig.from_environment()
    container = DriverContainer(config)

    # 取得服務實例
    mongo = await container.get_instance("mongo")
"""

# 便利函式，用於從當前 FastAPI 應用程式狀態獲取驅動實例
from app.context import get_current_driver_container

from .base import Driver, DriverConfig, DriverContainer
from .httpx import HttpxDriver, httpx
from .mongo import AsyncMongoClient, MongoDriver
from .storage import Storage, StorageDriver


async def get_driver(driver_name: str):
    """獲取 DriverContainer"""
    container = get_current_driver_container()
    driver = container._drivers.get(driver_name)
    await container.get_instance(driver_name)
    return driver


# 便利函式，用於快速獲取各種驅動實例
async def get_httpx_driver() -> HttpxDriver:
    """獲取 HTTPX 驅動實例"""
    return await get_driver("httpx")


async def get_storage_driver() -> StorageDriver:
    """獲取 Storage 驅動實例"""
    return await get_driver("storage")
async def get_mongo_driver() -> MongoDriver:
    """獲取 Mongo 驅動實例"""
    return await get_driver("mongo")

# 便利函式，用於快速獲取各種客戶端
async def get_storage_client() -> Storage:
    """獲取 Storage 客戶端"""
    container = get_current_driver_container()
    return await container.get_storage()


async def get_httpx_client() -> httpx.AsyncClient:
    """獲取 HTTPX 客戶端"""
    container = get_current_driver_container()
    return await container.get_httpx()

async def get_mongo_client() -> AsyncMongoClient:
    """獲取 Mongo 客戶端"""
    container = get_current_driver_container()
    return await container.get_mongo()

__all__ = [
    # 核心類別
    "Driver",
    "DriverConfig",
    "DriverContainer",
    # 具體驅動實作
    "HttpxDriver",
    "StorageDriver",
    "MongoDriver",
    # 便利函式
    "get_driver",
    "get_httpx_driver",
    "get_storage_driver"
    "get_mongo_driver",
    "get_httpx_client",
    "get_storage_client",
    "get_mongo_client",
]
