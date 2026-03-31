# 台灣法律 RAG MCP 系統 (Taiwan Law RAG MCP)

個人練習用的 RAG（Retrieval-Augmented Generation）專案，以地端 Qwen3 模型為核心，結合 FAISS 向量搜尋與 BM25 混合檢索，透過 MCP 協定讓 Claude 直接查詢台灣 48,000+ 條法律條文。

---

## 為什麼做這個？我怎麼做？

台灣法律資料涵蓋 1,300+ 部法律、48,000+ 條條文，資料量龐大無法直接餵給 AI。碰巧身邊有人遇到惡質加盟商糾紛，有感而發，決定以此為練習主題——用 RAG 技術讓 AI 助理真正能夠查詢台灣法律條文，並以地端運算為核心設計目標，確保隱私性與零 API 成本。

查詢分兩種情境：
- 知道條號（「勞基法第38條」）→ 直接精確比對
- 只知道情境（「加班費怎麼算」）→ 向量搜尋（FAISS） + BM25 關鍵字搜尋，各取Top-30 →  RRF 融合兩份結果 →  Reranker 重排取Top-20 → 去除重複法律 → 回傳 Top-10

模型選擇上原本想全用本地Qwen3模型，但礙於電腦GPU太爛embedding要跑好幾天...所以少量測試能跑後，就改為可切換成線上模型的彈性版本。

整個專案90%是AI生成，大概花了3天完成，大致設計流程：找成熟的github專案參考架構 -> gemini 討論可行性 -> claude產生MVP規格書 -> antigravity gemini 生成MVP -> kiro IDE 擴充功能+優化

---

## 系統架構

```
Claude Desktop / 任何 HTTP Client / 你的 App
     │  MCP Protocol          │  HTTP
     ▼                        ▼
MCP Server              POST /chat
(mcp-server/, TypeScript)    │
     │  HTTP                  │
     ▼                        ▼
Python RAG 引擎 (python-rag/, FastAPI)
     │
     ├── Embedding Provider  ──► 將查詢文字轉為向量
     ├── Reranking Provider  ──► 對搜尋結果重新排序
     ├── HybridRetriever     ──► FAISS 向量搜尋 + BM25 關鍵字搜尋
     └── GenerationProvider  ──► LLM 生成有引用來源的回答（Ollama / OpenAI / Anthropic）
```

---

## 快速開始

### 步驟 1：安裝環境

```bash
scripts\setup.bat
```

> 沒有 `uv`？先安裝：https://docs.astral.sh/uv/getting-started/installation/

### 步驟 2：設定 Provider

編輯 `.env`（`setup.bat` 已自動建立）：

**有 GPU（本地模式，不需要 API 金鑰）**

預設值即可，不用改任何東西。系統會自動偵測 VRAM：
- VRAM ≥ 9GB → Qwen3-Embedding-4B
- VRAM < 9GB → 自動降級為 Qwen3-Embedding-0.6B

> 我的 RTX 3060 12GB 要跑一天多，給你們參考= =

**沒有 GPU（線上模式）**

參考[LangChain Docs](https://docs.langchain.com/oss/python/integrations/embeddings)

填入 Provider 類型與 API 金鑰。同一 provider 只需填 `PROVIDER_API_KEY`：

```env
EMBEDDING_PROVIDER=voyageai
RERANKING_PROVIDER=voyageai
PROVIDER_API_KEY=voyageai金鑰
```

混搭不同 provider 時，分別填入各自金鑰：

```env
EMBEDDING_PROVIDER=voyageai
RERANKING_PROVIDER=cohere
EMBEDDING_API_KEY=你的 VoyageAI 金鑰
RERANKING_API_KEY=你的 Cohere 金鑰
```

混搭 本地模型 與 線上模型：

```env
EMBEDDING_PROVIDER=voyageai
RERANKING_PROVIDER=local
EMBEDDING_API_KEY=你的 VoyageAI 金鑰
```

> 向量維度由系統自動決定，不需要手動設定。

**Generation Provider（LLM 問答）**

設定用於生成回答的 LLM，支援本地 Ollama 或線上 API：

```env
# 本地 Ollama（需先啟動 ollama serve）
GENERATION_PROVIDER=ollama
GENERATION_MODEL_NAME=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434

# 或使用 OpenAI
GENERATION_PROVIDER=openai
GENERATION_API_KEY=sk-...
GENERATION_MODEL_NAME=gpt-4o-mini

# 或使用 Anthropic
GENERATION_PROVIDER=anthropic
GENERATION_API_KEY=sk-ant-...
GENERATION_MODEL_NAME=claude-3-5-haiku-20241022
```

### 步驟 3：建立索引

**首次使用，或切換 Embedding Provider 之後，必須重新執行：**

```bash
uv run scripts/build_index.py
```

這會自動從官方 API 下載最新法律資料，接著建立向量索引，需要一段時間。

> 使用線上 Embedding Provider 時，建立索引會呼叫線上 API，會產生費用。

**常用選項：**

```bash
# 強制重新下載資料（即使已有資料）
uv run scripts/build_index.py --force-download

# 跳過下載，直接用現有資料建立索引
uv run scripts/build_index.py --skip-download

# 跳過資料處理，只重建向量索引
uv run scripts/build_index.py --skip-data
```

**手動更新資料（不重建索引）：**

```bash
# 有資料就檢查版本，有新版本會詢問是否更新
uv run scripts/download_data.py

# 強制重新下載，跳過確認
uv run scripts/download_data.py --force
```

更新時會自動比對新舊資料，輸出新增、刪除、修改的法律清單。

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

### 步驟 5：設定 Claude Desktop 或其他支援 MCP Server 的 AI tool

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
        "RAG_API_URL": "http://localhost:8073"
      }
    }
  }
}
```

重啟 Claude Desktop 後，即可在對話中直接查詢台灣法律。

---

## MCP 工具說明

共提供 6 個工具，Claude 會根據你的問題自動選擇適合的工具。

### 1. 語義搜尋（semantic_search）

根據問題描述，用 AI 向量相似度找出最相關的法條。適合不知道確切條號、只知道情境的查詢。

使用範例：
> 「員工被資遣，雇主需要給多少預告期？」
> 「房東可以隨意漲租金嗎？」
> 「公司董事的責任有哪些？」

### 2. 精確條文查詢（exact_search）

已知法律名稱與條號時，直接取得該條文。支援常見別名（勞基法、個資法等）。

使用範例：
> 「勞基法第38條」
> 「民法第184條」
> 「公司法第23條」

### 3. 法律名稱搜尋（search_law_by_name）

列出某部法律的所有條文。適合想瀏覽整部法律架構時使用。

使用範例：
> 「列出勞動基準法所有條文」
> 「性別平等工作法有哪些規定？」

### 4. 取得完整法律（get_law_full_text）

取得某部法律的完整全文，包含章節結構、所有條文與官方連結。

使用範例：
> 「給我消費者保護法的完整內容」
> 「個人資料保護法全文」

### 5. 法律比較（compare_laws）

比較多部法律在同一主題下的相關條文差異，適合需要跨法律分析的情境。

使用範例：
> 「比較民法和消費者保護法對於損害賠償的規定」
> 「勞動基準法和勞工退休金條例對退休金的規定有何不同？」

### 6. 法律問答（ask_law_question）

整合 retrieval + generation 的完整 RAG 問答。不只回傳條文，而是根據相關條文生成有引用來源的繁體中文回答。

使用範例：
> 「勞工特別休假有幾天？」
> 「被資遣時雇主需要給多少預告期？」
> 「房東可以隨意漲租金嗎？」

> 需要先設定 `GENERATION_PROVIDER` 並確保對應服務正常運行（Ollama 或線上 API）。

---

## Provider 選項

### Embedding Provider（`EMBEDDING_PROVIDER`）

| 值 | 說明 | 需要 GPU | 需要金鑰 |
|---|---|---|---|
| `local`（預設） | 本地 Qwen3 模型，自動依 VRAM 選擇 4B 或 0.6B | 是 | 否 |
| `openai` | OpenAI Embeddings | 否 | 是 |
| `cohere` | Cohere Embeddings | 否 | 是 |
| `huggingface` | HuggingFace Embeddings（本機推論） | 否 | 否 |
| `google` | Google Generative AI Embeddings | 否 | 是 |
| `mistral` | Mistral AI Embeddings | 否 | 是 |
| `voyageai` | Voyage AI Embeddings | 否 | 是 |
| `bedrock` | AWS Bedrock Embeddings | 否 | AWS 憑證 |
| `azure-openai` | Azure OpenAI Embeddings | 否 | 是 |

### Reranking Provider（`RERANKING_PROVIDER`）

| 值 | 說明 | 需要 GPU | 需要金鑰 |
|---|---|---|---|
| `local`（預設） | 本地 Qwen3-Reranker-4B | 是 | 否 |
| `cohere` | Cohere Rerank API | 否 | 是 |
| `voyageai` | Voyage AI Rerank | 否 | 是 |
| `flashrank` | FlashRank（本機輕量 reranker） | 否 | 否 |

### 金鑰設定

| 環境變數 | 說明 |
|---|---|
| `PROVIDER_API_KEY` | 通用金鑰，embedding 和 reranking 共用同一 provider 時使用 |
| `EMBEDDING_API_KEY` | Embedding 專用金鑰，混搭不同 provider 時使用 |
| `RERANKING_API_KEY` | Reranking 專用金鑰，混搭不同 provider 時使用 |

優先順序：`EMBEDDING_API_KEY` > `PROVIDER_API_KEY`（向下相容）

### 選填設定

```env
EMBEDDING_MODEL_NAME=   # 覆寫 embedding 模型，例如 text-embedding-3-large
RERANKING_MODEL_NAME=   # 覆寫 reranking 模型
EMBEDDING_BATCH_SIZE=   # API 批次大小，預設 100（本地模型不受此影響）
```

---

## 切換 Provider 的注意事項

切換 Embedding Provider 時，向量維度會改變，**必須重新建立索引**，否則啟動時會報錯。

| Provider | 預設模型 | 向量維度 |
|---|---|---|
| `local` | Qwen3-Embedding-4B | 2560 |
| `local`（VRAM 不足） | Qwen3-Embedding-0.6B | 1024 |
| `openai` | text-embedding-3-small | 1536 |
| `cohere` | embed-multilingual-v3.0 | 1024 |
| `voyageai` | voyage-3 | 1024 |

---

## 測試

```bash
uv run python -m pytest python-rag/tests/ -v
```

---

## 評估框架

系統內建評估框架，可量化比較不同 retrieval 策略的效果。

### 驗證資料集

```bash
uv run scripts/run_evaluation.py --dry-run
```

### 執行完整評估

```bash
# 使用 OpenAI embedding（需設定 API key）
EMBEDDING_PROVIDER=openai OPENAI_API_KEY=sk-xxx uv run scripts/run_evaluation.py

# 只跑特定策略
uv run scripts/run_evaluation.py --strategy bm25 --k 5
uv run scripts/run_evaluation.py --strategy hybrid --k 10

# 所有策略，自訂輸出目錄
uv run scripts/run_evaluation.py --output-dir data/eval/results
```

評估完成後，終端機會輸出各策略的 Recall@K、MRR、NDCG@K 比較表，完整 Markdown 報告存至 `data/eval/results/eval_YYYYMMDD_HHMMSS.md`。

**建立 Golden Dataset：**

`data/` 目錄不納入版本控制，需自行建立評估資料集。參考範例格式：

```bash
cp scripts/golden_dataset.example.json data/eval/golden_dataset.json
# 接著編輯 golden_dataset.json，填入你的查詢與預期答案
```

每筆資料格式：

```json
{
  "query": "勞工加班費應如何計算？",
  "expected_law": "勞動基準法",
  "expected_articles": ["第 24 條"],
  "query_type": "semantic"
}
```

`query_type` 可為 `"semantic"`（情境描述）或 `"exact"`（直接查詢條號）。

---

## 實際範例演示

以下為在 Kiro IDE 中使用 `compare_laws` 工具比較「投資商品」與「基金商品」定義的實際查詢過程：

![實際範例：比較投資商品與基金商品定義](docs/images/demo_compare_laws.png)
