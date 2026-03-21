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

# 模擬或依賴注入 Retrieval Service 的介面
# 未來可替換為實際的檢索模組 (Phase 4 實作)
def get_retrieval_service():
    class DummyRetrievalService:
        def search_semantic(self, query: str, top_k: int, filter_category: str):
            return [{
                "law_name": "勞動基準法", "law_level": "法律",
                "law_category": "行政>勞動部>勞動條件及就業平等目", "law_url": "https://law.moj.gov.tw/",
                "article_no": "第 38 條", "chapter": "第四章",
                "content": f"這是關於 {query} 的模擬條文...", "score": 0.95, "modified_date": "20180621"
            }]

        def search_exact(self, query: str):
            return []
            
        def search_law(self, law_name: str, include_abolished: bool):
            return []
            
        def get_law_full(self, law_name: str):
            law = Law(
                law_name=law_name, law_level="法律", law_category="測試分類",
                law_url="http://test", modified_date="20200101", is_abolished=False
            )
            return {"law": law, "articles": []}
            
        def compare_laws(self, law_names: list, topic: str):
            return {name: [] for name in law_names}
            
        def rebuild_index(self, force: bool):
            return {"status": "success", "chunks": 55000, "time": 10.5}
            
    return DummyRetrievalService()

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
