# -*- coding: utf-8 -*-
"""
FastAPI 依賴注入函數

提供用於 FastAPI 路由的認證依賴注入函數。
用於 OpenAPI 文件生成和路由層級的認證標示。
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.setting import setting

from .service import ApiKeyAuthService

# 創建全域認證服務實例
AUTH_SERVICE = ApiKeyAuthService(setting)

# 創建 HTTPBearer 安全方案
api_key_security = HTTPBearer(
    scheme_name="API Key",
    description="在 Authorization Header 中提供 API Key: Authorization: Bearer <your-api-key>",
    auto_error=False,  # 不自動拋出錯誤，讓中間件處理
)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(api_key_security),
) -> str:
    """驗證 API Key 的依賴函數

    這個函數主要用於 OpenAPI 文件生成和路由依賴注入。
    實際的認證邏輯由 AuthMiddleware 在中間件層統一處理。

    使用場景：
    - OpenAPI/Swagger 文件自動生成認證欄位
    - 路由明確標示需要認證
    - 提供型別提示和 IDE 支援

    注意：由於 AuthMiddleware 已在中間件層處理認證，
    這個函數在正常情況下不會真正執行驗證邏輯。

    Args:
        credentials: HTTP Bearer 憑證

    Returns:
        str: API Key

    Raises:
        HTTPException: 如果認證失敗
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not AUTH_SERVICE.validate_api_key(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )

    return credentials.credentials


# 簡化的依賴，用於需要認證的路由
# 使用方式：在路由函數中加入參數 `_: str = RequireAuth`
# 作用：
# 1. 告訴 OpenAPI/Swagger 此端點需要認證
# 2. 提供清楚的程式碼標示
# 3. 支援 IDE 自動完成和型別檢查
RequireAuth = Depends(verify_api_key)


__all__ = [
    "AUTH_SERVICE",
    "api_key_security",
    "verify_api_key",
    "RequireAuth",
]
