# -*- coding: utf-8 -*-
"""
認證模組基礎類別

定義認證相關的基礎類別和抽象介面。
"""

import logging
from abc import ABC, abstractmethod

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.setting import Setting


class BaseAuthService(ABC):
    """認證服務基礎類別

    定義所有認證服務應該實作的介面。
    """

    def __init__(self, setting: Setting):
        self.setting = setting
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def validate(self, credentials: str) -> bool:
        """驗證認證資訊

        Args:
            credentials: 認證憑證

        Returns:
            bool: 驗證是否通過
        """
        pass


class BaseAuthMiddleware(BaseHTTPMiddleware, ABC):
    """認證中間件基礎類別

    定義所有認證中間件的通用行為。
    """

    def __init__(self, app: object, setting: Setting):
        super().__init__(app)
        self.setting = setting
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    async def dispatch(self, request: Request, call_next):
        """中間件主要邏輯

        Args:
            request: HTTP 請求物件
            call_next: 下一個中間件或路由處理器

        Returns:
            Response: HTTP 回應物件
        """
        pass

    def _log_auth_success(self, request: Request, additional_info: str = ""):
        """記錄認證成功日誌

        Args:
            request: HTTP 請求物件
            additional_info: 額外資訊
        """
        self.logger.info(
            f"Authentication successful - "
            f"Path: {request.url.path}, "
            f"Method: {request.method}, "
            f"Client IP: {request.client.host if request.client else 'unknown'}"
            f"{', ' + additional_info if additional_info else ''}"
        )

    def _log_auth_failure(
        self, request: Request, reason: str, additional_info: str = ""
    ):
        """記錄認證失敗日誌

        Args:
            request: HTTP 請求物件
            reason: 失敗原因
            additional_info: 額外資訊
        """
        self.logger.warning(
            f"Authentication failed - "
            f"Path: {request.url.path}, "
            f"Method: {request.method}, "
            f"Reason: {reason}, "
            f"Client IP: {request.client.host if request.client else 'unknown'}"
            f"{', ' + additional_info if additional_info else ''}"
        )


__all__ = [
    "BaseAuthService",
    "BaseAuthMiddleware",
]
