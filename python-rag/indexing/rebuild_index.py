import os
import sys
import json
import argparse
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

# 將專案根目錄加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from indexing.faiss_indexer import FaissIndexer
from indexing.bm25_indexer import BM25Indexer


def load_chunks(chunks_file: str, limit: int = None):
    print(f"Loading chunks from {chunks_file}...")
    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    print(f"Found {len(chunks)} chunks.")

    if limit:
        print(f"Applying test limit: {limit} chunks")
        chunks = chunks[:limit]

    return chunks


def format_chunk_text(chunk: dict) -> str:
    """格式化 chunk 文字，包含 metadata"""
    meta = chunk.get("metadata", {})
    law_name = meta.get("law_name", "未知法律")
    article_no = meta.get("article_no", "未知條號")
    content = chunk.get("content", "")
    chapter = meta.get("chapter", "")
    chapter_str = f"章節: {chapter}\n" if chapter else ""
    return f"法律: {law_name}\n{chapter_str}條號: {article_no}\n內容: {content}"


def embed_chunks_with_provider(embedding_provider, chunks: list, output_dir: str, batch_size: int = 100):
    """使用 EmbeddingProvider 批次 embed chunks，並儲存結果"""
    print(f"Pre-processing {len(chunks)} chunks...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        texts = list(executor.map(format_chunk_text, chunks))

    chunk_ids = [c["id"] for c in chunks]

    print(f"Start embedding {len(texts)} chunks...")
    # local provider 內部已有 batch_size / VRAM 自動管理，直接傳全部
    # langchain provider 則透過 batch_size 分批呼叫 API
    from providers.local_providers import LocalEmbeddingProvider
    if isinstance(embedding_provider, LocalEmbeddingProvider):
        all_embeddings = embedding_provider.embed_documents(texts)
    else:
        all_embeddings: list[np.ndarray] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            vecs = embedding_provider.embed_documents(batch)
            all_embeddings.extend(vecs)
            print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)}", end="\r")
        print()
    embeddings = np.stack(all_embeddings).astype(np.float32)

    os.makedirs(output_dir, exist_ok=True)

    emb_path = os.path.join(output_dir, "embeddings.npy")
    np.save(emb_path, embeddings)
    print(f"Saved embeddings to {emb_path} (shape: {embeddings.shape})")

    ids_path = os.path.join(output_dir, "chunk_ids.json")
    with open(ids_path, 'w', encoding='utf-8') as f:
        json.dump(chunk_ids, f, ensure_ascii=False, indent=2)
    print(f"Saved chunk IDs to {ids_path}")

    return embeddings, chunk_ids


def main():
    parser = argparse.ArgumentParser(description="Rebuild indices for Taiwan Law RAG")
    parser.add_argument("--chunks-file", type=str, default="../data/chunks.json", help="Path to chunks JSON file")
    parser.add_argument("--output-dir", type=str, default="../data", help="Output directory for indices")
    parser.add_argument("--test-limit", type=int, default=None, help="Limit number of chunks for testing")
    parser.add_argument("--batch-size", type=int, default=None, help="Batch size for embedding（不指定則使用 EMBEDDING_BATCH_SIZE 或預設值）")
    parser.add_argument("--force", action="store_true", help="Force rebuild (overwrite existing)")
    parser.add_argument("--dict-path", type=str, default=None, help="Custom dict path for jieba")

    args = parser.parse_args()

    chunks_file_path = os.path.abspath(args.chunks_file)
    output_dir_path = os.path.abspath(args.output_dir)

    if not os.path.exists(chunks_file_path):
        print(f"Error: {chunks_file_path} not found. Please run data processing first (Phase 2).")
        return

    print("=" * 50)
    print("🚀 Starting Index Rebuild Process")
    print("=" * 50)

    # 顯示目前使用的 Provider 設定
    embedding_provider_type = os.environ.get("EMBEDDING_PROVIDER", "local")
    embedding_model = os.environ.get("EMBEDDING_MODEL_NAME", "(預設)")
    print(f"EMBEDDING_PROVIDER = {embedding_provider_type}")
    print(f"EMBEDDING_MODEL_NAME = {embedding_model}")

    # 1. 載入 chunks
    t0 = time.time()
    chunks = load_chunks(chunks_file_path, args.test_limit)

    # 2. 建立 EmbeddingProvider（透過 ProviderFactory 讀取 .env）
    t1 = time.time()
    print("\n[Step 1/3] Initializing Embedding Provider...")
    from providers.factory import ProviderFactory
    # 只需要 embedding provider，不初始化 reranker（避免載入大型本地模型）
    from providers.config import ProviderConfig
    embedding_provider_type = os.environ.get("EMBEDDING_PROVIDER", "local")
    embedding_config = ProviderConfig(
        provider_type=embedding_provider_type,
        model_name=os.environ.get("EMBEDDING_MODEL_NAME"),
        api_key=os.environ.get("PROVIDER_API_KEY") or os.environ.get("OPENAI_API_KEY"),
    )
    embedding_provider = ProviderFactory.create_embedding_provider(embedding_config)

    # batch_size：CLI 參數 > 環境變數 > 預設 100
    batch_size = args.batch_size or int(os.environ.get("EMBEDDING_BATCH_SIZE", "100"))

    # 3. 產生 embeddings
    print("\n[Step 2/3] Generating Embeddings...")
    embeddings, chunk_ids = embed_chunks_with_provider(
        embedding_provider, chunks, output_dir_path, batch_size=batch_size
    )
    print(f"Embedding completed in {time.time()-t1:.2f}s")

    # 4. 建立 FAISS 索引
    t2 = time.time()
    print("\n[Step 3/3] Building FAISS Index...")
    dimension = embeddings.shape[1] if len(embeddings.shape) > 1 else 4096

    nlist = 100
    if args.test_limit and args.test_limit < nlist * 39:
        nlist = max(1, args.test_limit // 40)
        print(f"Adjusted FAISS nlist to {nlist} due to small sample size.")

    faiss_indexer = FaissIndexer(dimension=dimension, nlist=nlist)
    faiss_indexer.build_index(embeddings, chunks, output_dir=output_dir_path)
    print(f"FAISS index built in {time.time()-t2:.2f}s")

    # 5. 建立 BM25 索引
    t3 = time.time()
    print("\n[Step 4/4] Building BM25 Index...")
    bm25_dir = os.path.join(output_dir_path, "bm25_index")
    bm25_indexer = BM25Indexer(index_dir=bm25_dir, custom_dict_path=args.dict_path)
    bm25_indexer.build_index(chunks)
    print(f"BM25 index built in {time.time()-t3:.2f}s")

    print("=" * 50)
    print(f"✨ All indices rebuilt successfully in {time.time()-t0:.2f}s total!")
    print(f"Output directory: {output_dir_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()
