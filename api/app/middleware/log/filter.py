from logging import Filter as LoggingFilter
from logging import LogRecord

from fastapi.encoders import jsonable_encoder
from google.cloud.logging_v2.handlers import CloudLoggingFilter

from app.context import get_current_request, get_current_trace_info


class GoogleCloudLogFilter(CloudLoggingFilter):
    def _transform_msg_to_dict(self, record: LogRecord) -> dict:
        """將日誌消息轉換為字典格式。"""
        message = (
            record.getMessage() if hasattr(record, "getMessage") else str(record.msg)
        )
        if isinstance(message, str):
            message = {"message": message}
        record.msg = message
        return record

    def _add_req_headers_to_msg(self, record: LogRecord) -> None:
        """將請求標頭添加到日誌消息中。"""
        request = get_current_request()
        if request:
            record.msg["headers"] = jsonable_encoder(request.headers)
        return record

    def _add_domain_to_msg(self, record: LogRecord) -> None:
        """將網域信息添加到日誌消息中。"""
        domain = getattr(record, "domain", None)
        if domain:
            record.msg["domain"] = domain
        return record

    def _add_trace_info(self, record: LogRecord) -> None:
        """將 Trace 信息添加到日誌消息中。"""
        trace = get_current_trace_info()
        if trace:
            record.trace = trace.get("trace")
            record.span_id = trace.get("span_id")
        return record

    def transform_record(self, record: LogRecord) -> LogRecord:
        record = self._transform_msg_to_dict(record)
        for func_name in self.__class__.__dict__.keys():
            if func_name.startswith("_add_"):
                func = getattr(self, func_name)
                if callable(func):
                    record = func(record)
        record.args = ()
        return record

    def filter(self, record: LogRecord) -> bool:
        try:
            # 進行日誌過濾
            self.transform_record(record)
            # 調用父類方法
            super().filter(record)
            return True

        except Exception as e:
            # 避免 filter 出錯導致整個日誌系統崩潰
            print(f"Error in GoogleCloudLogFilter: {e}")
            # 如果出錯，讓日誌通過但不帶 trace 資訊
            record.args = ()
            return True


class LocalLogFilter(LoggingFilter):
    def filter(self, record: LogRecord) -> bool:
        domain = getattr(record, "domain", None)
        if domain:
            record.msg = domain + " - " + record.msg
        record.args = ()
        # 調用父類方法
        super().filter(record)

        return True
