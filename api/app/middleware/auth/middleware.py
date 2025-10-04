# -*- coding: utf-8 -*-
"""
API Key 認證中間件

攔截所有請求並驗證 API Key。豁免指定的路由（如 health check、API 文件等）。
這是實際執行認證邏輯的地方，提供統一的認證處理、錯誤回應和日誌記錄。
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.setting import Setting

from .base import BaseAuthMiddleware
from .service import ApiKeyAuthService


class AuthMiddleware(BaseAuthMiddleware):
    """API Key 認證中間件

    攔截所有請求並驗證 API Key。豁免指定的路由（如 health check、API 文件等）。
    這是實際執行認證邏輯的地方，提供統一的認證處理、錯誤回應和日誌記錄。
    """

    def __init__(self, app: object, setting: Setting):
        super().__init__(app, setting)
        self.auth_service = ApiKeyAuthService(setting)

    async def dispatch(self, request: Request, call_next):
        """中間件主要邏輯

        Args:
            request: HTTP 請求物件
            call_next: 下一個中間件或路由處理器

        Returns:
            Response: HTTP 回應物件
        """
        # 檢查豁免路由
        if self._is_exempt_path(request.url.path):
            return await call_next(request)

        # 檢查認證是否啟用
        if not self.setting.AUTH_ENABLED:
            return await call_next(request)

        # 提取 API Key
        api_key = self._extract_api_key(request)
        if not api_key:
            self._log_auth_failure(request, "Missing API Key")
            return self._create_error_response(401, "Missing API Key")

        # 驗證 API Key
        if not self.auth_service.validate_api_key(api_key):
            self._log_auth_failure(
                request,
                "Invalid API Key",
                f"API Key: {self.auth_service.mask_api_key(api_key)}",
            )
            return self._create_error_response(403, "Invalid API Key")

        # 記錄成功認證
        self._log_auth_success(
            request, f"API Key: {self.auth_service.mask_api_key(api_key)}"
        )

        # 設定認證上下文
        request.state.authenticated = True
        request.state.api_key = self.auth_service.mask_api_key(api_key)

        return await call_next(request)

    def _is_exempt_path(self, path: str) -> bool:
        """檢查路徑是否為豁免路由

        Args:
            path: 請求路徑

        Returns:
            bool: 是否為豁免路由
        """
        return any(path.startswith(exempt) for exempt in self.setting.AUTH_EXEMPT_PATHS)

    def _extract_api_key(self, request: Request) -> str | None:
        """從請求中提取 API Key

        Args:
            request: HTTP 請求物件

        Returns:
            str | None: 提取到的 API Key，如果沒有則返回 None
        """
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # 移除 "Bearer " 前綴
        return None

    def _create_error_response(self, status_code: int, message: str) -> JSONResponse:
        """創建錯誤回應

        Args:
            status_code: HTTP 狀態碼
            message: 錯誤訊息

        Returns:
            JSONResponse: JSON 錯誤回應
        """
        return JSONResponse(status_code=status_code, content={"detail": message})


__all__ = [
    "AuthMiddleware",
]
