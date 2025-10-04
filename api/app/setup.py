from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.logger import logger
from starlette.middleware import Middleware

from app.driver import (
    DriverConfig,
    DriverContainer,
)
from app.middleware import (
    DriverContainerMiddleware,
    LoggingMiddleware,
    RequestContextMiddleware,
)
from app.middleware.log import setup_logging
from app.setting import setting


@asynccontextmanager
async def lifespan(app: FastAPI):
    driver_config = DriverConfig(
        httpx={
            "timeout": 240,
            "max_connections": 80,
            "max_keepalive_connections": 80,
        },
        storage={
            "project": setting.GCP_PROJECT,
        },
        mongo={
            "connection_string": f"mongodb+srv://{setting.DB_USER}:{setting.DB_PASSWORD}@{setting.DB_NAME}.{setting.DB_HOST}",
            "database": setting.DB_NAME,
        },
    )
    driver_container = DriverContainer(driver_config, app.state)
    setup_logging(
        on_cloud=setting.ON_CLOUD,
        loggers=[logger],
    )
    app.state.driver_container = driver_container
    yield
    await driver_container.cleanup_all()


def setup_app_kwargs():
    return {
        "lifespan": lifespan,
        "middleware": [
            Middleware(RequestContextMiddleware),
            Middleware(DriverContainerMiddleware),
            Middleware(LoggingMiddleware),
        ],
    }


def setup_app():
    app = FastAPI(**setup_app_kwargs())
    return app


__all__ = [
    "setup_app",
]
