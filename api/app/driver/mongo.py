"""MongoDB 驅動實作

提供 MongoDB 非同步客戶端的初始化、清理和健康檢查功能。
支援資料庫 CRUD 操作、地理空間查詢和復雜聚合管線。
基於 pymongo 的非同步 API 實作。
"""

import time
from typing import TYPE_CHECKING

from app.middleware.log import get_logger

if TYPE_CHECKING:
    from pymongo.asynchronous.collection import AsyncCollection
    from pymongo.asynchronous.database import AsyncDatabase
    from pymongo.asynchronous.mongo_client import AsyncMongoClient
else:
    try:
        from pymongo.asynchronous.collection import AsyncCollection
        from pymongo.asynchronous.database import AsyncDatabase
        from pymongo.asynchronous.mongo_client import AsyncMongoClient
    except ImportError:
        AsyncMongoClient = None
        AsyncDatabase = None
        AsyncCollection = None

from pymongo.server_api import ServerApi

from app.driver.base import Driver


class MongoDriver(Driver["AsyncMongoClient"]):
    """MongoDB 驅動實作

    管理 MongoDB 非同步客戶端的生命週期，
    支援基礎 CRUD 操作、地理空間查詢和復雜聚合管線。
    """

    def __init__(self):
        self._logger = get_logger(__name__)
        self._driver: AsyncMongoClient | None = None
        self._database_name: str | None = None
        self._connection_string: str | None = None

    async def initialize(self, config: dict[str, object]) -> "AsyncMongoClient":
        """初始化 MongoDB 客戶端

        Args:
            config: MongoDB 配置字典，支援以下選項：
                - host: MongoDB 主機位址（可選，預設 localhost）
                - port: MongoDB 端口（可選，預設 27017）
                - username: 使用者名稱（可選）
                - password: 密碼（可選）
                - database: 資料庫名稱（必要）
                - connection_string: 完整連接字串（可選，優先於其他選項）
                - server_api: 伺服器 API 版本（可選，預設 "1"）
                - connect_timeout_ms: 連接超時（可選，預設 120000）
                - socket_timeout_ms: Socket 超時（可選，預設 120000）

        Returns:
            初始化後的 MongoDB 客戶端
        """
        self._validate_dependencies()
        self._extract_config(config)

        try:
            client = await self._create_driver(config)
            await self._test_connection(client)
            self._logger.info("MongoDB 客戶端初始化成功")
            return client

        except Exception as e:
            self._logger.error(f"MongoDB 初始化失敗: {e}")
            raise

    def _validate_dependencies(self) -> None:
        """驗證必要的依賴套件"""
        if AsyncMongoClient is None:
            raise ImportError("pymongo 套件未安裝。請執行: pip install pymongo[async]")

    def _extract_config(self, config: dict[str, object]) -> None:
        """提取並驗證配置參數"""
        database_name = config.get("database")
        connection_string = config.get("connection_string")

        # 如果沒有完整連接字串，檢查必要參數
        if not connection_string and not database_name:
            raise ValueError("必須提供 database 或 connection_string")

        self._database_name = str(database_name) if database_name else None
        self._connection_string = str(connection_string) if connection_string else None

        self._logger.info(f"初始化 MongoDB 客戶端: {self._database_name}")

    async def _create_driver(self, config: dict[str, object]) -> "AsyncMongoClient":
        """建立 MongoDB 客戶端"""
        # 建立連接字串
        if self._connection_string:
            uri = self._connection_string
        else:
            uri = self._build_connection_string(config)

        # 客戶端選項
        client_options = {
            "server_api": ServerApi(str(config.get("server_api", "1"))),
            "connectTimeoutMS": int(config.get("connect_timeout_ms", 120000)),
            "socketTimeoutMS": int(config.get("socket_timeout_ms", 120000)),
        }

        client = AsyncMongoClient(uri, **client_options)
        self._driver = client
        return client

    def _build_connection_string(self, config: dict[str, object]) -> str:
        """建立 MongoDB 連接字串"""
        host = config.get("host", "localhost")
        port = config.get("port", 27017)
        username = config.get("username")
        password = config.get("password")

        if username and password:
            # MongoDB Atlas 或需要認證的連接
            if "mongodb.net" in str(host):
                return f"mongodb+srv://{username}:{password}@{host}"
            else:
                return f"mongodb://{username}:{password}@{host}:{port}"
        else:
            return f"mongodb://{host}:{port}"

    async def _test_connection(self, client: "AsyncMongoClient") -> None:
        """測試客戶端連線"""
        try:
            # 執行 ping 命令測試連接
            await client.admin.command("ping")
            self._logger.info("MongoDB 連接測試成功")
        except Exception as e:
            self._logger.error(f"MongoDB 連接測試失敗: {e}")
            raise

    async def cleanup(self, instance: "AsyncMongoClient") -> None:
        """清理 MongoDB 客戶端"""
        try:
            if instance:
                await instance.close()
                self._logger.info("MongoDB 客戶端已關閉")

        except Exception as e:
            self._logger.error(f"清理 MongoDB 客戶端時發生錯誤: {e}")
        finally:
            self._reset_state()

    def _reset_state(self) -> None:
        """重置內部狀態"""
        self._driver = None
        self._database_name = None
        self._connection_string = None

    async def health_check(self, instance: "AsyncMongoClient") -> bool:
        """MongoDB 健康檢查"""
        if not self._is_initialized():
            self._logger.warning("MongoDB 驅動尚未初始化")
            return False

        return await self._perform_health_check(instance)

    def _is_initialized(self) -> bool:
        """檢查驅動是否已正確初始化"""
        return self._driver is not None and (
            self._database_name is not None or self._connection_string is not None
        )

    async def _perform_health_check(self, instance: "AsyncMongoClient") -> bool:
        """執行實際的健康檢查"""
        try:
            # 執行簡單的 ping 命令
            await instance.admin.command("ping")
            self._logger.debug("MongoDB 健康檢查通過")
            return True

        except Exception as e:
            self._logger.error(f"MongoDB 健康檢查失敗: {e}")
            return False

    # === 公開 API 方法 ===

    def get_database(self, database_name: str | None = None) -> "AsyncDatabase":
        """取得資料庫物件

        Args:
            database_name: 資料庫名稱，如未提供則使用預設資料庫

        Returns:
            資料庫物件
        """
        self._ensure_initialized()

        database_name = database_name or self._database_name
        if not database_name:
            raise ValueError("必須提供 database_name 或在初始化時設定預設資料庫名稱")

        return self._driver[database_name]

    def get_collection(
        self, collection_name: str, database_name: str | None = None
    ) -> "AsyncCollection":
        """取得集合物件

        Args:
            collection_name: 集合名稱
            database_name: 資料庫名稱，如未提供則使用預設資料庫

        Returns:
            集合物件
        """
        database = self.get_database(database_name)
        return database[collection_name]

    # === 基礎 CRUD 操作 ===

    async def insert_one(
        self,
        collection_name: str,
        document: dict[str, object],
        database_name: str | None = None,
    ) -> str:
        """插入單一文件

        Args:
            collection_name: 集合名稱
            document: 要插入的文件
            database_name: 資料庫名稱

        Returns:
            插入文件的 ID
        """
        collection = self.get_collection(collection_name, database_name)
        result = await collection.insert_one(document)
        return str(result.inserted_id)

    async def insert_many(
        self,
        collection_name: str,
        documents: list[dict[str, object]],
        database_name: str | None = None,
    ) -> list[str]:
        """插入多個文件

        Args:
            collection_name: 集合名稱
            documents: 要插入的文件列表
            database_name: 資料庫名稱

        Returns:
            插入文件的 ID 列表
        """
        collection = self.get_collection(collection_name, database_name)
        result = await collection.insert_many(documents)
        return [str(id_) for id_ in result.inserted_ids]

    async def find_one(
        self,
        collection_name: str,
        filter_: dict[str, object] | None = None,
        database_name: str | None = None,
        **kwargs,
    ) -> dict[str, object] | None:
        """查找單一文件

        Args:
            collection_name: 集合名稱
            filter_: 查詢條件
            database_name: 資料庫名稱
            **kwargs: 其他查詢參數

        Returns:
            找到的文件，如未找到則返回 None
        """
        collection = self.get_collection(collection_name, database_name)
        return await collection.find_one(filter_ or {}, **kwargs)

    async def find(
        self,
        collection_name: str,
        filter_: dict[str, object] | None = None,
        database_name: str | None = None,
        limit: int | None = None,
        skip: int = 0,
        sort: list[tuple[str, int]] | None = None,
        **kwargs,
    ) -> list[dict[str, object]]:
        """查找多個文件

        Args:
            collection_name: 集合名稱
            filter_: 查詢條件
            database_name: 資料庫名稱
            limit: 限制結果數量
            skip: 跳過文件數量
            sort: 排序條件
            **kwargs: 其他查詢參數

        Returns:
            找到的文件列表
        """
        collection = self.get_collection(collection_name, database_name)
        cursor = collection.find(filter_ or {}, **kwargs)

        if skip > 0:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        if sort:
            cursor = cursor.sort(sort)

        return await cursor.to_list(length=None)

    async def update_one(
        self,
        collection_name: str,
        filter_: dict[str, object],
        update: dict[str, object],
        database_name: str | None = None,
        upsert: bool = False,
        **kwargs,
    ) -> int:
        """更新單一文件

        Args:
            collection_name: 集合名稱
            filter_: 查詢條件
            update: 更新內容
            database_name: 資料庫名稱
            upsert: 是否在文件不存在時插入
            **kwargs: 其他更新參數

        Returns:
            修改的文件數量
        """
        collection = self.get_collection(collection_name, database_name)
        result = await collection.update_one(filter_, update, upsert=upsert, **kwargs)
        return result.modified_count

    async def update_many(
        self,
        collection_name: str,
        filter_: dict[str, object],
        update: dict[str, object],
        database_name: str | None = None,
        upsert: bool = False,
        **kwargs,
    ) -> int:
        """更新多個文件

        Args:
            collection_name: 集合名稱
            filter_: 查詢條件
            update: 更新內容
            database_name: 資料庫名稱
            upsert: 是否在文件不存在時插入
            **kwargs: 其他更新參數

        Returns:
            修改的文件數量
        """
        collection = self.get_collection(collection_name, database_name)
        result = await collection.update_many(filter_, update, upsert=upsert, **kwargs)
        return result.modified_count

    async def delete_one(
        self,
        collection_name: str,
        filter_: dict[str, object],
        database_name: str | None = None,
        **kwargs,
    ) -> int:
        """刪除單一文件

        Args:
            collection_name: 集合名稱
            filter_: 查詢條件
            database_name: 資料庫名稱
            **kwargs: 其他刪除參數

        Returns:
            刪除的文件數量
        """
        collection = self.get_collection(collection_name, database_name)
        result = await collection.delete_one(filter_, **kwargs)
        return result.deleted_count

    async def delete_many(
        self,
        collection_name: str,
        filter_: dict[str, object],
        database_name: str | None = None,
        **kwargs,
    ) -> int:
        """刪除多個文件

        Args:
            collection_name: 集合名稱
            filter_: 查詢條件
            database_name: 資料庫名稱
            **kwargs: 其他刪除參數

        Returns:
            刪除的文件數量
        """
        collection = self.get_collection(collection_name, database_name)
        result = await collection.delete_many(filter_, **kwargs)
        return result.deleted_count

    async def count_documents(
        self,
        collection_name: str,
        filter_: dict[str, object] | None = None,
        database_name: str | None = None,
        **kwargs,
    ) -> int:
        """計算文件數量

        Args:
            collection_name: 集合名稱
            filter_: 查詢條件
            database_name: 資料庫名稱
            **kwargs: 其他參數

        Returns:
            符合條件的文件數量
        """
        collection = self.get_collection(collection_name, database_name)
        return await collection.count_documents(filter_ or {}, **kwargs)

    # === 聚合操作 ===

    async def aggregate(
        self,
        collection_name: str,
        pipeline: list[dict[str, object]],
        database_name: str | None = None,
        **kwargs,
    ) -> list[dict[str, object]]:
        """執行聚合管線

        Args:
            collection_name: 集合名稱
            pipeline: 聚合管線
            database_name: 資料庫名稱
            **kwargs: 其他聚合參數

        Returns:
            聚合結果列表
        """
        start = time.time()
        collection = self.get_collection(collection_name, database_name)
        cursor = await collection.aggregate(pipeline, **kwargs)
        data = await cursor.to_list(length=None)
        end = time.time()
        self._logger.info(
            f"db {database_name} coll {collection_name} 聚合管線執行時間: {end - start:.4f} 秒"
        )
        return data

    # === 地理空間查詢工具方法 ===

    def _build_geospatial_filter(
        self, longitude: float, latitude: float, radius_km: float
    ) -> dict[str, object]:
        """建立地理空間查詢條件

        Args:
            longitude: 經度
            latitude: 緯度
            radius_km: 搜尋半徑（公里）

        Returns:
            地理空間查詢條件
        """
        condition = {
            "$geoNear": {
                "near": {"type": "Point", "coordinates": [longitude, latitude]},
                "distanceField": "distance_in_meter",
                "maxDistance": radius_km * 1000,  # 轉換為公尺
                "spherical": True,
            }
        }
        return condition

    def _build_text_search_filter(
        self, search_term: str, field_name: str = "name"
    ) -> dict[str, object]:
        """建立文字搜尋條件

        Args:
            search_term: 搜尋關鍵字
            field_name: 搜尋欄位名稱

        Returns:
            文字搜尋條件
        """
        return {"$regexMatch": {"input": f"${field_name}", "regex": search_term}}

    def _build_store_filters(
        self,
        platform: str | None = None,
        rating_range: tuple[float, float] | None = None,
        review_count_range: tuple[int, int] | None = None,
    ) -> dict[str, object]:
        """建立店家基本篩選條件

        Args:
            platform: 平台名稱
            rating_range: 評分範圍 (min, max)
            review_count_range: 評論數範圍 (min, max)

        Returns:
            店家篩選條件
        """
        filters = {}

        if platform:
            filters["platform"] = platform

        if rating_range:
            filters["rating.value"] = {"$gte": rating_range[0], "$lte": rating_range[1]}

        if review_count_range:
            filters["rating.review_count"] = {
                "$gte": review_count_range[0],
                "$lte": review_count_range[1],
            }

        return filters if filters else {"$expr": True}  # 如果沒有篩選條件，返回永真條件

    def _build_drink_tags_filter(self, drink_tags: list[str]) -> dict[str, object]:
        """建立飲料標籤篩選條件

        Args:
            drink_tags: 飲料標籤列表

        Returns:
            飲料標籤篩選條件
        """
        if not drink_tags:
            return {"$expr": True}

        # 合併所有飲料標籤為單一文字搜尋
        search_terms = " ".join(drink_tags)
        return {"$text": {"$search": search_terms}}

    # === 專用查詢方法 ===

    async def find_drink_stores_with_menu(
        self,
        longitude: float,
        latitude: float,
        drink_tags: list[str] | None = None,
        brands: list[str] | None = None,
        review_count_range: tuple[int, int] | None = None,
        rating_range: tuple[float, float] | None = None,
        distance_range: tuple[int, int] | None = None,
        platform: str | None = None,
        database_name: str | None = None,
    ) -> list[dict[str, object]]:
        """查找符合條件的店家及其完整菜單

        根據 ListStorePayload 的查詢邏輯，找出符合指定條件的店家，
        並返回這些店家的基本資訊和完整菜單。

        Args:
            longitude: 中心點經度
            latitude: 中心點緯度
            drink_tags: 飲料標籤列表（如：["青茶", "奶茶"]）
            brands: 品牌列表
            review_count_range: 評論數範圍 (min, max)
            rating_range: 評分範圍 (min, max)
            distance_range: 距離範圍（公尺）(min, max)
            platform: 平台名稱 ("ubereats" 或 "foodpanda")
            database_name: 資料庫名稱

        Returns:
            符合條件的店家列表，包含店家資訊和完整菜單
        """
        # 如果有飲料標籤篩選，需要採用兩階段查詢策略
        if drink_tags:
            return await self._find_stores_with_drink_tags(
                longitude,
                latitude,
                drink_tags,
                brands,
                review_count_range,
                rating_range,
                distance_range,
                platform,
                database_name,
            )

        # 沒有飲料標籤的情況，直接查詢店家
        return await self._find_stores_without_drink_filter(
            longitude,
            latitude,
            brands,
            review_count_range,
            rating_range,
            distance_range,
            platform,
            database_name,
        )

    async def _find_stores_with_drink_tags(
        self,
        longitude: float,
        latitude: float,
        drink_tags: list[str],
        brands: list[str] | None = None,
        review_count_range: tuple[int, int] | None = None,
        rating_range: tuple[float, float] | None = None,
        distance_range: tuple[int, int] | None = None,
        platform: str | None = None,
        database_name: str | None = None,
    ) -> list[dict[str, object]]:
        """使用飲料標籤篩選的店家查詢（兩階段策略）"""

        # 階段 1: 從 menu_item 找出有匹配飲料的店家 ID
        menu_pipeline = [
            # $text 搜尋必須是第一個階段
            {"$match": self._build_drink_tags_filter(drink_tags)},
            *([{"$match": {"platforms": platform}}] if platform else []),
            {"$group": {"_id": {"store_id": "$store_id", "platforms": "$platforms"}}},
            {
                "$project": {
                    "_id": 0,
                    "store_id": "$_id.store_id",
                    "platforms": "$_id.platforms",
                }
            },
        ]
        matching_stores = await self.aggregate(
            "menu_item", menu_pipeline, database_name
        )

        if not matching_stores:
            return []

        # 準備店家篩選條件
        store_conditions = []
        for store in matching_stores:
            store_conditions.append(
                {"store_id": store["store_id"]},
            )

        # 計算最大距離
        max_distance_km = 5.0 if not distance_range else distance_range[1]

        # 階段 2: 查詢符合條件的店家（不包含菜單）
        store_pipeline = [
            # 地理空間查詢，距離範圍篩選
            self._build_geospatial_filter(longitude, latitude, max_distance_km),
            # 基本店家篩選
            {
                "$match": self._build_store_filters(
                    platform, rating_range, review_count_range
                )
            },
            # 篩選有匹配飲料的店家
            {"$match": {"$or": store_conditions}},
            # 品牌篩選
            *(
                [
                    {
                        "$match": {
                            "$or": [
                                {"name": {"$regex": brand, "$options": "i"}}
                                for brand in brands
                            ]
                        }
                    }
                ]
                if brands
                else []
            ),
            # 整理輸出格式
            {
                "$project": {
                    "_id": 0,
                    "store_id": 1,
                    "name": 1,
                    "address": 1,
                    "platforms": 1,
                    "rating": 1,
                    "review_count": 1,
                    "cuisines": 1,
                    "distance_in_meter": "$distance_in_meter",
                    "distance_in_km": {
                        "$round": [{"$divide": ["$distance_in_meter", 1000]}, 2]
                    },
                }
            },
        ]
        stores = await self.aggregate("store", store_pipeline, database_name)

        if not stores:
            return []

        # 階段 3: 在 Python 中 JOIN 菜單資料
        return await self._join_menu_data(stores, drink_tags, database_name)

    async def _find_stores_without_drink_filter(
        self,
        longitude: float,
        latitude: float,
        brands: list[str] | None = None,
        review_count_range: tuple[int, int] | None = None,
        rating_range: tuple[float, float] | None = None,
        distance_range: tuple[int, int] | None = None,
        platform: str | None = None,
        database_name: str | None = None,
    ) -> list[dict[str, object]]:
        """沒有飲料標籤篩選的店家查詢"""

        # 計算最大距離
        max_distance_km = 5.0 if not distance_range else distance_range[1]

        pipeline = [
            # 地理空間查詢
            self._build_geospatial_filter(longitude, latitude, max_distance_km),
            # 基本店家篩選
            {
                "$match": self._build_store_filters(
                    platform, rating_range, review_count_range
                )
            },
            # 品牌篩選
            *(
                [
                    {
                        "$match": {
                            "$or": [
                                {"name": {"$regex": brand, "$options": "i"}}
                                for brand in brands
                            ]
                        }
                    }
                ]
                if brands
                else []
            ),
            # 整理輸出格式（不包含菜單）
            {
                "$project": {
                    "_id": 0,
                    "store_id": 1,
                    "name": 1,
                    "address": 1,
                    "platforms": 1,
                    "rating": 1,
                    "review_count": 1,
                    "cuisines": 1,
                    "distance_in_meter": "$distance_in_meter",
                    "distance_in_km": {
                        "$round": [{"$divide": ["$distance_in_meter", 1000]}, 2]
                    },
                }
            },
        ]

        stores = await self.aggregate("store", pipeline, database_name)

        if not stores:
            return []

        # 在 Python 中 JOIN 菜單資料
        return await self._join_menu_data(stores, None, database_name)

    async def find_nearby_stores(
        self,
        longitude: float,
        latitude: float,
        radius_km: float = 5.0,
        limit: int | None = None,
        database_name: str | None = None,
    ) -> list[dict[str, object]]:
        """查找附近的店家

        Args:
            longitude: 經度
            latitude: 緯度
            radius_km: 搜尋半徑（公里）
            limit: 限制結果數量
            database_name: 資料庫名稱

        Returns:
            附近的店家列表
        """
        pipeline = [
            self._build_geospatial_filter(longitude, latitude, radius_km),
            {
                "$project": {
                    "_id": 0,
                    "store_id": 1,
                    "name": 1,
                    "address": 1,
                    "platforms": 1,
                    "rating": 1,
                    "cuisines": 1,
                    "distance_km": "$distance_in_km",
                }
            },
        ]

        if limit:
            pipeline.append({"$limit": limit})

        return await self.aggregate("store", pipeline, database_name)

    async def search_menu_items(
        self,
        search_term: str,
        store_ids: list[str] | None = None,
        platform: str | None = None,
        database_name: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        """搜尋菜單項目

        Args:
            search_term: 搜尋關鍵字
            store_ids: 指定店家 ID 列表
            platform: 指定平台
            database_name: 資料庫名稱
            limit: 限制結果數量

        Returns:
            符合條件的菜單項目列表
        """
        filter_conditions = {
            "$regexMatch": {
                "input": "$name",
                "regex": search_term,
                "options": "i",  # 大小寫不敏感
            }
        }

        # 建立額外的篩選條件
        additional_filters = []
        if store_ids:
            additional_filters.append({"$in": ["$store_id", store_ids]})
        if platform:
            additional_filters.append({"$eq": ["$platforms", platform]})

        # 組合所有條件
        if additional_filters:
            match_condition = {"$and": [filter_conditions] + additional_filters}
        else:
            match_condition = filter_conditions

        pipeline = [
            {"$match": {"$expr": match_condition}},
            {
                "$project": {
                    "_id": 0,
                    "item_id": 1,
                    "store_id": 1,
                    "platforms": 1,
                    "name": 1,
                    "category": 1,
                    "description": 1,
                    "price": 1,
                    "is_popular": 1,
                }
            },
        ]

        if limit:
            pipeline.append({"$limit": limit})

        return await self.aggregate("menu_item", pipeline, database_name)

    async def _join_menu_data(
        self,
        stores: list[dict[str, object]],
        drink_tags: list[str] | None = None,
        database_name: str | None = None,
    ) -> list[dict[str, object]]:
        """在 Python 中將店家與菜單資料進行 JOIN

        Args:
            stores: 店家列表
            drink_tags: 飲料標籤列表，用於文字搜尋和排序
            database_name: 資料庫名稱

        Returns:
            包含完整菜單的店家列表，如有 drink_tags 則按搜尋相關性排序
        """
        if not stores:
            return []

        # 建立店家查詢條件
        store_conditions = []
        for store in stores:
            store_conditions.append(
                {"store_id": store["store_id"]},
            )

        # 查詢所有相關菜單項目
        menu_pipeline = []

        # 如果有飲料標籤，加入文字搜尋條件
        if drink_tags:
            # $text 搜尋必須是第一個階段
            menu_pipeline.append({"$match": self._build_drink_tags_filter(drink_tags)})
            # 然後加入店家條件篩選
            menu_pipeline.append({"$match": {"$or": store_conditions}})
            # 加入文字搜尋分數用於排序
            menu_pipeline.extend(
                [
                    {"$addFields": {"text_score": {"$meta": "textScore"}}},
                    {
                        "$project": {
                            "_id": 0,
                            "item_id": 1,
                            "store_id": 1,
                            "name": 1,
                            "category": 1,
                            "description": 1,
                            "price": 1,
                            "is_popular": 1,
                            "options": 1,
                            "text_score": 1,
                        }
                    },
                    # 按文字搜尋分數排序
                    {"$sort": {"text_score": {"$meta": "textScore"}}},
                ]
            )
        else:
            # 沒有飲料標籤時的一般查詢
            menu_pipeline.extend(
                [
                    {"$match": {"$or": store_conditions}},
                    {
                        "$project": {
                            "_id": 0,
                            "item_id": 1,
                            "store_id": 1,
                            "name": 1,
                            "category": 1,
                            "description": 1,
                            "price": 1,
                            "is_popular": 1,
                            "options": 1,
                        }
                    },
                ]
            )

        menu_items = await self.aggregate("menu_item", menu_pipeline, database_name)

        # 建立菜單項目索引以提高查詢效率
        menu_index = {}
        store_hit_counts = {}  # 記錄每個店家的命中數量

        for item in menu_items:
            key = item["store_id"]
            if key not in menu_index:
                menu_index[key] = []
                store_hit_counts[key] = 0
            menu_index[key].append(item)
            store_hit_counts[key] += 1

        # 為每個店家添加對應的菜單
        result = []
        for store in stores:
            store_copy = store.copy()
            key = store["store_id"]
            store_copy["menu"] = menu_index.get(key, [])
            # 如果有飲料標籤搜尋，加入命中數量用於排序
            if drink_tags:
                store_copy["hit_count"] = store_hit_counts.get(key, 0)
            result.append(store_copy)

        # 如果有飲料標籤，按命中數量排序（由大到小）
        if drink_tags:
            result.sort(key=lambda x: x.get("hit_count", 0), reverse=True)
            # 移除臨時的 hit_count 欄位
            for store in result:
                store.pop("hit_count", None)

        return result

    async def find_drinks(
        self,
        longitude: float,
        latitude: float,
        drink_tags: list[str] | None = None,
        brands: list[str] | None = None,
        review_count_range: tuple[int, int] | None = None,
        rating_range: tuple[float, float] | None = None,
        distance_range: tuple[int, int] | None = None,
        platform: str | None = None,
        limit: int | None = None,
        database_name: str | None = None,
    ) -> list[dict[str, object]]:
        """查找符合條件的飲料菜單項目，附帶所屬店家資訊

        採用兩階段查詢策略：
        1. 先對 store collection 進行地理空間篩選和店家條件篩選
        2. 根據符合條件的店家 ID，對 menu_item collection 進行飲料標籤搜尋

        Args:
            longitude: 中心點經度
            latitude: 中心點緯度
            drink_tags: 飲料標籤列表（如：["青茶", "奶茶"]）
            brands: 品牌列表
            review_count_range: 評論數範圍 (min, max)
            rating_range: 評分範圍 (min, max)
            distance_range: 距離範圍（公尺）(min, max)
            platform: 平台名稱 ("ubereats" 或 "foodpanda")
            limit: 限制結果數量
            database_name: 資料庫名稱

        Returns:
            飲料菜單項目列表，每個項目包含完整的店家資訊
            格式：[{
                "item_id": "...",
                "name": "...",
                "description": "...",
                "price": 120.0,
                "category": "...",
                "is_popular": true,
                "options": [...],
                "store": {
                    "store_id": "...",
                    "name": "...",
                    "address": "...",
                    "rating": {...},
                    "distance_in_meter": 1200,
                    "distance_in_km": 1.2,
                    ...
                }
            }]
        """
        # 階段 1: 查詢符合條件的店家
        qualifying_stores = await self._find_qualifying_stores(
            longitude,
            latitude,
            brands,
            review_count_range,
            rating_range,
            distance_range,
            platform,
            database_name,
        )

        if not qualifying_stores:
            return []

        # 階段 2: 根據店家 ID 和飲料標籤查詢菜單項目
        return await self._find_drinks_from_stores(
            qualifying_stores, drink_tags, platform, limit, database_name
        )

    async def _find_qualifying_stores(
        self,
        longitude: float,
        latitude: float,
        brands: list[str] | None = None,
        review_count_range: tuple[int, int] | None = None,
        rating_range: tuple[float, float] | None = None,
        distance_range: tuple[int, int] | None = None,
        platform: str | None = None,
        database_name: str | None = None,
    ) -> list[dict[str, object]]:
        """第一階段：查詢符合條件的店家"""

        # 計算最大距離
        max_distance_km = 5.0 if not distance_range else distance_range[1]

        # 建立店家查詢管線
        pipeline = [
            # 地理空間查詢
            self._build_geospatial_filter(longitude, latitude, max_distance_km),
            # 基本店家篩選
            {
                "$match": self._build_store_filters(
                    platform, rating_range, review_count_range
                )
            },
            # 品牌篩選
            *(
                [
                    {
                        "$match": {
                            "$or": [
                                {"name": {"$regex": brand, "$options": "i"}}
                                for brand in brands
                            ]
                        }
                    }
                ]
                if brands
                else []
            ),
            # 整理店家資料格式
            {
                "$project": {
                    "_id": 0,
                    "store_id": 1,
                    "name": 1,
                    "brand": 1,
                    "address": 1,
                    "platform": 1,
                    "rating": 1,
                    "review_count": 1,
                    "cuisines": 1,
                    "source_url": 1,
                    "distance_in_meter": "$distance_in_meter",
                    "distance_in_km": {
                        "$round": [{"$divide": ["$distance_in_meter", 1000]}, 2]
                    },
                }
            },
        ]
        return await self.aggregate("store", pipeline, database_name)

    async def _find_drinks_from_stores(
        self,
        stores: list[dict[str, object]],
        drink_tags: list[str] | None = None,
        platform: str | None = None,
        limit: int | None = None,
        database_name: str | None = None,
    ) -> list[dict[str, object]]:
        """第二階段：根據店家列表和飲料標籤查詢菜單項目"""

        # 建立店家查詢條件
        store_conditions = []
        for store in stores:
            condition = {"store_id": store["store_id"]}
            store_conditions.append(condition)

        # 建立菜單項目查詢管線
        pipeline = []

        # 如果有飲料標籤，使用文字搜尋（必須是第一個階段）
        if drink_tags:
            pipeline.append({"$match": self._build_drink_tags_filter(drink_tags)})

        pipeline.append({"$match": {"price": {"$gte": 20}}})

        # 篩選符合條件的店家
        pipeline.append({"$match": {"$or": store_conditions}})

        # 如果有飲料標籤，加入文字搜尋分數
        if drink_tags:
            pipeline.append({"$addFields": {"text_score": {"$meta": "textScore"}}})

        # 整理菜單項目資料格式
        pipeline.append(
            {
                "$project": {
                    "_id": 0,
                    "item_id": 1,
                    "name": 1,
                    "description": 1,
                    "price": 1,
                    "image_url": 1,
                    "category": 1,
                    "is_popular": 1,
                    "options": 1,
                    "store_id": 1,
                    "platforms": 1,
                    **({"text_score": 1} if drink_tags else {}),
                }
            }
        )

        # 排序
        if drink_tags:
            # 如果有飲料標籤搜尋，按文字搜尋分數排序
            pipeline.append({"$sort": {"text_score": {"$meta": "textScore"}}})

        # 限制結果數量
        if limit:
            pipeline.append({"$limit": limit})

        # 執行菜單項目查詢
        menu_items = await self.aggregate("menu_item", pipeline, database_name)

        # 建立店家索引以便快速查詢
        store_index = {}
        for store in stores:
            key = (store["store_id"], store.get("platforms"))
            store_index[key] = store

        # 將店家資料附加到每個菜單項目
        result = []
        for item in menu_items:
            # 尋找對應的店家資料
            key = (item["store_id"], item.get("platforms"))
            store_data = store_index.get(key)

            if store_data:
                # 附加店家資料，移除臨時欄位
                item["store_id"] = item.pop("store_id", store_data["store_id"])
                item["platform"] = item.pop("platform", store_data.get("platform"))
                item["store_name"]= store_data.get("name")
                item["store_url"] = store_data.get("source_url")
                item["brand_name"] = store_data.get("brand")

                result.append(item)
        result.sort(key=lambda x: x["text_score"], reverse=True) if drink_tags else None
        return result

    # === 私有輔助方法 ===

    def _ensure_initialized(self) -> None:
        """確保驅動已初始化"""
        if not self._is_initialized():
            raise RuntimeError("MongoDriver 尚未初始化，請先呼叫 initialize() 方法")
