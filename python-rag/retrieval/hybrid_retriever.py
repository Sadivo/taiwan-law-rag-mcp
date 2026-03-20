from typing import List, Dict, Any
from .vector_retriever import VectorRetriever
from .bm25_retriever import BM25Retriever
import numpy as np

class HybridRetriever:
    """
    混合檢索: Vector Search + BM25
    1. 平行或順序執行 Vector 與 BM25
    2. 使用 RRF 進行排名融合
    """
    def __init__(self, vector_retriever: VectorRetriever, bm25_retriever: BM25Retriever, embedder=None):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.embedder = embedder
        
    def _rrf(self, rankings: List[List[Dict[str, Any]]], k: int = 60) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion 演算法
        RRF(d) = Σ 1/(k + rank_i(d))
        """
        rrf_scores = {}
        docs_map = {}
        
        for ranking in rankings:
            for rank, doc in enumerate(ranking):
                # 假設 doc 必需有唯一標識 'id' (由 chunker 生產的 chunk_id)
                doc_id = doc.get('id')
                if doc_id is None:
                    continue
                    
                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = 0.0
                    docs_map[doc_id] = doc
                    
                rrf_scores[doc_id] += 1.0 / (k + rank + 1)
                
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in sorted_docs:
            doc = docs_map[doc_id].copy()
            doc['rrf_score'] = score
            results.append(doc)
            
        return results

    def search(self, query: str, top_k: int = 20, max_retrieval: int = 30) -> List[Dict[str, Any]]:
        # 1. 取得 Query Vector
        query_vector = None
        if self.embedder:
            query_vector = self.embedder.embed_query(query)
        else:
            # 備用假資料產生，以應對模組尚未整合好的情況
            dim = 4096
            if hasattr(self.vector_retriever, 'index') and self.vector_retriever.index is not None:
                dim = self.vector_retriever.index.d
            query_vector = np.random.rand(dim).astype('float32')
            
        # 2. 檢索搜集
        vector_results = self.vector_retriever.search(query_vector, top_k=max_retrieval)
        bm25_results = self.bm25_retriever.search(query, top_k=max_retrieval)
        
        # 3. RRF 融合
        fusion_results = self._rrf([vector_results, bm25_results], k=60)
        
        # 4. 回傳前 N 筆給後續作為 rerank 基礎
        return fusion_results[:top_k]
