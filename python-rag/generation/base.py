"""
generation/base.py
GenerationProvider 抽象介面
"""
from abc import ABC, abstractmethod
from typing import Iterator


class GenerationProviderError(Exception):
    """GenerationProvider 初始化或呼叫失敗"""


class GenerationProvider(ABC):
    """文字生成 Provider 抽象介面"""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """接收完整 prompt 並回傳生成文字"""
        ...

    @abstractmethod
    def generate_stream(self, prompt: str) -> Iterator[str]:
        """以迭代器方式逐 token 回傳生成文字"""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """回傳識別字串，例如 'ollama:qwen3-8b'"""
        ...
