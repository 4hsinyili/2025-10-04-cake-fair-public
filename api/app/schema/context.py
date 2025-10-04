import hashlib

from pydantic import Field, computed_field
from pydantic.dataclasses import dataclass


@dataclass(slots=True)
class SessionData:
    location: tuple[float, float] | None = None  # (longitude, latitude)
    drink_preference: object | None = None
    response_preference: object | None = None
    drink_preference_chat: list[dict] = Field(default_factory=list)
    response_preference_chat: list[dict] = Field(default_factory=list)
    openai_model: str = "x-ai/grok-4-fast:free"
    meta_data: dict = Field(default_factory=dict)

@dataclass(slots=True)
class StreamlitSession:
    session_id: str
    email: str | None = None

    @computed_field
    @property
    def session_hash(self) -> str:
        """計算 session_id 的 SHA-256 雜湊值"""
        return hashlib.sha256(self.session_id.encode()).hexdigest()