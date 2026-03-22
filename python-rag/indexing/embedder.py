import os
import json
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional

class Embedder:
    """
    使用 Qwen3-Embedding-4B 進行向量化
    """
    def __init__(self, model_name: str = "Qwen/Qwen3-Embedding-4B", batch_size: Optional[int] = None):
        self.model_name = model_name

        if torch.cuda.is_available():
            self.device = 'cuda'
        elif torch.backends.mps.is_available():
            self.device = 'mps'
        else:
            self.device = 'cpu'

        print(f"[{self.__class__.__name__}] Loading model {model_name} on {self.device}...")

        # 先用 CPU 載入再移到 GPU，避免直接在 GPU 上載入 float32 爆 VRAM
        self.model = SentenceTransformer(model_name, device='cpu')

        if self.device == 'cuda':
            self.model.half()  # 先轉 fp16
            self.model.to('cuda')  # 再移到 GPU
            print(f"[{self.__class__.__name__}] Model converted to fp16 and moved to GPU")
            used_gb = torch.cuda.memory_allocated() / 1e9
            print(f"[{self.__class__.__name__}] Model VRAM usage: {used_gb:.1f} GB")

        # 模型載入後才計算 batch size
        self.batch_size = batch_size or self._auto_batch_size()
        print(f"[{self.__class__.__name__}] Using batch size: {self.batch_size}")

    def _auto_batch_size(self) -> int:
        if self.device != 'cuda':
            return 8

        total_vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        allocated_gb = torch.cuda.memory_allocated() / 1e9
        # 保留 1GB 緩衝
        remaining_gb = total_vram_gb * 0.85 - allocated_gb - 1.0

        print(f"[{self.__class__.__name__}] VRAM total: {total_vram_gb:.1f} GB, model used: {allocated_gb:.1f} GB, remaining: {remaining_gb:.1f} GB")

        if remaining_gb <= 0:
            print(f"[{self.__class__.__name__}] Warning: insufficient VRAM, falling back to CPU")
            self.device = 'cpu'
            self.model.to('cpu')
            return 8

        per_batch_gb = 0.3
        batch_size = max(8, int(remaining_gb / per_batch_gb) * 8)
        batch_size = min(batch_size, 256)

        return batch_size

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

    def embed_chunks(self, chunks, output_dir: str = "data"):
        print(f"[{self.__class__.__name__}] Pre-processing {len(chunks)} chunks...")
        
        # 預先處理所有文字（利用多執行緒加速）
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as executor:
            texts = list(executor.map(self.format_text, chunks))
    
        chunk_ids = [c["id"] for c in chunks]
    
        print(f"[{self.__class__.__name__}] Start embedding {len(texts)} chunks with batch size {self.batch_size}...")
        
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
            device=self.device,
            convert_to_numpy=True,
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
