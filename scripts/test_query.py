import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../python-rag')))

from retrieval.query_classifier import QueryClassifier
from retrieval.vector_retriever import VectorRetriever
from retrieval.bm25_retriever import BM25Retriever
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.reranker import Reranker
from retrieval.deduplicator import Deduplicator

import warnings
warnings.filterwarnings("ignore")

def test_query():
    print("="*50)
    print("初始化組件...")
    start_time = time.time()
    
    classifier = QueryClassifier()
    # 確保傳入相對路徑是可以從專案根目錄相對應的
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    vector_retriever = VectorRetriever(
        index_path=os.path.join(base_dir, "data/taiwan_law.faiss"), 
        meta_path=os.path.join(base_dir, "data/chunks.pkl")
    )
    bm25_retriever = BM25Retriever(
        index_dir=os.path.join(base_dir, "data/bm25_index")
    )
    
    hybrid_retriever = HybridRetriever(vector_retriever, bm25_retriever)
    reranker = Reranker()
    deduplicator = Deduplicator(max_per_law=3)
    
    print(f"初始化完成，耗時: {time.time() - start_time:.2f} 秒")
    
    queries = [
        "勞基法第38條",
        "加班費如何計算",
        "員工離職後競業禁止"
    ]
    
    for query in queries:
        print("\n" + "="*50)
        print(f"測試查詢: '{query}'")
        
        # 1. 分類
        cls_res = classifier.classify(query)
        print(f"分類結果: {cls_res}")
        
        # 2. 檢索
        search_start = time.time()
        
        # 使用 Hybrid Retriever
        hybrid_docs = hybrid_retriever.search(query, top_k=20, max_retrieval=30)
        
        # 3. Rerank
        reranked_docs = reranker.rerank(query, hybrid_docs, top_k=10)
        
        # 4. 去重
        final_docs = deduplicator.deduplicate(reranked_docs)
        
        search_time = time.time() - search_start
        passed = "✅" if search_time < 1.5 else "❌"
        print(f"\n檢索花費時間: {search_time:.4f} 秒 {passed}, 總共取得 {len(final_docs)} 條結果")
        
        # 印出 Top 3
        for i, doc in enumerate(final_docs[:3]):
            law_name = doc.get('law_name', '未知')
            article_no = doc.get('article_no', '未知')
            score = doc.get('rerank_score', doc.get('rrf_score', 0))
            print(f"[{i+1}] {law_name} {article_no} (Score: {score:.4f})")
            
    print("\n驗證腳本執行結束")

if __name__ == "__main__":
    test_query()
