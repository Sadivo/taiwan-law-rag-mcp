import os
from typing import List, Dict, Any
import jieba

class BM25Retriever:
    """
    Whoosh BM25 檢索
    1. 開啟 Whoosh 索引目錄
    2. 使用分詞處理 query
    3. 進行關鍵字搜尋
    """
    def __init__(self, index_dir: str = "data/bm25_index"):
        self.index_dir = index_dir
        self.ix = None
        self._load_index()

    def _load_index(self):
        try:
            from whoosh.index import open_dir
        except ImportError:
            print("Warning: whoosh is not installed.")
            return

        full_index_dir = os.path.abspath(self.index_dir)
        if os.path.exists(full_index_dir):
            try:
                self.ix = open_dir(full_index_dir)
            except Exception as e:
                print(f"Error opening Whoosh index: {e}")
        else:
            print(f"Whoosh index directory not found at {full_index_dir}")

    def search(self, query: str, top_k: int = 30) -> List[Dict[str, Any]]:
        if self.ix is None:
            return []
            
        try:
            from whoosh.qparser import QueryParser
        except ImportError:
            return []
            
        words = list(jieba.cut_for_search(query))
        search_query = " ".join(words)
        
        results = []
        with self.ix.searcher() as searcher:
            parser = QueryParser("content", self.ix.schema)
            try:
                q = parser.parse(search_query)
            except Exception:
                q = parser.parse(query)
                
            hits = searcher.search(q, limit=top_k)
            for hit in hits:
                chunk_data = dict(hit.fields())
                if "chunk_id" in chunk_data and "id" not in chunk_data:
                    chunk_data["id"] = chunk_data.pop("chunk_id")
                chunk_data["bm25_score"] = hit.score
                results.append(chunk_data)
                
        return results
