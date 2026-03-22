import os
import sys
import json
import argparse
import time

# 將專案根目錄加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indexing.embedder import Embedder
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

def extract_dimension(embeddings):
    """取得 embeddings 維度"""
    if len(embeddings.shape) > 1:
        return embeddings.shape[1]
    return 4096

def main():
    parser = argparse.ArgumentParser(description="Rebuild indices for Taiwan Law RAG")
    parser.add_argument("--chunks-file", type=str, default="../data/chunks.json", help="Path to chunks JSON file")
    parser.add_argument("--output-dir", type=str, default="../data", help="Output directory for indices")
    parser.add_argument("--test-limit", type=int, default=None, help="Limit number of chunks for testing")
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size for embedding")
    parser.add_argument("--force", action="store_true", help="Force rebuild (overwrite existing)")
    parser.add_argument("--model-name", type=str, default="Qwen/Qwen3-Embedding-4B", help="Model name for sentence-transformers")
    parser.add_argument("--dict-path", type=str, default=None, help="Custom dict path for jieba")
    
    args = parser.parse_args()
    
    # 解析路徑為絕對路徑，方便從任意地方執行
    chunks_file_path = os.path.abspath(args.chunks_file)
    output_dir_path = os.path.abspath(args.output_dir)
    
    if not os.path.exists(chunks_file_path):
        print(f"Error: {chunks_file_path} not found. Please run data processing first (Phase 2).")
        return

    print("=" * 50)
    print("🚀 Starting Index Rebuild Process (Phase 3)")
    print("=" * 50)

    # 1. 載入 chunks
    t0 = time.time()
    chunks = load_chunks(chunks_file_path, args.test_limit)
    
    # 2. 建立向量索引 (Embedder)
    t1 = time.time()
    print("\n[Step 1/3] Generating Embeddings...")
    embedder = Embedder(model_name=args.model_name, batch_size=args.batch_size)
    embeddings, chunk_ids = embedder.embed_chunks(chunks, output_dir=output_dir_path)
    print(f"Embedding completed in {time.time()-t1:.2f}s")
    
    # 3. 建立 FAISS 索引
    t2 = time.time()
    print("\n[Step 2/3] Building FAISS Index...")
    dimension = extract_dimension(embeddings)
    
    # IVFPQ 訓練時 nlist 如果設定大於訓練筆數會報錯，如果是測試模式需相應調降 nlist
    nlist = 100
    if args.test_limit and args.test_limit < nlist * 39:
        nlist = max(1, args.test_limit // 40)
        print(f"Adjusted FAISS nlist to {nlist} due to small sample size.")
        
    faiss_indexer = FaissIndexer(dimension=dimension, nlist=nlist)
    faiss_indexer.build_index(embeddings, chunks, output_dir=output_dir_path)
    print(f"FAISS index built in {time.time()-t2:.2f}s")
    
    # 4. 建立 BM25 索引
    t3 = time.time()
    print("\n[Step 3/3] Building BM25 Index...")
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
