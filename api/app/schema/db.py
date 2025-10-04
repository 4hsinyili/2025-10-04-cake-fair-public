import hashlib

from pydantic import Field, computed_field
from pydantic.dataclasses import dataclass


@dataclass(slots=True)
class Coordinates:
    latitude: float
    longitude: float


@dataclass(slots=True)
class Location:
    """MongoDB Point 格式的座標，按照 [經度, 緯度] 順序儲存"""

    coordinates: list[float]  # [longitude, latitude]
    type: str = "Point"


@dataclass(slots=True)
class Rating:
    value: float
    review_count: int


@dataclass(slots=True)
class OpeningHourEntry:
    opening_time: str
    closing_time: str


@dataclass(slots=True)
class OperatingHour:
    weekday: int
    service_type: str
    hours: list[OpeningHourEntry]


@dataclass(slots=True)
class MenuItem:
    id: str | int | None
    name: str
    description: str
    price: float
    image_url: str
    is_popular: bool


@dataclass(slots=True)
class MenuCategory:
    id: str | int | None
    name: str
    description: str
    items: list[MenuItem]


@dataclass(slots=True)
class Menu:
    categories: list[MenuCategory]


@dataclass(slots=True)
class DeliveryInfo:
    minimum_order: float
    delivery_fee: float


@dataclass(slots=True)
class CrossPlatformMatchDetails:
    brand_similarity: float
    name_similarity: float
    distance_score: float


@dataclass(slots=True)
class CrossPlatformMatch:
    has_match: bool
    match_platform: str
    match_store_id: str
    match_store_name: str
    match_confidence: str
    similarity_score: float
    distance_km: float
    match_details: CrossPlatformMatchDetails


@dataclass(slots=True)
class BrandDoc:
    brand_id: str = Field(default="", description="品牌的唯一識別碼")
    name: str = Field(default="", description="品牌名稱")
    normalized_name: str = Field(
        default="", description="正規化後的品牌名稱，用於搜索和比對"
    )
    has_chain: bool = Field(default=False, description="是否為連鎖品牌")
    chain_count: int = Field(default=0, description="連鎖店數量", ge=0)
    platforms: list[str] | None = Field(
        default=None, description="品牌所在的平台列表 (如 foodpanda, ubereats)"
    )
    cuisines: list[str] | None = Field(default=None, description="品牌提供的料理類型")
    regions: list[str] | None = Field(default=None, description="品牌服務的地區")
    rating: Rating | None = Field(default=None, description="品牌評分資訊")
    created_at: int = Field(default=0, description="建立時間戳記")
    updated_at: int | None = Field(default=None, description="最後更新時間戳記")

    @computed_field
    @property
    def _id(self) -> str:
        """使用 brand_id 和 normalized_name 組合來產生唯一的 _id"""
        source = f"{self.brand_id}_{self.normalized_name}"
        return hashlib.md5(source.encode()).hexdigest()


@dataclass(slots=True)
class MenuItemDoc:
    @dataclass
    class Category:
        id: str | int | None = Field(default=None, description="分類的唯一識別碼")
        name: str = Field(default="", description="分類名稱")
        description: str = Field(default="", description="分類描述")

    item_id: str | int = Field(description="菜單項目的唯一識別碼")
    store_id: str = Field(description="所屬店家的識別碼")
    platform: str = Field(description="所屬平台 (如 foodpanda, ubereats)")
    name: str = Field(description="菜單項目名稱")
    category: str = Field(description="菜單項目分類")
    normalized_name: str = Field(
        default="", description="正規化後的項目名稱，用於搜索和比對"
    )
    description: str = Field(default="", description="菜單項目詳細描述")
    price: float = Field(default=0.0, description="價格", ge=0)
    image_url: str = Field(default="", description="項目圖片網址")
    is_popular: bool = Field(default=False, description="是否為熱門項目")
    keywords: list[str] | None = Field(default=None, description="相關關鍵字")
    created_at: int = Field(default=0, description="建立時間戳記")
    updated_at: int | None = Field(default=None, description="最後更新時間戳記")

    @computed_field
    @property
    def _id(self) -> str:
        """使用 platform, store_id, item_id 和 name 組合來產生唯一的 _id"""
        source = f"{self.platform}_{self.store_id}_{self.item_id}_{self.name}"
        return hashlib.md5(source.encode()).hexdigest()


@dataclass(slots=True)
class StoreDoc:
    store_id: str = Field(description="店家的唯一識別碼")
    platform: str = Field(description="所屬平台 (如 foodpanda, ubereats)")
    name: str = Field(description="店家名稱")
    brand: str = Field(default="", description="所屬品牌名稱")
    brand_id: str = Field(default="", description="所屬品牌識別碼")
    normalized_name: str = Field(
        default="", description="正規化後的店家名稱，用於搜索和比對"
    )
    address: str = Field(default="", description="店家地址")
    location: Location | None = Field(
        default=None, description="店家座標（MongoDB Point 格式）"
    )
    rating: Rating | None = Field(default=None, description="店家評分資訊")
    cuisines: list[str] | None = Field(default=None, description="提供的料理類型")
    operating_hours: list[OperatingHour] | None = Field(
        default=None, description="營業時間"
    )
    phone: str = Field(default="", description="聯絡電話")
    delivery_info: DeliveryInfo | None = Field(default=None, description="外送資訊")
    source_url: str = Field(default="", description="原始資料來源網址")
    keywords: list[str] | None = Field(default=None, description="相關關鍵字")
    created_at: int = Field(default=0, description="建立時間戳記")
    updated_at: int | None = Field(default=None, description="最後更新時間戳記")

    @computed_field
    @property
    def _id(self) -> str:
        """使用 platform 和 store_id 組合來產生唯一的 _id"""
        source = f"{self.platform}_{self.store_id}"
        return hashlib.md5(source.encode()).hexdigest()


@dataclass(slots=True)
class DrinkTagDoc:
    name: str = Field(default="", description="飲品標籤名稱")
    count: int = Field(default=0, description="標籤出現次數", ge=0)

    @computed_field
    @property
    def _id(self) -> str:
        """使用 name 來產生唯一的 _id"""
        source = self.name
        return hashlib.md5(source.encode()).hexdigest()
