"""DriverContainer 核心介面

此模組定義了 DriverContainer 系統的基礎介面和主要實作，
包括 Driver 抽象基類和 DriverContainer 主類別。
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


class Driver(ABC, Generic[T]):
    """驅動基礎介面

    所有具體驅動都必須實作此介面，提供統一的初始化、清理和健康檢查機制。
    """

    @abstractmethod
    async def initialize(self, config: dict[str, object]) -> T:
        """初始化驅動實例

        Args:
            config: 驅動配置字典

        Returns:
            初始化後的驅動實例

        Raises:
            Exception: 初始化失敗時拋出異常
        """
        pass

    @abstractmethod
    async def cleanup(self, instance: T) -> None:
        """清理驅動實例

        Args:
            instance: 要清理的驅動實例
        """
        pass

    @abstractmethod
    async def health_check(self, instance: T) -> bool:
        """健康檢查

        Args:
            instance: 要檢查的驅動實例

        Returns:
            True 表示健康，False 表示不健康
        """
        pass


@dataclass
class DriverConfig:
    """驅動配置

    統一管理所有驅動的配置資訊，支援從環境變數建立和測試環境配置。
    """

    # HTTPX 配置
    httpx: dict[str, object] = field(
        default_factory=lambda: {
            "timeout": 240.0,
            "max_keepalive": 20,
            "max_connections": 100,
            "retry": 3,
        }
    )

    # Cloud Storage 配置
    storage: dict[str, object] = field(
        default_factory=lambda: {
            "project": "your-gcp-project",
            "default_bucket": "your-default-bucket",
            "service_file": None,  # 服務帳戶金鑰檔案路徑
            "api_root": None,  # 用於本地模擬器
        }
    )

    # MongoDB 配置
    mongo: dict[str, object] = field(
        default_factory=lambda: {
            "host": "localhost",
            "port": 27017,
            "database": "test",
            "username": None,
            "password": None,
            "connection_string": None,  # 完整連接字串，優先於其他選項
            "server_api": "1",
            "connect_timeout_ms": 120000,
            "socket_timeout_ms": 120000,
        }
    )

    @classmethod
    def from_environment(cls) -> "DriverConfig":
        """從環境變數建立配置

        Returns:
            從環境變數建立的 DriverConfig 實例
        """
        # 這裡可以從 setting 或環境變數載入實際配置
        return cls()

    @classmethod
    def for_testing(cls) -> "DriverConfig":
        """測試環境配置

        Returns:
            適用於測試環境的 DriverConfig 實例
        """
        return cls(
            elasticsearch={"hosts": ["http://localhost:9200"]},
            redis={"host": "localhost", "port": 6379, "db": 1},
            httpx={"timeout": 5.0, "verify_ssl": False},
            mysql={"host": "localhost", "database": "test_db"},
            task={
                "project": "test-project",
                "location": "asia-east1",
                "chronous": "async",
                "semaphore": 5,
            },
            storage={"project": "test-project", "default_bucket": "test-bucket"},
        )


class DriverContainer:
    """驅動容器實作

    負責管理所有外部依賴服務的生命週期，包括初始化、獲取實例、
    健康檢查和資源清理。支援與 FastAPI app.state 的整合。
    """

    def __init__(self, config: DriverConfig, app_state: object = None):
        """初始化驅動容器

        Args:
            config: 驅動配置
            app_state: FastAPI app.state 或其他狀態管理物件
        """
        self.config = config
        self.app_state = app_state
        self._instances: dict[str, object] = {}
        self._drivers: dict[str, Driver] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._logger = logging.getLogger(__name__)

        # 註冊預設驅動
        self._register_default_drivers()

    def _register_default_drivers(self) -> None:
        """註冊預設驅動

        註冊系統內建的驅動實例，包括 Elasticsearch、Redis、HTTPX、MySQL、Task 和 Storage。
        """
        # 動態導入驅動，避免循環導入
        from .httpx import HttpxDriver
        from .mongo import MongoDriver
        from .storage import StorageDriver

        self._drivers["httpx"] = HttpxDriver()
        self._drivers["storage"] = StorageDriver()
        self._drivers["mongo"] = MongoDriver()

        # 為每個驅動建立鎖
        for name in self._drivers:
            self._locks[name] = asyncio.Lock()

    async def register_driver(self, name: str, driver: Driver) -> None:
        """註冊自訂驅動

        Args:
            name: 驅動名稱
            driver: 驅動實例
        """
        self._drivers[name] = driver
        self._locks[name] = asyncio.Lock()
        self._logger.info(f"Registered driver: {name}")

    def _get_from_app_state(self, name: str) -> object | None:
        """從 app.state 獲取已存在的實例

        Args:
            name: 驅動名稱

        Returns:
            找到的實例，如果沒有找到則返回 None
        """
        if self.app_state is None:
            return None

        # 支援多種命名慣例
        possible_names = [
            name,  # elasticsearch
            f"{name}_driver",  # elasticsearch_driver
            f"async_{name}_driver",  # async_elasticsearch_driver
            f"{name}_pool",  # mysql_pool
        ]

        for attr_name in possible_names:
            if hasattr(self.app_state, attr_name):
                instance = getattr(self.app_state, attr_name)
                if instance is not None:
                    self._logger.info(
                        f"Found existing instance for '{name}' in app.state as '{attr_name}'"
                    )
                    return instance

        return None

    def _store_to_app_state(self, name: str, instance: object) -> None:
        """將實例存儲到 app.state

        Args:
            name: 驅動名稱
            instance: 要存儲的實例
        """
        if self.app_state is None:
            return

        # 使用一致的命名慣例
        attr_name = f"{name}_driver"
        if name == "mysql":
            attr_name = f"{name}_pool"

        setattr(self.app_state, attr_name, instance)
        self._logger.info(f"Stored instance for '{name}' to app.state as '{attr_name}'")

    async def get_instance(self, name: str) -> object:
        """獲取驅動實例（優先從 app.state 獲取）

        Args:
            name: 驅動名稱

        Returns:
            驅動實例

        Raises:
            ValueError: 當驅動未註冊時
            Exception: 當初始化失敗時
        """
        if name not in self._drivers:
            raise ValueError(f"Driver '{name}' not registered")

        # 首先嘗試從 app.state 獲取
        existing_instance = self._get_from_app_state(name)
        if existing_instance is not None:
            return existing_instance

        # 檢查本地實例
        if name in self._instances:
            return self._instances[name]

        # 使用鎖確保線程安全
        async with self._locks[name]:
            # 雙重檢查
            existing_instance = self._get_from_app_state(name)
            if existing_instance is not None:
                return existing_instance

            if name in self._instances:
                return self._instances[name]

            try:
                # 獲取驅動配置
                driver_config = getattr(self.config, name, {})

                # 初始化驅動
                self._logger.info(f"Initializing driver: {name}")
                instance = await self._drivers[name].initialize(driver_config)

                # 同時存儲到本地和 app.state
                self._instances[name] = instance
                self._store_to_app_state(name, instance)

                self._logger.info(f"Driver '{name}' initialized successfully")
                return instance

            except Exception as e:
                self._logger.error(f"Failed to initialize driver '{name}': {e}")
                raise

    async def cleanup_all(self) -> None:
        """清理所有實例"""
        cleanup_tasks = []

        for name, instance in self._instances.items():
            if name in self._drivers:
                task = self._cleanup_instance(name, instance)
                cleanup_tasks.append(task)

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self._instances.clear()
        self._logger.info("All driver instances cleaned up")

    async def _cleanup_instance(self, name: str, instance: object) -> None:
        """清理單個實例

        Args:
            name: 驅動名稱
            instance: 要清理的實例
        """
        try:
            await self._drivers[name].cleanup(instance)
            self._logger.info(f"Driver '{name}' cleaned up successfully")
        except Exception as e:
            self._logger.error(f"Failed to cleanup driver '{name}': {e}")

    async def health_check_all(self) -> dict[str, bool]:
        """檢查所有服務健康狀態

        Returns:
            字典，鍵為驅動名稱，值為健康狀態
        """
        health_status = {}

        for name, instance in self._instances.items():
            if name in self._drivers:
                try:
                    is_healthy = await self._drivers[name].health_check(instance)
                    health_status[name] = is_healthy
                except Exception as e:
                    self._logger.error(f"Health check failed for '{name}': {e}")
                    health_status[name] = False

        return health_status

    @asynccontextmanager
    async def get_driver(self, name: str):
        """上下文管理器方式獲取客戶端

        Args:
            name: 驅動名稱

        Yields:
            驅動實例
        """
        instance = await self.get_instance(name)
        try:
            yield instance
        finally:
            # 在這裡可以添加使用後的清理邏輯
            pass

    # 便利方法
    async def get_httpx(self):
        """獲取 HTTPX 客戶端"""
        await self.get_instance("httpx")  # 確保初始化
        return await self.get_instance("httpx")

    async def get_storage(self):
        """獲取 Cloud Storage 客戶端"""
        await self.get_instance("storage")  # 確保初始化
        return await self.get_instance("storage")

    async def get_mongo(self):
        """獲取 MongoDB 客戶端"""
        await self.get_instance("mongo")  # 確保初始化
        return await self.get_instance("mongo")
