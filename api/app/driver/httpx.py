"""HTTPX 驅動實作

提供 HTTPX 異步客戶端的初始化、清理和健康檢查功能。
支援代理、SSL 驗證和各種 HTTP 配置選項。
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx
else:
    try:
        import httpx
    except ImportError:
        httpx = None

from app.driver.base import Driver


class HttpxDriver(Driver["httpx.AsyncClient"]):
    """HTTPX 驅動實作

    管理 HTTPX AsyncClient 的生命週期，包括連線池配置、
    代理設定、SSL 驗證和自訂標頭。
    """

    def __init__(self):
        self._logger = logging.getLogger(__name__)

    async def initialize(self, config: dict[str, object]) -> "httpx.AsyncClient":
        """初始化 HTTPX 客戶端

        Args:
            config: HTTPX 配置字典，支援以下選項：
                - timeout: 超時時間，預設為 240.0 秒
                - max_keepalive: 最大保持連線數，預設為 20
                - max_connections: 最大連線數，預設為 100
                - retry: 重試次數，預設為 3

        Returns:
            初始化後的 HTTPX AsyncClient

        Raises:
            ImportError: 當 httpx 套件未安裝時
            Exception: 當初始化失敗時
        """
        if httpx is None:
            raise ImportError("httpx package is required for HttpxDriver")

        # 基本配置
        client_config = {
            "timeout": httpx.Timeout(timeout=config.get("timeout", 240.0)),
            "limits": httpx.Limits(
                max_keepalive_connections=config.get("max_keepalive", 20),
                max_connections=config.get("max_connections", 100),
                keepalive_expiry=config.get("keepalive_expiry", 5.0),
            ),
            "transport": httpx.AsyncHTTPTransport(retries=config.get("retry", 3)),
        }

        try:
            self._logger.info("Initializing HTTPX client")
            client = httpx.AsyncClient(**client_config)

            self._logger.info("HTTPX client initialized successfully")
            return client

        except Exception as e:
            self._logger.error(f"Failed to initialize HTTPX client: {e}")
            raise

    async def cleanup(self, instance: "httpx.AsyncClient") -> None:
        """清理 HTTPX 客戶端

        Args:
            instance: 要清理的 HTTPX AsyncClient 實例
        """
        try:
            await instance.aclose()
            self._logger.info("HTTPX client closed successfully")
        except Exception as e:
            self._logger.error(f"Error closing HTTPX client: {e}")

    async def health_check(self, instance: "httpx.AsyncClient") -> bool:
        """HTTPX 健康檢查

        執行簡單的 HTTP 請求檢查客戶端狀態。

        Args:
            instance: 要檢查的 HTTPX AsyncClient 實例

        Returns:
            True 表示健康，False 表示不健康
        """
        try:
            # 使用 httpbin.org 進行簡單的連線測試
            test_urls = [
                "https://httpbin.org/status/200",
                "https://www.google.com/",
                "https://httpstat.us/200",
            ]

            for url in test_urls:
                try:
                    response = await instance.get(url, timeout=5)
                    if response.status_code == 200:
                        self._logger.debug(f"HTTPX health check successful with {url}")
                        return True
                except Exception as e:
                    self._logger.debug(f"HTTPX health check failed for {url}: {e}")
                    continue

            self._logger.warning("HTTPX health check failed for all test URLs")
            return False

        except Exception as e:
            self._logger.error(f"HTTPX health check failed: {e}")
            return False
