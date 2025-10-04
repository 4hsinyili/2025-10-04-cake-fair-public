# -*- coding: utf-8 -*-
"""
中間件模組

提供應用程式所需的各種中間件功能，包括日誌記錄、錯誤處理等。
注意：認證中間件已移至 app.middleware.auth 模組統一管理。
"""

from app.middleware.auth import AuthMiddleware, DocsAuthMiddleware
from app.middleware.driver import DriverContainerMiddleware
from app.middleware.log import LoggingMiddleware, setup_logging
from app.middleware.request import RequestContextMiddleware
from app.middleware.trace import TraceMiddleware

__all__ = [
    "AuthMiddleware",
    "DocsAuthMiddleware",
    "DriverContainerMiddleware",
    "LoggingMiddleware",
    "RequestContextMiddleware",
    "TraceMiddleware",
    "setup_logging",
]
