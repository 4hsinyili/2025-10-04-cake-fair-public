import logging
from logging import LogRecord

import google.cloud.logging_v2
from app.setting import setting
from google.cloud.logging_v2.handlers import CloudLoggingFilter
from streamlit import st
from streamlit.runtime.scriptrunner import get_script_run_ctx


class GoogleCloudLogFilter(CloudLoggingFilter):
    def filter(self, record: LogRecord) -> bool:
        original_message = (
            record.getMessage() if hasattr(record, "getMessage") else str(record.msg)
        )
        context = get_script_run_ctx()
        session_id = context.session_id
        user_email = context.user_info.get("email", "Unknown")
        record.trace = session_id
        record.span_id = session_id
        client_info = {"client": {"email": user_email, "session_id": session_id}}
        if not (hasattr(record, "msg") and isinstance(record.msg, dict)):
            # 轉換為字典格式
            record.msg = {
                "message": original_message,
            }
        record.msg.update(client_info)
        record.args = ()
        super().filter(record)

        return True


def create_logger(on_cloud: bool = False):
    logger = logging.getLogger()
    logger.handlers = []  # Clear existing handlers to avoid duplicates
    if on_cloud:
        print("Running in cloud environment, setting up Google Cloud logging")
        client = google.cloud.logging_v2.Client()
        handler = client.get_default_handler()
        handler.setLevel(logging.INFO)
        handler.filters = []
        filter = GoogleCloudLogFilter(project=client.project)
        handler.addFilter(filter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    else:
        print("Running in local environment, setting up local logging")
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    logger.info("Logging setup complete")
    return logger

@st.cache_resource
def get_cached_logger():
    on_cloud = setting.ON_CLOUD
    logger = create_logger(on_cloud=on_cloud)
    return logger