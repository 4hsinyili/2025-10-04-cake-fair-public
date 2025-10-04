# middleware.py
from typing import TypeVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.context import reset_current_request, set_current_request

# 定義泛型類型變數
RequestType = TypeVar("RequestType", bound=Request)


class DebugMixin:
    """除錯功能混入類。"""

    @property
    def is_debugging(self) -> bool:
        """檢查當前請求是否處於除錯模式。

        透過檢查請求的查詢參數 (query params) 中是否包含 'debug' 參數，
        且其值為 'true', '1', 'yes', 'on' (不分大小寫) 來判斷。

        Returns:
            bool: 如果處於除錯模式則回傳 True，否則回傳 False。
        """
        if not hasattr(self, "query_params"):
            return False

        debug_value = self.query_params.get("debug", "")  # type: ignore
        return debug_value.lower() in {"true", "1", "yes", "on"}


class EnhancedRequest(Request, DebugMixin):
    """增強的 Request 類，包含除錯功能。"""

    pass


class RequestContextMiddleware(BaseHTTPMiddleware):
    """請求上下文中介軟體。

    為每個請求設置上下文變數，並提供增強功能。
    """

    async def dispatch(self, request: Request, call_next):
        # 創建增強的請求物件
        enhanced_request = EnhancedRequest(scope=request.scope, receive=request.receive)

        # 設置請求上下文
        request_token = set_current_request(enhanced_request)

        try:
            response = await call_next(request)
        finally:
            reset_current_request(request_token)
        return response


# 便利函式
def get_current_request():
    """獲取當前請求實例

    Returns:
        當前的 EnhancedRequest 實例，如果未設定則返回 None
    """
    from app.context import get_current_request as _get_current_request

    return _get_current_request()
