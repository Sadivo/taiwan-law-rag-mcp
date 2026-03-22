"""
providers/config.py
自訂例外類別與 ProviderConfig 設定模型
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 例外類別層次
# ---------------------------------------------------------------------------

class ProviderError(Exception):
    """所有 Provider 例外的基底類別"""


class ProviderInitializationError(ProviderError):
    """模型或 API 初始化失敗"""


class ProviderAPIError(ProviderError):
    """線上 API 呼叫失敗且重試耗盡"""


class ProviderConfigError(ProviderError):
    """設定錯誤（未知類型、缺少金鑰等）"""


class DimensionMismatchError(ProviderError):
    """向量維度與 FAISS 索引不符"""


# ---------------------------------------------------------------------------
# ProviderConfig
# ---------------------------------------------------------------------------

ProviderType = str  # 允許任意字串，factory 層負責驗證


class ProviderConfig(BaseModel):
    model_config = {"protected_namespaces": ()}

    provider_type: ProviderType = "local"
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    batch_size: int = Field(default=100, ge=1)
    extra: dict = Field(default_factory=dict)

    def to_json(self) -> str:
        """將設定序列化為 JSON 字串"""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> "ProviderConfig":
        """從 JSON 字串解析為 ProviderConfig 物件"""
        return cls.model_validate_json(json_str)
