from pydantic import Field
from pydantic_settings import BaseSettings


class Setting(BaseSettings):
    SERVICE_NAME: str = "drink-recommendation"
    API_CONTAINER_NAME: str = "api"
    AGENT_CONTAINER_NAME: str = "agent"
    CLIENT_CONTAINER_NAME: str = "client"
    API_PORT: int = 3001
    AGENT_PORT: int = 3002
    CLIENT_PORT: int = 8080
    SHORT_SHA: str = "latest"
    BRANCH_NAME: str = "main"
    PROJECT: str = Field(..., alias="PROJECT_ID")
    LOCATION: str = "asia-east1"
    DEPLOY_TIMEOUT: int = 300  # in seconds
    STAGE: str = "dev"