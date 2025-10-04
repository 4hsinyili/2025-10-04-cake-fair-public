from pydantic_settings import BaseSettings


class Setting(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    GCP_BUCKET_NAME: str
    GCP_PROJECT: str = "cake-fair"
    ON_CLOUD: bool = False

setting = Setting()