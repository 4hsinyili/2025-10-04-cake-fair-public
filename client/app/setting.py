from pydantic_settings import BaseSettings


class Setting(BaseSettings):
    ON_CLOUD: bool = False

setting = Setting()