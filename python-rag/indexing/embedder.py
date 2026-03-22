import os
import json
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any

class Embedder:
    """
    使用 Qwen3-Embedding-4B 進行向量化
    """
    def __init__(self, model_name: str = "Qwen/Qwen3-Embedding-4B", batch_size: int = 256):
        self.model_name = model_name
        self.batch_size = batch_size
        
        # 自動判斷是否有 GPU
        if torch.cuda.is_available():
            self.device = 'cuda'
        elif torch.backends.mps.is_available():
            self.device = 'mps'
        else:
            self.device = 'cpu'
            
        print(f"[{self.__class__.__name__}] Loading model {model_name} on {self.device}...")
        self.model = SentenceTransformer(model_name, device=self.device,model_kwargs={"torch_dtype": "float16"})

    def embed_query(self, query: str) -> np.ndarray:
        """
        將單一查詢文本轉換為向量
        """
        embedding = self.model.encode(
            [query],
            show_progress_bar=False,
            normalize_embeddings=True
        )
        return embedding[0]

    def format_text(self, chunk: Dict[str, Any]) -> str:
        """
        格式化文本以包含 metadata (法律名稱、條號、章節、內容)
        """
        meta = chunk.get("metadata", {})
        law_name = meta.get("law_name", "未知法律")
        article_no = meta.get("article_no", "未知條號")
        content = chunk.get("content", "")
        
        chapter = meta.get("chapter", "")
        chapter_str = f"章節: {chapter}\n" if chapter else ""
        
        return f"法律: {law_name}\n{chapter_str}條號: {article_no}\n內容: {content}"

    def embed_chunks(self, chunks: List[Dict[str, Any]], output_dir: str = "data"):
        """
        批次將 chunks 轉換為向量並保存至 output_dir 中
        """
        texts = [self.format_text(c) for c in chunks]
        chunk_ids = [c["id"] for c in chunks]

        print(f"[{self.__class__.__name__}] Start embedding {len(texts)} chunks with batch size {self.batch_size}...")
        
        # 進行向量化，包含進度條與正規化
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
            device=self.device,
            convert_to_numpy=True
        )

        os.makedirs(output_dir, exist_ok=True)
        
        # 保存 embeddings.npy
        emb_path = os.path.join(output_dir, "embeddings.npy")
        np.save(emb_path, embeddings)
        print(f"[{self.__class__.__name__}] Saved embeddings to {emb_path} (shape: {embeddings.shape})")

        # 保存 chunk_ids.json
        ids_path = os.path.join(output_dir, "chunk_ids.json")
        with open(ids_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_ids, f, ensure_ascii=False, indent=2)
            
        print(f"[{self.__class__.__name__}] Saved chunk IDs to {ids_path}")
        
        return embeddings, chunk_ids
