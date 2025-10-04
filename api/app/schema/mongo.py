from typing import Literal

from pydantic import Field
from pydantic.dataclasses import dataclass

from app.schema.db import Location


@dataclass(slots=True)
class ListStorePayload:
    location: tuple[float, float]  # (longitude, latitude)
    drink_tags: list[str] = Field(default_factory=list)
    brands: list[str] = Field(default_factory=list)
    review_count_range: tuple[int, int] | None = None  # (min, max)
    rating_range: tuple[float, float] | None = None  # (min,
    distance_range: tuple[int, int] | None = None  # (min, max) in meters
    platform: Literal["ubereats", "foodpanda"] | None = "ubereats"

@dataclass(slots=True)
class Company:
    alias: str
    name: str
    location: Location
    address: str


@dataclass(slots=True)
class Brand:
    name: str = Field(default="", description="品牌名稱")
    has_chain: bool = Field(default=False, description="是否為連鎖品牌")
    chain_count: int = Field(default=0, description="連鎖店數量", ge=0)