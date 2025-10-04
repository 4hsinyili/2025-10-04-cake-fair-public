"""DriverContainer 中介軟體

為每個請求設定 DriverContainer 上下文，讓便利函式能夠正常工作。
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.context import set_current_driver_container


class DriverContainerMiddleware(BaseHTTPMiddleware):
    """DriverContainer 上下文中介軟體

    為每個請求設定 DriverContainer 上下文，使得在請求處理過程中
    能夠透過便利函式（如 get_es_driver()）獲取各種驅動實例。
    """

    async def dispatch(self, request: Request, call_next):
        """處理請求並設定 DriverContainer 上下文

        Args:
            request: HTTP 請求物件
            call_next: 下一個中介軟體或路由處理器

        Returns:
            HTTP 回應物件
        """
        # 設定 DriverContainer 上下文
        if hasattr(request.app.state, "driver_container"):
            set_current_driver_container(request.app.state.driver_container)

        # 繼續處理請求
        response = await call_next(request)

        # ContextVar 會自動在請求結束時重置，無需手動清理
        return response
