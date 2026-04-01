"""
api/health.py
Health Checker 模組：ProviderStatus、ProviderInfo、HealthState 及相關工具函式
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProviderStatus(str, Enum):
    OK = "ok"
    UNREACHABLE = "unreachable"
    ERROR = "error"


@dataclass
class ProviderInfo:
    name: str           # e.g. "local:Qwen3-Embedding-4B"
    status: ProviderStatus


@dataclass
class HealthState:
    embedding: ProviderInfo
    reranking: ProviderInfo
    generation: ProviderInfo

    @property
    def overall_status(self) -> str:
        statuses = {self.embedding.status, self.reranking.status, self.generation.status}
        if ProviderStatus.ERROR in statuses:
            return "error"
        if ProviderStatus.UNREACHABLE in statuses:
            return "degraded"
        return "ok"


# Module-level singleton，由 lifespan 設定
_health_state: HealthState | None = None


def get_health_state() -> HealthState:
    """回傳目前的 HealthState singleton；若尚未初始化則拋出 RuntimeError"""
    if _health_state is None:
        raise RuntimeError("HealthState 尚未初始化，請確認 lifespan 已正確執行")
    return _health_state


def set_health_state(state: HealthState) -> None:
    """設定 module-level HealthState singleton"""
    global _health_state
    _health_state = state


def check_generation_reachable(provider) -> ProviderStatus:
    """對 generation provider 發送最小 probe 請求，判斷是否可連線。

    捕捉所有例外並回傳 UNREACHABLE；成功則回傳 OK。
    """
    try:
        provider.generate("")
        return ProviderStatus.OK
    except Exception:
        return ProviderStatus.UNREACHABLE


def print_startup_summary(state: HealthState, host: str, port: int) -> None:
    """輸出啟動摘要至 stdout，包含服務 URL 與各 provider 狀態。

    格式範例：
        Taiwan Law RAG — http://127.0.0.1:8073
          ✓ Embedding  : local:Qwen3-Embedding-4B
          ✓ Reranking  : local:Qwen3-Reranker-4B
          ✗ Generation : ollama:qwen3:8b (unreachable at http://localhost:11434)
    """
    def _symbol(status: ProviderStatus) -> str:
        return "✓" if status == ProviderStatus.OK else "✗"

    url = f"http://{host}:{port}"
    print(f"Taiwan Law RAG — {url}")
    print(f"  {_symbol(state.embedding.status)} Embedding  : {state.embedding.name}")
    print(f"  {_symbol(state.reranking.status)} Reranking  : {state.reranking.name}")
    print(f"  {_symbol(state.generation.status)} Generation : {state.generation.name}")
