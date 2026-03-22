from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import time
import hashlib
import json
import logging
from .models import (
    SemanticSearchRequest, ExactSearchRequest, LawSearchRequest,
    LawFullRequest, CompareRequest, RebuildIndexRequest,
    SearchResponse, ExactSearchResponse, LawSearchResponse,
    LawFullResponse, CompareResponse, RebuildIndexResponse,
    SearchResult, Law, Article
)
from .cache import query_cache

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level singleton — initialized once on first request
_retrieval_service = None
_embedding_provider_name: str = "unknown"
_reranking_provider_name: str = "unknown"


def _provider_display_name(provider) -> str:
    """Build a 'type:model' display string from a provider instance."""
    provider_type = type(provider).__name__
    # LocalEmbeddingProvider / LocalRerankingProvider
    if hasattr(provider, "_embedder"):
        model = getattr(provider._embedder, "model_name", "")
        short = model.split("/")[-1] if model else provider_type
        return f"local:{short}"
    if hasattr(provider, "_reranker"):
        model = getattr(provider._reranker, "model_name", "")
        short = model.split("/")[-1] if model else provider_type
        return f"local:{short}"
    # LangChainEmbeddingProvider / LangChainRerankingProvider
    if hasattr(provider, "_config"):
        cfg = provider._config
        ptype = getattr(cfg, "provider_type", "unknown")
        model = getattr(cfg, "model_name", None) or ""
        short = model.split("/")[-1] if model else ptype
        return f"{ptype}:{short}" if short else ptype
    return provider_type


def get_retrieval_service():
    """Return the singleton RetrievalService, initializing it on first call."""
    global _retrieval_service, _embedding_provider_name, _reranking_provider_name

    if _retrieval_service is not None:
        return _retrieval_service

    try:
        from providers.factory import ProviderFactory
        from retrieval.retrieval_service import RetrievalService
        from retrieval.vector_retriever import VectorRetriever
        from retrieval.bm25_retriever import BM25Retriever
        from retrieval.hybrid_retriever import HybridRetriever

        logger.info("Initializing providers via ProviderFactory.from_env()...")
        embedding_provider, reranking_provider = ProviderFactory.from_env()

        _embedding_provider_name = _provider_display_name(embedding_provider)
        _reranking_provider_name = _provider_display_name(reranking_provider)

        logger.info(
            "Providers initialized: embedding=%s, reranking=%s",
            _embedding_provider_name,
            _reranking_provider_name,
        )

        vector_retriever = VectorRetriever()
        bm25_retriever = BM25Retriever()
        hybrid_retriever = HybridRetriever(
            vector_retriever, bm25_retriever, embedder=embedding_provider
        )

        _retrieval_service = RetrievalService(
            embedding_provider, reranking_provider, hybrid_retriever
        )
        logger.info("RetrievalService singleton created successfully.")
    except Exception as exc:
        logger.error("Failed to initialize RetrievalService: %s", exc)
        raise

    return _retrieval_service


def _generate_cache_key(prefix: str, **kwargs) -> str:
    key_content = json.dumps(kwargs, sort_keys=True)
    return prefix + ":" + hashlib.md5(key_content.encode('utf-8')).hexdigest()

@router.post("/search/semantic", response_model=SearchResponse)
async def semantic_search(request: SemanticSearchRequest, service = Depends(get_retrieval_service)):
    start_time = time.time()
    
    # 檢查快取
    cache_key = _generate_cache_key("semantic", query=request.query, top_k=request.top_k, filter=request.filter_category)
    cached_result = query_cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for query: {request.query}")
        return cached_result
    
    try:
        raw_results = service.search_semantic(
            query=request.query, 
            top_k=request.top_k, 
            filter_category=request.filter_category
        )
        
        results = [SearchResult(**r) for r in raw_results]
        query_time = time.time() - start_time
        
        response = SearchResponse(
            results=results,
            total=len(results),
            query_time=query_time
        )
        
        # 寫入快取
        query_cache.set(cache_key, response)
        return response
        
    except Exception as e:
        logger.error(f"Semantic search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search/exact", response_model=ExactSearchResponse)
async def exact_search(request: ExactSearchRequest, service = Depends(get_retrieval_service)):
    try:
        raw_results = service.search_exact(request.query)
        return ExactSearchResponse(results=[SearchResult(**r) for r in raw_results])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search/law", response_model=LawSearchResponse)
async def law_search(request: LawSearchRequest, service = Depends(get_retrieval_service)):
    try:
        raw_results = service.search_law(request.law_name, request.include_abolished)
        return LawSearchResponse(results=[SearchResult(**r) for r in raw_results])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/law/full", response_model=LawFullResponse)
async def get_law_full(request: LawFullRequest, service = Depends(get_retrieval_service)):
    try:
        data = service.get_law_full(request.law_name)
        return LawFullResponse(law=data["law"], articles=data.get("articles", []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/law/compare", response_model=CompareResponse)
async def compare_laws(request: CompareRequest, service = Depends(get_retrieval_service)):
    try:
        data = service.compare_laws(request.law_names, request.topic)
        return CompareResponse(comparison=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/index/rebuild", response_model=RebuildIndexResponse)
async def rebuild_index(request: RebuildIndexRequest, background_tasks: BackgroundTasks, service = Depends(get_retrieval_service)):
    try:
        data = service.rebuild_index(request.force)
        return RebuildIndexResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
