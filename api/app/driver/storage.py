"""Google Cloud Storage 驅動實作

提供 Google Cloud Storage 非同步客戶端的初始化、清理和健康檢查功能。
支援檔案上傳、下載、列表和刪除等基本操作。
基於 gcloud-aio-storage 套件實作。
"""

import logging
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    from gcloud.aio.storage import Bucket, Storage
else:
    try:
        from gcloud.aio.storage import Bucket, Storage
    except ImportError:
        Storage = None
        Bucket = None

from app.driver.base import Driver


class StorageDriver(Driver["Storage"]):
    """Google Cloud Storage 驅動實作

    管理 Google Cloud Storage 非同步客戶端的生命週期，
    支援檔案上傳、下載、列表和刪除等基本操作。
    """

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._driver: Storage
        self._project: str
        self._default_bucket: str

    async def initialize(self, config: dict[str, object]) -> "Storage":
        """初始化 Cloud Storage 客戶端

        Args:
            config: Cloud Storage 配置字典，支援以下選項：
                - project: GCP 專案 ID（必要）
                - service_file: 服務帳戶金鑰檔案路徑（可選）
                - default_bucket: 預設儲存桶名稱（可選）
                - api_root: API 根路徑，用於本地模擬器（可選）

        Returns:
            初始化後的 Cloud Storage 客戶端
        """
        self._validate_dependencies()
        self._extract_config(config)

        try:
            client = await self._create_driver(config)
            await self._test_connection(client)

            self._logger.info("Cloud Storage client initialized successfully")
            return client

        except Exception as e:
            self._logger.error(f"Failed to initialize Cloud Storage client: {e}")
            raise

    def _validate_dependencies(self) -> None:
        """驗證必要的依賴套件"""
        if Storage is None:
            raise ImportError(
                "gcloud-aio-storage package is required for StorageDriver"
            )

    def _extract_config(self, config: dict[str, object]) -> None:
        """提取並驗證配置參數"""
        project = config.get("project")
        default_bucket = config.get("default_bucket")

        if not project:
            raise ValueError("project is required for StorageDriver")

        self._project = str(project)
        self._default_bucket = str(default_bucket) if default_bucket else None

        self._logger.info(
            f"Initializing Cloud Storage client: {project} "
            f"(default_bucket: {default_bucket})"
        )

    async def _create_driver(self, config: dict[str, object]) -> "Storage":
        """建立 Cloud Storage 客戶端"""
        client_kwargs = {}

        if service_file := config.get("service_file"):
            client_kwargs["service_file"] = service_file

        if api_root := config.get("api_root"):
            client_kwargs["api_root"] = api_root

        client = Storage(**client_kwargs)
        self._driver = client
        return client

    async def _test_connection(self, client: "Storage") -> None:
        """測試客戶端連線"""
        try:
            # 嘗試列出儲存桶來測試連線
            buckets = await client.list_buckets(self._project)
            self._logger.debug(
                f"Connection test successful (found {len(buckets)} buckets)"
            )
        except Exception as e:
            self._logger.warning(
                f"Client connectivity test failed (this may be normal): {e}"
            )

    async def cleanup(self, instance: "Storage") -> None:
        """清理 Cloud Storage 客戶端"""
        try:
            await instance.close()
            self._logger.info("Cloud Storage client closed successfully")

            self._reset_state()

        except Exception as e:
            self._logger.error(f"Error closing Cloud Storage client: {e}")

    def _reset_state(self) -> None:
        """重置內部狀態"""
        self._driver = None

    async def health_check(self, instance: "Storage") -> bool:
        """Cloud Storage 健康檢查"""
        if not self._is_initialized():
            self._logger.warning("Driver not properly initialized, health check failed")
            return False

        return await self._perform_health_check(instance)

    def _is_initialized(self) -> bool:
        """檢查驅動是否已正確初始化"""
        return self._project is not None and self._driver is not None

    async def _perform_health_check(self, instance: "Storage") -> bool:
        """執行實際的健康檢查"""
        try:
            # 嘗試列出儲存桶來驗證連線
            buckets = await instance.list_buckets(self._project)
            self._logger.debug(
                f"Health check successful (found {len(buckets)} buckets)"
            )
            return True

        except Exception as e:
            self._logger.debug(f"Health check failed: {e}")
            return False

    # === 公開 API 方法 ===

    def get_bucket(self, bucket_name: str | None = None) -> "Bucket":
        """取得儲存桶物件

        Args:
            bucket_name: 儲存桶名稱，如未提供則使用預設儲存桶

        Returns:
            儲存桶物件
        """
        self._ensure_initialized()

        bucket_name = bucket_name or self._default_bucket
        if not bucket_name:
            raise ValueError(
                "bucket_name is required or default_bucket must be configured"
            )

        return self._driver.get_bucket(bucket_name)

    async def list_buckets(self, **kwargs) -> list["Bucket"]:
        """列出專案中的所有儲存桶

        Returns:
            儲存桶列表
        """
        self._ensure_initialized()
        return await self._driver.list_buckets(self._project, **kwargs)

    async def upload(
        self,
        object_name: str,
        file_data: str | bytes | IO,
        bucket_name: str | None = None,
        **kwargs,
    ) -> dict[str, object]:
        """上傳檔案到 Cloud Storage

        Args:
            object_name: 物件名稱（路徑）
            file_data: 檔案資料
            bucket_name: 儲存桶名稱，如未提供則使用預設儲存桶
            **kwargs: 其他上傳參數（content_type, metadata 等）

        Returns:
            上傳結果
        """
        self._ensure_initialized()

        bucket_name = bucket_name or self._default_bucket
        if not bucket_name:
            raise ValueError(
                "bucket_name is required or default_bucket must be configured"
            )

        return await self._driver.upload(bucket_name, object_name, file_data, **kwargs)

    async def upload_from_filename(
        self, object_name: str, filename: str, bucket_name: str | None = None, **kwargs
    ) -> dict[str, object]:
        """從檔案路徑上傳檔案到 Cloud Storage

        Args:
            object_name: 物件名稱（路徑）
            filename: 本地檔案路徑
            bucket_name: 儲存桶名稱，如未提供則使用預設儲存桶
            **kwargs: 其他上傳參數

        Returns:
            上傳結果
        """
        self._ensure_initialized()

        bucket_name = bucket_name or self._default_bucket
        if not bucket_name:
            raise ValueError(
                "bucket_name is required or default_bucket must be configured"
            )

        return await self._driver.upload_from_filename(
            bucket_name, object_name, filename, **kwargs
        )

    async def download(
        self, object_name: str, bucket_name: str | None = None, **kwargs
    ) -> bytes:
        """從 Cloud Storage 下載檔案

        Args:
            object_name: 物件名稱（路徑）
            bucket_name: 儲存桶名稱，如未提供則使用預設儲存桶
            **kwargs: 其他下載參數

        Returns:
            檔案內容
        """
        self._ensure_initialized()

        bucket_name = bucket_name or self._default_bucket
        if not bucket_name:
            raise ValueError(
                "bucket_name is required or default_bucket must be configured"
            )

        return await self._driver.download(bucket_name, object_name, **kwargs)

    async def download_to_filename(
        self, object_name: str, filename: str, bucket_name: str | None = None, **kwargs
    ) -> None:
        """從 Cloud Storage 下載檔案到本地

        Args:
            object_name: 物件名稱（路徑）
            filename: 本地檔案路徑
            bucket_name: 儲存桶名稱，如未提供則使用預設儲存桶
            **kwargs: 其他下載參數
        """
        self._ensure_initialized()

        bucket_name = bucket_name or self._default_bucket
        if not bucket_name:
            raise ValueError(
                "bucket_name is required or default_bucket must be configured"
            )

        await self._driver.download_to_filename(
            bucket_name, object_name, filename, **kwargs
        )

    async def delete(
        self, object_name: str, bucket_name: str | None = None, **kwargs
    ) -> None:
        """刪除 Cloud Storage 中的檔案

        Args:
            object_name: 物件名稱（路徑）
            bucket_name: 儲存桶名稱，如未提供則使用預設儲存桶
            **kwargs: 其他刪除參數
        """
        self._ensure_initialized()

        bucket_name = bucket_name or self._default_bucket
        if not bucket_name:
            raise ValueError(
                "bucket_name is required or default_bucket must be configured"
            )

        await self._driver.delete(bucket_name, object_name, **kwargs)

    async def list_objects(
        self, bucket_name: str | None = None, prefix: str | None = None, **kwargs
    ) -> list[dict[str, object]]:
        """列出儲存桶中的物件

        Args:
            bucket_name: 儲存桶名稱，如未提供則使用預設儲存桶
            prefix: 物件名稱前綴過濾
            **kwargs: 其他列表參數

        Returns:
            物件資訊列表
        """
        self._ensure_initialized()

        bucket_name = bucket_name or self._default_bucket
        if not bucket_name:
            raise ValueError(
                "bucket_name is required or default_bucket must be configured"
            )

        bucket = self._driver.get_bucket(bucket_name)
        return await bucket.list_blobs(prefix=prefix, **kwargs)

    async def get_object_metadata(
        self, object_name: str, bucket_name: str | None = None, **kwargs
    ) -> dict[str, object]:
        """取得物件元資料

        Args:
            object_name: 物件名稱（路徑）
            bucket_name: 儲存桶名稱，如未提供則使用預設儲存桶
            **kwargs: 其他參數

        Returns:
            物件元資料
        """
        self._ensure_initialized()

        bucket_name = bucket_name or self._default_bucket
        if not bucket_name:
            raise ValueError(
                "bucket_name is required or default_bucket must be configured"
            )

        return await self._driver.get_metadata(bucket_name, object_name, **kwargs)

    async def copy(
        self,
        source_object_name: str,
        destination_object_name: str,
        source_bucket_name: str | None = None,
        destination_bucket_name: str | None = None,
        **kwargs,
    ) -> dict[str, object]:
        """複製物件

        Args:
            source_object_name: 來源物件名稱
            destination_object_name: 目標物件名稱
            source_bucket_name: 來源儲存桶名稱，如未提供則使用預設儲存桶
            destination_bucket_name: 目標儲存桶名稱，如未提供則使用預設儲存桶
            **kwargs: 其他複製參數

        Returns:
            複製結果
        """
        self._ensure_initialized()

        source_bucket_name = source_bucket_name or self._default_bucket
        destination_bucket_name = destination_bucket_name or self._default_bucket

        if not source_bucket_name or not destination_bucket_name:
            raise ValueError(
                "bucket names are required or default_bucket must be configured"
            )

        return await self._driver.copy(
            source_bucket_name,
            source_object_name,
            destination_bucket_name,
            new_name=destination_object_name,
            **kwargs,
        )

    # === 私有輔助方法 ===

    def _ensure_initialized(self) -> None:
        """確保驅動已初始化"""
        if not self._driver or not self._project:
            raise RuntimeError(
                "StorageDriver not initialized. Call initialize() first."
            )
