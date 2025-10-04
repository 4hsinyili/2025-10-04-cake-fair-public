# -*- coding: utf-8 -*-
"""
Cloud Trace 追蹤中間件

提供 Cloud Trace 追蹤功能，為每個請求設置追蹤上下文，
支援 Google Cloud Trace 格式和自動生成追蹤 ID。
"""

import nanoid
from fastapi.logger import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.context import (
    reset_current_trace_info,
    set_current_trace_info,
)
from app.setting import setting


class BaseTraceMiddleware(BaseHTTPMiddleware):
    """基礎追蹤中介軟體抽象類別，提供通用的追蹤處理流程"""

    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.config = kwargs

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """主要調度方法，協調各個處理步驟"""
        trace_token = None

        try:
            # 設置追蹤上下文
            trace_token = self._setup_trace_context(request)

            # 請求前處理
            self._before_request(request)

            # 執行請求
            response = await call_next(request)

            # 請求後處理
            self._after_request(request, response)

            return response

        except Exception as ex:
            return self._handle_exception(request, ex)
        finally:
            # 清理上下文
            self._cleanup_context(trace_token)

    def _setup_trace_context(self, request: Request) -> object | None:
        """設置追蹤上下文"""
        cloud_trace = request.headers.get("x-cloud-trace-context", "")

        trace_parts = cloud_trace.split("/")
        if len(trace_parts) >= 2:
            trace_info = {
                "trace": f"projects/{setting.basic.PROJECT}/traces/{trace_parts[0]}",
                "span_id": trace_parts[1].split(";")[0],
            }
        else:
            trace_id = nanoid.generate(
                size=16,
                alphabet="01234567DEFGHIJKLMNOPQRSTUVWXdefghijklmnopqrstuvwxyz",
            )
            span_id = nanoid.generate(size=19, alphabet="0123456789")

            trace_info = {
                "trace": f"projects/{setting.basic.PROJECT}/traces/{trace_id}",
                "span_id": span_id,
            }

        # 將追蹤資訊存入 request.state 供其他中間件使用
        request.state.trace_info = trace_info

        return set_current_trace_info(trace_info)

    def _before_request(self, request: Request) -> None:
        """請求前處理鉤子方法"""
        pass

    def _after_request(self, request: Request, response: Response) -> None:
        """請求後處理鉤子方法"""
        # 將追蹤資訊加入響應標頭
        trace_info = getattr(request.state, "trace_info", {})
        if "trace" in trace_info and "span_id" in trace_info:
            response.headers["x-cloud-trace-context"] = (
                f"{trace_info['trace'].split('/')[-1]}/{trace_info['span_id']}"
            )

    def _handle_exception(self, request: Request, exception: Exception) -> Response:
        """處理異常"""
        logger.error(f"Trace middleware exception: {exception}")
        # 繼續拋出異常讓其他中間件處理
        raise exception

    def _cleanup_context(self, trace_token: object | None) -> None:
        """清理上下文"""
        if trace_token:
            try:
                reset_current_trace_info(trace_token)
            except Exception as e:
                # 避免清理 context 時的錯誤影響主要流程
                logger.warning(f"Error resetting trace_context: {e}")


class TraceMiddleware(BaseTraceMiddleware):
    """標準追蹤中介軟體實作"""

    def _before_request(self, request: Request) -> None:
        """請求前的額外處理邏輯"""
        super()._before_request(request)
        # 可以在這裡添加特定的追蹤前處理邏輯

    def _after_request(self, request: Request, response: Response) -> None:
        """請求後的額外處理邏輯"""
        super()._after_request(request, response)
        # 可以在這裡添加特定的追蹤後處理邏輯


class DetailedTraceMiddleware(BaseTraceMiddleware):
    """詳細追蹤中介軟體實作，記錄更多追蹤資訊"""

    def _before_request(self, request: Request) -> None:
        """記錄詳細的追蹤資訊"""
        super()._before_request(request)
        trace_info = getattr(request.state, "trace_info", {})
        logger.debug(
            f"Trace setup - Trace ID: {trace_info.get('trace', 'N/A')}, Span ID: {trace_info.get('span_id', 'N/A')}"
        )

    def _after_request(self, request: Request, response: Response) -> None:
        """記錄追蹤完成資訊"""
        super()._after_request(request, response)
        trace_info = getattr(request.state, "trace_info", {})
        logger.debug(f"Trace completed for {trace_info.get('trace', 'N/A')}")


# 為了保持向後相容性，保留這些函式但它們將直接使用 app.context 中的實作
# 在後續版本中可以考慮移除這些包裝函式
def get_current_trace_info() -> dict | None:
    """取得目前的追蹤上下文"""
    from app.context import get_current_trace_info as _get_current_trace_info

    return _get_current_trace_info()


def get_trace_id() -> str | None:
    """取得目前的追蹤 ID"""
    from app.context import get_trace_id as _get_trace_id

    return _get_trace_id()


def get_span_id() -> str | None:
    """取得目前的 Span ID"""
    from app.context import get_span_id as _get_span_id

    return _get_span_id()
