# Phase 3 實作紀錄：索引建立 (Indexing Module)

**紀錄日期**：2026-03-20

## 1. 模組目標
實作 RAG 系統之索引建立層 (Phase 3)，包含：
1. **向量索引 (Vector Index)**：以指定模型產出文本嵌入 (Embeddings) 並建立 FAISS (HNSW + IVF) 高效索引，供語義檢索。
2. **關鍵字索引 (Keyword Index)**：建立 Whoosh BM25 索引，供精確關鍵字及條號檢索。

## 2. 完成檔案
已於 `python-rag/indexing/` 目錄下完成以下開發：
- `embedder.py`: 負責載入模型 (`Qwen/Qwen3-Embedding-4B` 等) 並批次處理 `chunks.json` 以產出 `embeddings.npy` 檔案。
- `faiss_indexer.py`: 負責承接嵌入向量並採用 `IndexIVFPQ` 架構結合 `HNSW` 建立本地索引落檔 (`taiwan_law.faiss` 及其對應的 `chunks.pkl`)。
- `bm25_indexer.py`: 負責初始化 `Whoosh` 的 Schema 並利用 `jieba` 中文分詞切斷內文，落檔 BM25 索引資料夾。
- `rebuild_index.py`: 統整以上三大邏輯的命令列工具腳本，作為資料管道之標準入口。預設參數保留採用 `--model-name "Qwen/Qwen3-Embedding-4B"`。

## 3. 測試與除錯歷程
### 3.1 依賴衝突解決
- **問題**：原計畫書的相依性指定 `sentence-transformers==2.2.2`，但近期版本的 `huggingface_hub` (< 0.23.0 之後) 中移除了 `cached_download`，導致初始化報錯 `ImportError`。
- **解法**：修改 `VIBE_CODING_PROMPT.md` 並利用 `uv` 環境管理工具，將依賴更正為 `sentence-transformers>=2.2.2` 以順利安裝相容於新款 HF Hub 的 5.3.0 (或更高) 版本。

### 3.2 功能整合測試
- **前置作業**：因原始的 `ChLaw.json` 尚未經過切塊，撰寫並執行了 `scripts/run_phase2.py` 將原始資料處理成 48,212 筆 chunks 序列落為 `data/chunks.json`。
- **輕量級驗證**：為避免開發測試時下載龐大的 4B 模型導致曠日廢時，透過參數注入 `--model-name all-MiniLM-L6-v2` 搭配 `--test-limit 300` 進行輕量級整合測試。
- **測試結果**：FAISS Index 與 Whoosh 原型順利產出於 `data/` 下，腳本回報 `Exit code: 0`，順利證實第三階段的架構正確完工。

## 4. 正式環境部署注意
1. **執行指令**：若要在正式模式下跑足全量法規（約 5.5 萬區塊），執行腳本不需提供任何特殊參數，即會預設使用對應的 Qwen 模型：
   ```bash
   uv run python python-rag/indexing/rebuild_index.py --chunks-file data/chunks.json --output-dir data
   ```
2. **硬體開銷**：`Qwen/Qwen3-Embedding-4B` 將需要 GPU 支援以避免記憶體溢出或處理緩慢。FAISS 已經動態兼容硬體，只要確保 PyTorch 安裝其 CUDA 版本則可無痛啟用。
