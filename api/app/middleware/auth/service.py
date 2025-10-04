# -*- coding: utf-8 -*-
"""
API Key 認證服務

處理 API Key 的驗證邏輯，包括固定 API Key 和規則型 API Key。
提供快取機制以提升驗證效能。
"""

import hashlib
import hmac
import time

from app.setting import Setting

from .base import BaseAuthService


class ApiKeyAuthService(BaseAuthService):
    """API Key 認證服務類別

    處理 API Key 的驗證邏輯，包括固定 API Key 和規則型 API Key。
    提供快取機制以提升驗證效能。
    """

    def __init__(self, setting: Setting):
        super().__init__(setting)
        self.cache: dict[
            str, tuple[bool, float]
        ] = {}  # {api_key: (is_valid, timestamp)}

    def validate(self, api_key: str) -> bool:
        """驗證 API Key

        Args:
            api_key: 要驗證的 API Key

        Returns:
            bool: 驗證是否通過
        """
        return self.validate_api_key(api_key)

    def validate_api_key(self, api_key: str) -> bool:
        """驗證 API Key

        Args:
            api_key: 要驗證的 API Key

        Returns:
            bool: 驗證是否通過
        """
        # 檢查快取
        if self._check_cache(api_key):
            return self.cache[api_key][0]

        # 驗證 API Key
        is_valid = self._validate_fixed_key(api_key) or self._validate_rule_key(api_key)

        # 快取結果
        self._cache_result(api_key, is_valid)
        return is_valid

    def _check_cache(self, api_key: str) -> bool:
        """檢查快取中是否有有效的驗證結果

        Args:
            api_key: API Key

        Returns:
            bool: 快取中是否有有效結果
        """
        if api_key not in self.cache:
            return False

        _, cached_time = self.cache[api_key]
        current_time = time.time()

        # 檢查快取是否過期
        if current_time - cached_time > self.setting.AUTH_CACHE_TTL_SECONDS:
            del self.cache[api_key]
            return False

        return True

    def _cache_result(self, api_key: str, is_valid: bool):
        """快取驗證結果

        Args:
            api_key: API Key
            is_valid: 驗證結果
        """
        self.cache[api_key] = (is_valid, time.time())

    def _validate_fixed_key(self, api_key: str) -> bool:
        """驗證固定 API Key

        Args:
            api_key: 要驗證的 API Key

        Returns:
            bool: 是否為有效的固定 API Key
        """
        return api_key in self.setting.fixed_api_keys

    def _validate_rule_key(self, api_key: str) -> bool:
        """驗證規則型 API Key

        規則型 API Key 格式：{prefix}_{timestamp}_{signature}
        例如：pk_1693699200_a1b2c3d4

        Args:
            api_key: 要驗證的 API Key

        Returns:
            bool: 是否為有效的規則型 API Key
        """
        # 解析 API Key 格式
        parts = api_key.split("_")
        if len(parts) != 3 or parts[0] != self.setting.AUTH_RULE_PREFIX:
            return False

        try:
            timestamp = int(parts[1])
            signature = parts[2]

            # 檢查時間窗口
            current_time = int(time.time())
            if current_time - timestamp > self.setting.AUTH_TIME_WINDOW_HOURS * 3600:
                self.logger.debug(f"Rule-based API Key expired: {api_key[:10]}...")
                return False

            # 驗證簽名
            expected_signature = self._generate_signature(
                self.setting.AUTH_RULE_PREFIX, timestamp
            )
            if signature == expected_signature:
                self.logger.debug(
                    f"Rule-based API Key validated successfully: {api_key[:10]}..."
                )
                return True
            else:
                self.logger.debug(
                    f"Rule-based API Key signature mismatch: {api_key[:10]}..."
                )
                return False

        except (ValueError, IndexError) as e:
            self.logger.debug(
                f"Rule-based API Key format error: {api_key[:10]}..., error: {e}"
            )
            return False

    def _generate_signature(self, prefix: str, timestamp: int) -> str:
        """生成 API Key 簽名

        使用 HMAC-SHA256 生成簽名，取前 8 個字元。

        Args:
            prefix: API Key 前綴
            timestamp: 時間戳

        Returns:
            str: 生成的簽名
        """
        message = f"{prefix}_{timestamp}"
        secret_key = self.setting.API_KEY.encode("utf-8")
        signature = hmac.new(secret_key, message.encode("utf-8"), hashlib.sha256)
        return signature.hexdigest()[:8]

    def generate_rule_key(self, timestamp: int | None = None) -> str:
        """生成規則型 API Key（用於測試或管理工具）

        Args:
            timestamp: 指定的時間戳，如果為 None 則使用當前時間

        Returns:
            str: 生成的規則型 API Key
        """
        if timestamp is None:
            timestamp = int(time.time())

        signature = self._generate_signature(self.setting.AUTH_RULE_PREFIX, timestamp)
        return f"{self.setting.AUTH_RULE_PREFIX}_{timestamp}_{signature}"

    def mask_api_key(self, api_key: str) -> str:
        """遮罩 API Key 用於日誌記錄

        保留前 4 位和後 4 位字元，中間用 * 替代。

        Args:
            api_key: 原始 API Key

        Returns:
            str: 遮罩後的 API Key
        """
        if len(api_key) <= 8:
            return "*" * len(api_key)
        return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]


__all__ = [
    "ApiKeyAuthService",
]
