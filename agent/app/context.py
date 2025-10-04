"""應用程式上下文管理

此模組提供全域上下文管理功能，用於在請求處理過程中
共享應用程式狀態和資源實例。
"""

from contextvars import ContextVar

from fastapi import Request

# 請求上下文變數
_request_context: ContextVar["Request | None"] = ContextVar(
    "_request_context", default=None
)


def set_current_request(request: "Request") -> object:
    """設定當前的請求上下文

    Args:
        request: 要設定的 Request 實例

    Returns:
        上下文 token，用於後續重置
    """
    return _request_context.set(request)


def get_current_request() -> "Request | None":
    """獲取當前的請求上下文

    Returns:
        當前的 Request 實例，如果未設定則返回 None
    """
    return _request_context.get()


def reset_current_request(token: object) -> None:
    """重置請求上下文

    Args:
        token: 由 set_current_request 返回的 token
    """
    _request_context.reset(token)

__all__ = [
    "set_current_request",
    "get_current_request",
    "reset_current_request",
]
