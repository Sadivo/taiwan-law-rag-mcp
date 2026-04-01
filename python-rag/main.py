from contextlib import asynccontextmanager
import logging
import os

from dotenv import load_dotenv
load_dotenv()  # 載入 .env 檔（若存在）

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api import routes
from api import chat_routes
from api import session_routes
from api.models import HealthResponse, GenerationProviderInfo
from api.health import (
    HealthState,
    ProviderInfo,
    ProviderStatus,
    get_health_state,
    set_health_state,
    check_generation_reachable,
    print_startup_summary,
)

# 設定日誌
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

host = os.getenv("API_HOST", "127.0.0.1")
port = int(os.getenv("API_PORT", "8073") or "8073")


def _provider_display_name(provider) -> str:
    """Build a 'type:model' display string from a provider instance."""
    provider_type = type(provider).__name__
    if hasattr(provider, "_embedder"):
        model = getattr(provider._embedder, "model_name", "")
        short = model.split("/")[-1] if model else provider_type
        return f"local:{short}"
    if hasattr(provider, "_reranker"):
        model = getattr(provider._reranker, "model_name", "")
        short = model.split("/")[-1] if model else provider_type
        return f"local:{short}"
    if hasattr(provider, "_config"):
        cfg = provider._config
        ptype = getattr(cfg, "provider_type", "unknown")
        model = getattr(cfg, "model_name", None) or ""
        short = model.split("/")[-1] if model else ptype
        return f"{ptype}:{short}" if short else ptype
    return provider_type


def _init_generation_safe():
    """嘗試初始化 generation provider；失敗回傳 None。"""
    try:
        from providers.factory import ProviderFactory
        provider = ProviderFactory.generation_from_env()
        return provider
    except Exception as exc:
        logger.warning("Generation provider 初始化失敗（標記為 unreachable）：%s", exc)
        return None


def _generation_display_name() -> str:
    """Build generation provider display name from env vars."""
    provider_type = os.getenv("GENERATION_PROVIDER", "ollama")
    model_name = os.getenv("GENERATION_MODEL_NAME", "")
    if model_name:
        short = model_name.split("/")[-1]
        return f"{provider_type}:{short}"
    return provider_type


def _build_health_state(embedding_provider, reranking_provider, generation_provider) -> HealthState:
    """組裝 HealthState，對 generation provider 做 probe 確認可連線性。"""
    emb_name = _provider_display_name(embedding_provider)
    rer_name = _provider_display_name(reranking_provider)

    if generation_provider is None:
        gen_name = _generation_display_name()
        gen_status = ProviderStatus.UNREACHABLE
    else:
        gen_name = _provider_display_name(generation_provider)
        if not gen_name or gen_name == type(generation_provider).__name__:
            gen_name = _generation_display_name()
        gen_status = check_generation_reachable(generation_provider)

    return HealthState(
        embedding=ProviderInfo(name=emb_name, status=ProviderStatus.OK),
        reranking=ProviderInfo(name=rer_name, status=ProviderStatus.OK),
        generation=ProviderInfo(name=gen_name, status=gen_status),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    from providers.factory import ProviderFactory
    from retrieval.retrieval_service import RetrievalService
    from retrieval.vector_retriever import VectorRetriever
    from retrieval.bm25_retriever import BM25Retriever
    from retrieval.hybrid_retriever import HybridRetriever

    logger.info("Initializing providers via ProviderFactory.from_env()...")
    # 失敗則 raise，讓 uvicorn 以非零 exit code 結束
    embedding_provider, reranking_provider = ProviderFactory.from_env()

    # 初始化 retrieval service，讓 routes.py 不需要 lazy init
    vector_retriever = VectorRetriever()
    bm25_retriever = BM25Retriever()
    hybrid_retriever = HybridRetriever(
        vector_retriever, bm25_retriever, embedder=embedding_provider
    )
    routes._retrieval_service = RetrievalService(
        embedding_provider, reranking_provider, hybrid_retriever
    )
    routes._embedding_provider_name = _provider_display_name(embedding_provider)
    routes._reranking_provider_name = _provider_display_name(reranking_provider)

    # 失敗回傳 None，標記 unreachable
    generation_provider = _init_generation_safe()

    state = _build_health_state(embedding_provider, reranking_provider, generation_provider)
    set_health_state(state)
    print_startup_summary(state, host, port)

    yield
    # shutdown（無需特別清理）


app = FastAPI(
    title="Taiwan Law RAG API",
    description="台灣法律 RAG MCP 系統的檢索 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載路由
app.include_router(routes.router)
app.include_router(chat_routes.router)
app.include_router(session_routes.router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        state = get_health_state()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Service not initialized")

    response = HealthResponse(
        status=state.overall_status,
        embedding_provider=state.embedding.name,
        reranking_provider=state.reranking.name,
        generation_provider=GenerationProviderInfo(
            name=state.generation.name,
            status=state.generation.status.value,
        ),
    )

    if state.overall_status == "error":
        raise HTTPException(status_code=503, detail=response.model_dump())

    return response


if __name__ == "__main__":
    import uvicorn

    logger.info(f"啟動伺服器：http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
