# -*- coding: utf-8 -*-
"""
統一日誌系統模組

整合結構化日誌記錄、請求日誌中間件和 Google Cloud 日誌功能
提供統一的日誌介面和配置管理
"""

# 核心日誌功能
import time
import traceback

from fastapi.logger import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.middleware.log.filter import GoogleCloudLogFilter, LocalLogFilter
from app.middleware.log.setup import (
    get_logger,
    get_on_cloud,
    setup_logger,
    setup_logging,
)


class BaseLoggingMiddleware(BaseHTTPMiddleware):
    """基礎日誌中介軟體抽象類別，提供通用的請求處理流程"""

    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.config = kwargs

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """主要調度方法，協調各個處理步驟"""
        start_time = time.perf_counter()

        try:
            # 請求前處理
            self._before_request(request)

            # 執行請求
            response = await call_next(request)

            # 請求後處理
            process_time = time.perf_counter() - start_time
            self._after_request(request, response, process_time)

            return response

        except Exception as ex:
            return self._handle_exception(request, ex)

    def _before_request(self, request: Request) -> None:
        """請求前處理鉤子方法"""
        pass

    def _after_request(
        self, request: Request, response: Response, process_time: float
    ) -> None:
        """請求後處理鉤子方法"""
        logger.info(
            f"Response: {response.status_code}, process Time: {process_time:.4f} seconds"
        )

    def _handle_exception(self, request: Request, exception: Exception) -> JSONResponse:
        """處理異常"""
        logger.error(f"Request failed: {exception}")
        logger.error(traceback.format_exc())

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(exception),
            },
        )


class LoggingMiddleware(BaseLoggingMiddleware):
    """標準日誌中介軟體實作"""

    def _before_request(self, request: Request) -> None:
        """請求前的額外處理邏輯"""
        super()._before_request(request)
        # 可以在這裡添加特定的請求前處理邏輯

    def _after_request(
        self, request: Request, response: Response, process_time: float
    ) -> None:
        """請求後的額外處理邏輯"""
        super()._after_request(request, response, process_time)
        # 可以在這裡添加特定的請求後處理邏輯


class DetailedLoggingMiddleware(BaseLoggingMiddleware):
    """詳細日誌中介軟體實作範例，展示如何擴展功能"""

    def _before_request(self, request: Request) -> None:
        """記錄詳細的請求資訊"""
        super()._before_request(request)
        logger.info(f"Request: {request.method} {request.url}")
        logger.debug(f"Headers: {dict(request.headers)}")

    def _after_request(
        self, request: Request, response: Response, process_time: float
    ) -> None:
        """記錄詳細的響應資訊"""
        super()._after_request(request, response, process_time)
        logger.debug(f"Response headers: {dict(response.headers)}")

    def _handle_exception(self, request: Request, exception: Exception) -> JSONResponse:
        """詳細的異常處理"""
        logger.error(
            f"Detailed request info - URL: {request.url}, Method: {request.method}"
        )
        return super()._handle_exception(request, exception)


__all__ = [
    # 基礎日誌設定
    "get_logger",
    "setup_logger",
    "setup_logging",
    "get_on_cloud",
    # 過濾器
    "GoogleCloudLogFilter",
    "LocalLogFilter",
    # 中間件 (原有)
    "BaseLoggingMiddleware",
    "LoggingMiddleware",
    "DetailedLoggingMiddleware",
]
