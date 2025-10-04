# -*- coding: utf-8 -*-
"""
認證模組

整合 API Key 認證和文件認證的完整解決方案。

模組結構：
- base: 基礎抽象類別
- service: 認證服務邏輯
- middleware: API Key 認證中間件
- docs_middleware: 文件認證中間件
- dependencies: FastAPI 依賴注入函數

使用範例：

```python
from app.middleware.auth import AuthMiddleware, DocsAuthMiddleware, RequireAuth
from fastapi import FastAPI

# 應用中間件
app = FastAPI()
app.add_middleware(AuthMiddleware, setting=setting)
app.add_middleware(DocsAuthMiddleware, setting=setting)

# 在路由中使用依賴
@app.get("/protected", dependencies=[RequireAuth])
async def protected_route():
    return {"message": "This is a protected route"}

# 或者作為參數使用
@app.get("/user")
async def get_user(_: str = RequireAuth):
    return {"user": "current user"}
```
"""

from .base import BaseAuthMiddleware, BaseAuthService
from .dependencies import AUTH_SERVICE, RequireAuth, api_key_security, verify_api_key
from .docs_middleware import DocsAuthMiddleware
from .middleware import AuthMiddleware
from .service import ApiKeyAuthService

__all__ = [
    # 基礎類別
    "BaseAuthService",
    "BaseAuthMiddleware",
    # 服務類別
    "ApiKeyAuthService",
    "AUTH_SERVICE",
    # 中間件
    "AuthMiddleware",
    "DocsAuthMiddleware",
    # 依賴注入
    "api_key_security",
    "verify_api_key",
    "RequireAuth",
]
