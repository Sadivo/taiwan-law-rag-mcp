import os
import pickle
import numpy as np
import faiss
from typing import List, Dict, Any

class FaissIndexer:
    """
    FAISS 索引建立 (高性能向量檢索)
    使用 HNSW + IVF (IndexIVFPQ) 混合索引
    """
    def __init__(self, dimension: int = 4096, nlist: int = 100, m: int = 32, nbits: int = 8):
        self.dimension = dimension
        self.nlist = nlist
        self.m = m
        self.nbits = nbits
        
        print(f"[{self.__class__.__name__}] Initializing FAISS IndexIVFPQ with HNSW quantizer...")
        # 建立 quantizer (HNSW 演算法)
        self.quantizer = faiss.IndexHNSWFlat(dimension, m)
        
        # 建立 IVFPQ 索引，預設使用 Inner Product 來符合我們正規化後的向量相似度計算
        self.index = faiss.IndexIVFPQ(
            self.quantizer, 
            dimension, 
            nlist, 
            m, 
            nbits, 
            faiss.METRIC_INNER_PRODUCT
        )

    def build_index(self, embeddings: np.ndarray, chunks: List[Dict[str, Any]], output_dir: str = "data"):
        """
        訓練並建立 FAISS 索引，將其連同 chunks 存為檔案
        """
        assert embeddings.shape[1] == self.dimension, f"Dimension mismatch: expected {self.dimension}, got {embeddings.shape[1]}"
        
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)

        # 訓練 IVFPQ 索引所需的量化器
        print(f"[{self.__class__.__name__}] Training faiss index with {embeddings.shape[0]} vectors...")
        self.index.train(embeddings)
        
        # 將向量加入索引
        print(f"[{self.__class__.__name__}] Adding vectors to index...")
        self.index.add(embeddings)
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 備份索引檔 taiwan_law.faiss
        index_path = os.path.join(output_dir, "taiwan_law.faiss")
        faiss.write_index(self.index, index_path)
        print(f"[{self.__class__.__name__}] Saved FAISS index to {index_path}")

        # 保存 chunk metadata (chunks.pkl) 以供比對使用
        chunks_path = os.path.join(output_dir, "chunks.pkl")
        with open(chunks_path, 'wb') as f:
            pickle.dump(chunks, f)
            
        print(f"[{self.__class__.__name__}] Saved chunk metadata to {chunks_path}")
        
        return self.index
