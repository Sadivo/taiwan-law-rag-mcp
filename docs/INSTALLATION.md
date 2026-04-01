# 安裝指南

本文件說明如何從零開始安裝並啟動 Taiwan Law RAG 系統。

---

## 前置需求

請確認以下工具已安裝於你的系統：

| 工具 | 版本需求 | 說明 |
|---|---|---|
| Python | 3.11+ | 後端執行環境 |
| [uv](https://docs.astral.sh/uv/) | 最新版 | Python 套件與虛擬環境管理 |
| [Ollama](https://ollama.com/) | 最新版 | 若使用本地 LLM（`GENERATION_PROVIDER=ollama`）才需要 |

安裝 `uv`：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安裝 Ollama（僅在使用本地 LLM 時需要）：

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# 下載預設模型
ollama pull qwen3:8b
```

---

## 取得原始碼

```bash
git clone <repository-url>
cd taiwan-law-rag
```

---

## 建立虛擬環境

```bash
# 建立虛擬環境
uv venv

# 安裝所有依賴套件
uv sync
```

---

## 設定 `.env`

複製範本並依需求填寫：

```bash
cp .env.example .env
```

以下依不同使用情境提供設定範例。

### Embedding Provider 設定範例

#### `local`（不需要 API 金鑰）

使用本機模型，無需任何 API 金鑰，適合離線或隱私敏感場景。

```env
EMBEDDING_PROVIDER=local
RERANKING_PROVIDER=local
PROVIDER_API_KEY=
```

#### `openai`

```env
EMBEDDING_PROVIDER=openai
RERANKING_PROVIDER=local
PROVIDER_API_KEY=sk-...
EMBEDDING_MODEL_NAME=text-embedding-3-small
```

#### `cohere`

```env
EMBEDDING_PROVIDER=cohere
RERANKING_PROVIDER=cohere
PROVIDER_API_KEY=<your-cohere-api-key>
```

#### `voyageai`

```env
EMBEDDING_PROVIDER=voyageai
RERANKING_PROVIDER=voyageai
PROVIDER_API_KEY=pa-...
```

> 若 Embedding 與 Reranking 使用不同 provider，可分別設定 `EMBEDDING_API_KEY` 與 `RERANKING_API_KEY`，優先順序高於 `PROVIDER_API_KEY`。

---

### Generation Provider 設定範例

#### `ollama`（不需要 API 金鑰）

使用本機 Ollama 服務，無需 API 金鑰。

```env
GENERATION_PROVIDER=ollama
GENERATION_MODEL_NAME=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434
GENERATION_API_KEY=
```

#### `openai`

```env
GENERATION_PROVIDER=openai
GENERATION_API_KEY=sk-...
GENERATION_MODEL_NAME=gpt-4o-mini
```

#### `anthropic`

```env
GENERATION_PROVIDER=anthropic
GENERATION_API_KEY=sk-ant-...
GENERATION_MODEL_NAME=claude-3-5-haiku-20241022
```

---

### 使用 `local` Provider（完全免 API 金鑰）

若 `EMBEDDING_PROVIDER=local` 且 `GENERATION_PROVIDER=ollama`，**不需要填寫任何 API 金鑰**即可啟動完整服務。最小化設定如下：

```env
EMBEDDING_PROVIDER=local
RERANKING_PROVIDER=local
GENERATION_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
API_HOST=127.0.0.1
API_PORT=8073
```

---

### 完整 `.env` 欄位說明

| 變數 | 預設值 | 說明 |
|---|---|---|
| `EMBEDDING_PROVIDER` | `local` | Embedding 後端：`local` \| `openai` \| `cohere` \| `voyageai` |
| `RERANKING_PROVIDER` | `local` | Reranking 後端：`local` \| `voyageai` \| `cohere` \| `flashrank` |
| `PROVIDER_API_KEY` | （空） | Embedding / Reranking 共用 API 金鑰 |
| `EMBEDDING_API_KEY` | （空） | Embedding 專用 API 金鑰（優先於 `PROVIDER_API_KEY`） |
| `RERANKING_API_KEY` | （空） | Reranking 專用 API 金鑰（優先於 `PROVIDER_API_KEY`） |
| `EMBEDDING_MODEL_NAME` | （provider 預設） | 覆寫 Embedding 模型名稱 |
| `RERANKING_MODEL_NAME` | （provider 預設） | 覆寫 Reranking 模型名稱 |
| `GENERATION_PROVIDER` | `ollama` | Generation 後端：`ollama` \| `openai` \| `anthropic` |
| `GENERATION_API_KEY` | （空） | Generation API 金鑰（openai / anthropic 需要） |
| `GENERATION_MODEL_NAME` | （provider 預設） | 覆寫 Generation 模型名稱 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服務位址 |
| `API_HOST` | `127.0.0.1` | FastAPI 監聽位址 |
| `API_PORT` | `8073` | FastAPI 監聽埠號 |

---

## 啟動服務

```bash
# 方式一：使用根目錄統一入口（推薦）
uv run main.py serve

# 方式二：直接啟動 FastAPI
uv run python-rag/main.py
```

服務啟動後會輸出各 provider 狀態摘要，例如：

```
Taiwan Law RAG — http://127.0.0.1:8073
  ✓ Embedding  : local:bge-m3
  ✓ Reranking  : local:bge-reranker
  ✓ Generation : ollama:qwen3:8b
```

若 Generation provider 無法連線，服務仍會正常啟動，但問答功能將不可用：

```
Taiwan Law RAG — http://127.0.0.1:8073
  ✓ Embedding  : local:bge-m3
  ✓ Reranking  : local:bge-reranker
  ✗ Generation : ollama:qwen3:8b (unreachable at http://localhost:11434)
```

---

## 驗證安裝

服務啟動後，執行以下指令確認服務正常運作：

```bash
curl http://127.0.0.1:8073/health
```

預期回應（HTTP 200）：

```json
{
  "status": "ok",
  "embedding_provider": "local:bge-m3",
  "reranking_provider": "local:bge-reranker",
  "generation_provider": {
    "name": "ollama:qwen3:8b",
    "status": "ok"
  }
}
```

`status` 欄位說明：

| 值 | 含義 |
|---|---|
| `ok` | 所有 provider 正常 |
| `degraded` | Generation provider 無法連線，搜尋功能仍可用 |
| `error` | Embedding 或 Reranking 初始化失敗，服務無法正常運作 |

---

## 常見問題

**Q：啟動時出現 `ModuleNotFoundError`**

確認已執行 `uv sync` 安裝所有依賴。

**Q：Generation provider 顯示 `unreachable`**

若使用 `ollama`，確認 Ollama 服務已啟動：

```bash
ollama serve
```

**Q：想快速驗證環境設定是否正確**

```bash
uv run main.py check
```

此指令會檢查所有 provider 連線狀態，不啟動 FastAPI 服務。
