import os
import pickle
import numpy as np
from typing import List, Dict, Any

try:
    import faiss
except ImportError:
    faiss = None

class VectorRetriever:
    """
    FAISS 向量檢索
    1. 載入 FAISS 索引 (taiwan_law.faiss)
    2. 載入 chunk metadata (chunks.pkl)
    3. 接收 query 向量，進行近鄰搜尋
    """
    
    def __init__(self, index_path: str = "data/taiwan_law.faiss", meta_path: str = "data/chunks.pkl"):
        self.index_path = index_path
        self.meta_path = meta_path
        self.index = None
        self.chunks = []
        self._load_index()

    def _load_index(self):
        if faiss is None:
            print("Warning: faiss is not installed.")
            return

        full_index_path = os.path.abspath(self.index_path)
        if os.path.exists(full_index_path):
            self.index = faiss.read_index(full_index_path)
        else:
            print(f"Index not found at {full_index_path}")
            
        full_meta_path = os.path.abspath(self.meta_path)
        if os.path.exists(full_meta_path):
            with open(full_meta_path, 'rb') as f:
                self.chunks = pickle.load(f)
        else:
            print(f"Metadata not found at {full_meta_path}")

    def search(self, query_vector: np.ndarray, top_k: int = 30) -> List[Dict[str, Any]]:
        if self.index is None or len(self.chunks) == 0:
            return []
            
        if len(query_vector.shape) == 1:
            query_vector = np.expand_dims(query_vector, axis=0)
            
        query_vector = query_vector.astype('float32')
        
        distances, indices = self.index.search(query_vector, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1: 
                continue
            if idx < len(self.chunks):
                chunk = self.chunks[idx].copy()
                meta = chunk.get("metadata", {})
                for k, v in meta.items():
                    if k not in chunk:
                        chunk[k] = v
                chunk["vector_score"] = float(distances[0][i])
                results.append(chunk)
                
        return results
