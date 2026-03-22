# 台灣法律 RAG MCP 系統 (Taiwan Law RAG MCP)

這是一個專為台灣法律設計的 RAG (Retrieval-Augmented Generation) 系統，提供 MCP Server 介面，可與 Claude Desktop 直接整合。

---

## 系統架構

```
Claude Desktop
     │  MCP Protocol
     ▼
MCP Server (mcp-server/, TypeScript)
     │  HTTP
     ▼
Python RAG 引擎 (python-rag/, FastAPI)
     │
     ├── Embedding Provider  ──► 將查詢文字轉為向量
     ├── Reranking Provider  ──► 對搜尋結果重新排序
     └── HybridRetriever     ──► FAISS 向量搜尋 + BM25 關鍵字搜尋
```

---

## 快速開始

### 步驟 1：安裝環境

```bash
pip install uv          # 若尚未安裝 uv
uv sync                 # 安裝 Python 依賴

cd mcp-server
npm install
npm run build
cd ..
```

### 步驟 2：選擇 Provider 並設定

複製設定範本：

```bash
cp .env.example .env
```

**有 GPU（本地模式，不需要任何 API 金鑰）**

`.env` 保持預設即可，什麼都不用改：
```
EMBEDDING_PROVIDER=local
RERANKING_PROVIDER=local
```

系統會自動偵測 GPU VRAM：
- VRAM ≥ 9GB → 載入 Qwen3-Embedding-4B（2560 維）
- VRAM < 9GB → 自動降級為 Qwen3-Embedding-0.6B（1024 維）

**沒有 GPU（線上模式）**

在 `.env` 填入 Provider 類型和 API 金鑰：

```
EMBEDDING_PROVIDER=openai
RERANKING_PROVIDER=cohere
PROVIDER_API_KEY=你的金鑰
```

換成 Cohere 只需改前兩行，金鑰那行不動：

```
EMBEDDING_PROVIDER=cohere
RERANKING_PROVIDER=cohere
PROVIDER_API_KEY=你的金鑰
```

向量維度由系統自動決定，不需要手動設定。

### 步驟 3：建立索引

**首次使用，或切換 Embedding Provider 之後，必須重新執行：**

```bash
uv run scripts/build_index.py
```

這會讀取 `data/ChLaw.json/` 的法律資料並建立向量索引，需要一段時間。

> 使用線上 Embedding Provider 時，建立索引會呼叫線上 API，會產生費用。

### 步驟 4：啟動 Python RAG 服務

**每次使用前都需要啟動，MCP Server 透過 HTTP 連接這個服務：**

```bash
uv run python-rag/main.py
```

確認服務正常（另開一個 terminal）：

```bash
curl http://localhost:8000/health
```

回應中會顯示目前使用的 Provider：
```json
{
  "status": "ok",
  "embedding_provider": "local:Qwen3-Embedding-4B",
  "reranking_provider": "local:Qwen3-Reranker-4B"
}
```

### 步驟 5：設定 Claude Desktop

設定檔位於 `%APPDATA%\Claude\claude_desktop_config.json`，加入：

```json
{
  "mcpServers": {
    "taiwan-law": {
      "command": "node",
      "args": [
        "C:\\你的路徑\\taiwan-law-rag-mcp\\mcp-server\\dist\\index.js"
      ],
      "env": {
        "RAG_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

重啟 Claude Desktop 後，即可在對話中直接查詢台灣法律。

---

## Provider 選項

### Embedding Provider（`EMBEDDING_PROVIDER`）

| 值 | 說明 | 需要 GPU | 需要金鑰 |
|---|---|---|---|
| `local`（預設） | 本地 Qwen3 模型，自動依 VRAM 選擇 4B 或 0.6B | 是 | 否 |
| `openai` | OpenAI Embeddings | 否 | `PROVIDER_API_KEY` |
| `cohere` | Cohere Embeddings | 否 | `PROVIDER_API_KEY` |
| `huggingface` | HuggingFace Embeddings（本機推論） | 否 | 否 |
| `google` | Google Generative AI Embeddings | 否 | `PROVIDER_API_KEY` |
| `mistral` | Mistral AI Embeddings | 否 | `PROVIDER_API_KEY` |
| `voyageai` | Voyage AI Embeddings | 否 | `PROVIDER_API_KEY` |
| `bedrock` | AWS Bedrock Embeddings | 否 | AWS 憑證 |
| `azure-openai` | Azure OpenAI Embeddings | 否 | `PROVIDER_API_KEY` |

任何 LangChain 支援的 Embeddings class 都能用，透過 `ProviderConfig(extra={"langchain_class": "module.ClassName"})` 指定。

### Reranking Provider（`RERANKING_PROVIDER`）

| 值 | 說明 | 需要 GPU | 需要金鑰 |
|---|---|---|---|
| `local`（預設） | 本地 Qwen3-Reranker-4B | 是 | 否 |
| `cohere` | Cohere Rerank API | 否 | `PROVIDER_API_KEY` |
| `voyageai` | Voyage AI Rerank | 否 | `PROVIDER_API_KEY` |
| `flashrank` | FlashRank（本機輕量 reranker） | 否 | 否 |

### 選填設定

```
EMBEDDING_MODEL_NAME=   # 覆寫 embedding 模型，例如 text-embedding-3-large
RERANKING_MODEL_NAME=   # 覆寫 reranking 模型
EMBEDDING_BATCH_SIZE=   # 批次大小，預設 100
```

> 向下相容：若你已有 `OPENAI_API_KEY` / `COHERE_API_KEY` 等舊格式的環境變數，不設定 `PROVIDER_API_KEY` 也能正常運作。

---

## 切換 Provider 的注意事項

切換 Embedding Provider 時，向量維度會改變，**必須重新建立索引**，否則啟動時會報錯。

| Provider | 預設模型 | 向量維度 |
|---|---|---|
| `local` | Qwen3-Embedding-4B | 2560 |
| `local`（VRAM 不足） | Qwen3-Embedding-0.6B | 1024 |
| `openai` | text-embedding-3-small | 1536 |
| `openai` + `EMBEDDING_MODEL_NAME=text-embedding-3-large` | text-embedding-3-large | 3072 |
| `cohere` | embed-multilingual-v3.0 | 1024 |

---

## 測試

```bash
cd python-rag
uv run python -m pytest tests/ -v
```
