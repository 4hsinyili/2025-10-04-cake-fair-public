# -*- coding: utf-8 -*-
"""
API 文件認證中間件

提供 API 文件（Swagger UI、ReDoc、OpenAPI Schema）的 HTTP Basic 認證功能。
"""

import base64

from fastapi import Request
from fastapi.responses import JSONResponse

from app.setting import Setting

from .base import BaseAuthMiddleware


class DocsAuthMiddleware(BaseAuthMiddleware):
    """文件認證中間件

    為 API 文件相關端點提供 HTTP Basic 認證保護。
    保護的端點包括：/docs、/redoc、/openapi.json
    """

    def __init__(self, app: object, setting: Setting):
        super().__init__(app, setting)

        # 需要保護的文件路徑
        self.protected_paths = ["/docs", "/redoc", "/openapi.json"]

    async def dispatch(self, request: Request, call_next):
        """中間件主要邏輯

        Args:
            request: HTTP 請求物件
            call_next: 下一個中間件或路由處理器

        Returns:
            Response: HTTP 回應物件
        """
        # 檢查是否為需要保護的文件路徑
        if not self._is_docs_path(request.url.path):
            return await call_next(request)

        # 檢查文件認證是否啟用
        if not self.setting.DOCS_AUTH_ENABLED:
            return await call_next(request)

        # 檢查 Basic 認證
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            return self._create_auth_challenge_response()

        # 驗證認證資訊
        if not self._validate_basic_auth(auth_header):
            self._log_auth_failure(request, "Invalid credentials")
            return self._create_auth_challenge_response()

        # 記錄成功認證
        self._log_auth_success(request, f"User: {self.setting.DOCS_USERNAME}")

        return await call_next(request)

    def _is_docs_path(self, path: str) -> bool:
        """檢查路徑是否為文件路徑

        Args:
            path: 請求路徑

        Returns:
            bool: 是否為文件路徑
        """
        return path in self.protected_paths

    def _validate_basic_auth(self, auth_header: str) -> bool:
        """驗證 Basic 認證資訊

        Args:
            auth_header: Authorization header 值

        Returns:
            bool: 認證是否通過
        """
        try:
            # 提取 Base64 編碼的認證資訊
            encoded_credentials = auth_header[6:]  # 移除 "Basic " 前綴
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            username, password = decoded_credentials.split(":", 1)
            # 驗證使用者名稱和密碼
            return (
                username == self.setting.DOCS_USERNAME
                and password == self.setting.DOCS_PASSWORD
            )

        except (ValueError, UnicodeDecodeError) as e:
            self.logger.debug(f"Basic auth parsing error: {e}")
            return False

    def _create_auth_challenge_response(self) -> JSONResponse:
        """創建認證挑戰回應

        Returns:
            JSONResponse: 401 回應，要求進行 Basic 認證
        """
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"},
            headers={"WWW-Authenticate": 'Basic realm="API Documentation"'},
        )


__all__ = [
    "DocsAuthMiddleware",
]
