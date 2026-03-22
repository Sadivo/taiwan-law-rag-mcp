# Phase 8：LangChain Provider 整合與 MCP 端對端測試

## 目標

將 RAG 系統的 Embedding / Reranking 層抽象化，支援任意 LangChain Provider（不再寫死 local 模型），並完成 MCP Server 端對端查詢測試。

---

## 實作內容

### 1. Provider 抽象層（`python-rag/providers/`）

建立完整的 Provider 模組：

| 檔案 | 說明 |
|---|---|
| `config.py` | `ProviderConfig` pydantic model、自訂例外類別 |
| `base.py` | `EmbeddingProvider`、`RerankingProvider` 抽象介面 |
| `local_providers.py` | 封裝本地 `Embedder` / `Reranker` |
| `langchain_providers.py` | 透過 LangChain 介面支援任意線上 Provider |
| `factory.py` | `ProviderFactory.from_env()` 從環境變數建立 Provider |

### 2. 統一 API 金鑰設計

- 使用 `PROVIDER_API_KEY` 單一環境變數，不再區分 `OPENAI_API_KEY` / `COHERE_API_KEY`
- 向下相容：若未設定 `PROVIDER_API_KEY`，仍會 fallback 讀取舊格式金鑰
- 切換 Provider 只需改 `EMBEDDING_PROVIDER` 和 `RERANKING_PROVIDER` 兩個變數

### 3. 支援任意 LangChain Provider

`_BUILTIN_EMBEDDINGS` 查表支援：openai、cohere、huggingface、google、mistral、voyageai、bedrock、azure-openai

進階用法：透過 `config.extra["langchain_class"]` 指定任意 LangChain Embeddings class。

### 4. rebuild_index.py 改用 ProviderFactory

- 移除 hardcode 的 `Embedder` import
- 改用 `ProviderFactory.create_embedding_provider()` 讀取 `.env`
- 只初始化 embedding provider，不載入 reranker（避免浪費 VRAM / 下載時間）
- local 模型的 batch_size 由 `Embedder._auto_batch_size()` 自動決定，不受 `EMBEDDING_BATCH_SIZE` 影響

---

## 問題與解法

### 問題 1：`langchain-voyageai` 未安裝

**錯誤：** `ModuleNotFoundError: No module named 'langchain_voyageai'`

**解法：** `uv pip install langchain-voyageai`

**根本原因：** LangChain 各 provider 是獨立套件，需個別安裝。

---

### 問題 2：pydantic v2 model 的 `inspect.signature` 不可靠

**錯誤：**
```
ValidationError: 1 validation error for VoyageAIEmbeddings
model - Field required
```

**原因：** pydantic v2 的 model `__init__` 簽名只有 `**data`，`inspect.signature` 掃不到 field 名稱，導致 `model` 參數沒被傳入。

**解法：**
1. API key 參數名改用 `_API_KEY_PARAM` 查表（每個 provider 的參數名不同）
2. 模型名稱改為逐一嘗試 `model` / `model_name`，哪個不報錯就用哪個
3. 移除重複定義的 `_embed_query_with_retry` / `_embed_batch_with_retry` 方法

---

### 問題 3：VoyageAI Rate Limit

**錯誤：** `RateLimitError: 3 RPM and 10K TPM`

**原因：** 帳號未加付款方式，rate limit 極低（3 RPM），48212 個 chunks 一次送出直接撞牆。

**解法：** 至 [dashboard.voyageai.com](https://dashboard.voyageai.com/) 加付款方式，或先用 `--test-limit 100` 測試少量 chunks。

---

### 問題 4：rebuild_index.py 初始化了不需要的 Reranker

**現象：** 執行 `rebuild_index.py` 時，花了 10 分鐘下載 Qwen3-Reranker-4B（8GB），佔用大量 VRAM，但重建索引根本不需要 reranker。

**原因：** 原本呼叫 `ProviderFactory.from_env()` 會同時初始化 embedding + reranking 兩個 provider。

**解法：** 改為只呼叫 `ProviderFactory.create_embedding_provider(embedding_config)`，跳過 reranker 初始化。

---

### 問題 5：Port 8000 被佔用

**錯誤：** `[WinError 10013] 嘗試存取通訊端被拒絕`

**解法：**
```bash
netstat -ano | findstr :8000   # 找到佔用的 PID
taskkill /PID <PID> /F         # 強制終止
```

---

### 問題 6：MCP exact search 回傳空結果（法律別名未轉換）

**現象：** 查詢「勞基法第17條」回傳空結果。

**原因：** `QueryClassifier` 解析出 `law_name="勞基法"`，但 chunks 裡存的是完整名稱 `"勞動基準法"`，字串比對失敗。`law_aliases.py` 雖然有別名對照表，但 `retrieval_service.py` 的 `search_exact` 沒有使用它。

**解法：** 在 `search_exact` 加入 `normalize_law_name(law_name)` 轉換：
```python
from data_processing.law_aliases import normalize_law_name
if law_name:
    law_name = normalize_law_name(law_name)
```

---

### 問題 7：API `SearchResult` model 的 `score` 為必填

**錯誤：**
```
ValidationError: 1 validation error for SearchResult
score - Field required
```

**原因：** `api/models.py` 的 `SearchResult.score` 是必填欄位，但 exact search / law search 回傳的 chunks 沒有 `score`（只有 semantic search 才有相關度分數）。

**解法：** 將 `score` 改為 optional：
```python
score: Optional[float] = Field(default=None, description="相關度分數")
```
同時將所有 `str` 欄位加上 `default=""`，避免其他欄位缺失時也報錯。

---

### 問題 8：README 未說明需啟動 FastAPI

**現象：** MCP 工具呼叫失敗，原因是 `http://localhost:8000` 沒有服務在跑。

**解法：** 更新 README 步驟 4，明確說明需執行：
```bash
uv run python-rag/main.py
```

---

## MCP 端對端測試結果

### 測試 1：精確條文查詢

**查詢：** 勞基法第17條

**結果：** ✅ 成功

```
【1】勞動基準法 第 17 條 (第 二 章 勞動契約)
雇主依前條終止勞動契約者，應依下列規定發給勞工資遣費：
一、在同一雇主之事業單位繼續工作，每滿一年發給相當於一個月平均工資之資遣費。
二、依前款計算之剩餘月數，或工作未滿一年者，以比例計給之。未滿一個月者以一個月計。
前項所定資遣費，雇主應於終止勞動契約三十日內發給。
```

### 測試 2：語義搜尋

**查詢：** 投資型商品定義條件

**結果：** ✅ 成功，回傳 10 條相關法條，涵蓋金融資產證券化條例、證券交易法、不動產證券化條例等。

---

## 系統啟動流程（確認可用）

```
1. uv run scripts/build_index.py     # 建立索引（首次或切換 Provider 後）
2. uv run python-rag/main.py         # 啟動 FastAPI（每次使用前）
3. Claude Desktop 透過 MCP 查詢      # 正常運作
```

---

## 環境設定（`.env`）

```
EMBEDDING_PROVIDER=voyageai
EMBEDDING_MODEL_NAME=voyage-3.5-lite
RERANKING_PROVIDER=local
PROVIDER_API_KEY=<voyageai api key>
```
