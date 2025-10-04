import logging
import os

import fastapi
import fastapi.logger
import google.cloud.logging_v2

from app.middleware.log.filter import GoogleCloudLogFilter, LocalLogFilter
from app.setting import setting

CLIENT = google.cloud.logging_v2.Client()


def disable_system_logging():
    for logger_name in [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "uvicorn.asgi",
        "jieba",
        "stderr",
    ]:
        logger_instance = logging.getLogger(logger_name)
        logger_instance.handlers = []  # Clear all handlers
        logger_instance.propagate = False  # Prevent propagation to root logger
        logger_instance.setLevel(logging.WARNING)  # Set to WARNING to reduce noise


def get_on_cloud() -> bool:
    return setting.ON_CLOUD if setting.ON_CLOUD is not None else os.getenv("ON_CLOUD") == "1"


def setup_logger(logger: logging.Logger, on_cloud: bool = None):
    logger_name = logger.name

    # 更徹底地清除現有設定
    for handler in logger.handlers[:]:  # 使用切片複製避免在迭代時修改列表
        logger.removeHandler(handler)
        handler.close()  # 確保 handler 被正確關閉

    # 確保 logger 不會繼承父級 logger 的 handlers
    logger.propagate = False

    if on_cloud:
        # 建立新的 handler
        handler = CLIENT.get_default_handler()
        handler.setLevel(logging.INFO)

        # 清除現有 filters 並添加我們的 filter
        handler.filters.clear()
        filter_instance = GoogleCloudLogFilter(project=CLIENT.project)
        handler.addFilter(filter_instance)

        # 檢查是否已經有相同的 handler，避免重複
        handler_exists = False
        for existing_handler in logger.handlers:
            if (
                hasattr(existing_handler, "transport")
                and hasattr(handler, "transport")
                and existing_handler.transport == handler.transport
            ):
                handler_exists = True
                break

        if not handler_exists:
            logger.addHandler(handler)

        logger.setLevel(logging.INFO)
        disable_system_logging()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        filter_instance = LocalLogFilter()
        handler.addFilter(filter_instance)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    logger.info(
        f"Logging setup complete for {logger_name} with filter: {filter_instance.__class__.__name__}"
    )
    return logger


def get_logger(name: str = None, on_cloud: bool = None):
    on_cloud = get_on_cloud() if on_cloud is None else on_cloud
    if name:
        logger = logging.getLogger(name)
    else:
        logger = fastapi.logger.logger
    return setup_logger(logger, on_cloud)


def setup_logging(
    loggers: list[logging.Logger] = None, names: list[str] = None, on_cloud: bool = None
):
    loggers = loggers or []
    for logger in loggers:
        setup_logger(logger, on_cloud)

    names = names or []
    for name in names:
        get_logger(name, on_cloud)
