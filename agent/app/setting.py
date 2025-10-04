from pydantic import Field
from pydantic_settings import BaseSettings


class Setting(BaseSettings):
    class OpenRouterSettings(BaseSettings):
        API_KEY: str = Field(..., alias="OPENROUTER_API_KEY")
        API_BASE: str = Field(
            "https://openrouter.ai/api/v1", alias="OPENROUTER_API_BASE"
        )

    openrouter: OpenRouterSettings = OpenRouterSettings()


setting = Setting()
