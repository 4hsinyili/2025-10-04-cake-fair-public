"""應用程式上下文管理

此模組提供全域上下文管理功能，用於在請求處理過程中
共享應用程式狀態和資源實例。
"""

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.driver import DriverContainer
    from app.middleware.request import EnhancedRequest

# DriverContainer 上下文變數
_current_driver_container: ContextVar["DriverContainer | None"] = ContextVar(
    "_current_driver_container", default=None
)

# 請求上下文變數
_request_context: ContextVar["EnhancedRequest | None"] = ContextVar(
    "_request_context", default=None
)

# Trace 上下文變數
_trace_context: ContextVar[dict | None] = ContextVar("_trace_context", default=None)


# ============= DriverContainer 相關函式 =============


def set_current_driver_container(container: "DriverContainer") -> None:
    """設定當前的 DriverContainer（通常在請求開始時呼叫）

    Args:
        container: 要設定的 DriverContainer 實例
    """
    _current_driver_container.set(container)


def get_current_driver_container() -> "DriverContainer":
    """獲取當前的 DriverContainer

    Returns:
        當前的 DriverContainer 實例

    Raises:
        RuntimeError: 當 DriverContainer 未設定時
    """
    container = _current_driver_container.get()
    if container is None:
        raise RuntimeError("DriverContainer not found in current context")
    return container


def clear_current_driver_container() -> None:
    """清除當前的 DriverContainer（用於測試或特殊情況）"""
    _current_driver_container.set(None)


# ============= Request 相關函式 =============


def set_current_request(request: "EnhancedRequest") -> object:
    """設定當前的請求上下文

    Args:
        request: 要設定的 EnhancedRequest 實例

    Returns:
        上下文 token，用於後續重置
    """
    return _request_context.set(request)


def get_current_request() -> "EnhancedRequest | None":
    """獲取當前的請求上下文

    Returns:
        當前的 EnhancedRequest 實例，如果未設定則返回 None
    """
    return _request_context.get()


def reset_current_request(token: object) -> None:
    """重置請求上下文

    Args:
        token: 由 set_current_request 返回的 token
    """
    _request_context.reset(token)


# ============= Trace 相關函式 =============


def set_current_trace_info(trace_info: dict) -> object:
    """設定當前的追蹤上下文

    Args:
        trace_info: 追蹤資訊字典

    Returns:
        上下文 token，用於後續重置
    """
    return _trace_context.set(trace_info)


def get_current_trace_info() -> dict | None:
    """獲取當前的追蹤上下文

    Returns:
        當前的追蹤資訊字典，如果未設定則返回 None
    """
    return _trace_context.get()


def get_trace_id() -> str | None:
    """獲取當前的追蹤 ID

    Returns:
        當前的追蹤 ID，如果未設定則返回 None
    """
    trace_info = _trace_context.get()
    if trace_info and "trace" in trace_info:
        return trace_info["trace"].split("/")[-1]
    return None


def get_span_id() -> str | None:
    """獲取當前的 Span ID

    Returns:
        當前的 Span ID，如果未設定則返回 None
    """
    trace_info = _trace_context.get()
    if trace_info and "span_id" in trace_info:
        return trace_info["span_id"]
    return None


def reset_current_trace_info(token: object) -> None:
    """重置追蹤上下文

    Args:
        token: 由 set_current_trace_info 返回的 token
    """
    try:
        _trace_context.reset(token)
    except Exception:
        # 避免清理 context 時的錯誤影響主要流程
        pass


__all__ = [
    # DriverContainer 相關
    "set_current_driver_container",
    "get_current_driver_container",
    "clear_current_driver_container",
    # Request 相關
    "set_current_request",
    "get_current_request",
    "reset_current_request",
    # Trace 相關
    "set_current_trace_info",
    "get_current_trace_info",
    "get_trace_id",
    "get_span_id",
    "reset_current_trace_info",
]
