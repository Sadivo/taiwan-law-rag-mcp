# Taiwan Law RAG — 使用說明

本文件涵蓋 MCP 工具呼叫範例、FastAPI curl 指令、Session 多輪對話流程、CLI 子命令說明，以及 Query Understanding 模組的啟用方式。

---

## 目錄

1. [MCP 工具使用範例](#1-mcp-工具使用範例)
2. [FastAPI curl 指令範例](#2-fastapi-curl-指令範例)
3. [Session API 多輪對話流程](#3-session-api-多輪對話流程)
4. [CLI 子命令說明](#4-cli-子命令說明)
5. [Query Understanding 模組](#5-query-understanding-模組)

---

## 1. MCP 工具使用範例

MCP Server 透過 TypeScript 實作，呼叫底層 FastAPI（預設 `http://127.0.0.1:8073`）。以下範例適用於任何支援 MCP 協定的客戶端（如 Claude Desktop、Kiro）。

### semantic_search

根據法律問題或關鍵字進行語義向量搜尋，找出最相關的法條。

```json
{
  "tool": "semantic_search",
  "arguments": {
    "query": "加班費計算規定",
    "top_k": 5,
    "filter_category": "勞動"
  }
}
```

參數說明：
- `query`（必填）：法律問題或關鍵字
- `top_k`（選填，預設 10）：回傳結果數量
- `filter_category`（選填）：過濾法律類別

---

### exact_search

精確條文查詢，適合已知法律名稱與條號的情境。

```json
{
  "tool": "exact_search",
  "arguments": {
    "query": "勞基法第38條"
  }
}
```

參數說明：
- `query`（必填）：精確查詢句，例如「勞動基準法第 24 條」

---

### search_law_by_name

依法律名稱搜尋，找出符合名稱關鍵字的法律列表。

```json
{
  "tool": "search_law_by_name",
  "arguments": {
    "law_name": "勞動基準法",
    "include_abolished": false
  }
}
```

參數說明：
- `law_name`（必填）：法律名稱或關鍵字
- `include_abolished`（選填，預設 `false`）：是否包含已廢止法律

---

### get_law_full_text

取得指定法律的完整條文全文。

```json
{
  "tool": "get_law_full_text",
  "arguments": {
    "law_name": "勞動基準法"
  }
}
```

參數說明：
- `law_name`（必填）：法律完整名稱

---

### compare_laws

比較多部法律在同一主題下的相關條文差異。

```json
{
  "tool": "compare_laws",
  "arguments": {
    "law_names": ["民法", "公司法"],
    "topic": "股東權利"
  }
}
```

參數說明：
- `law_names`（必填）：要比較的法律名稱陣列（至少兩部）
- `topic`（必填）：比較主題或關鍵字

---

### ask_law_question

向台灣法律 AI 助理提問，獲得有引用來源的繁體中文回答（完整 RAG 流程：檢索 + LLM 生成）。

```json
{
  "tool": "ask_law_question",
  "arguments": {
    "question": "雇主可以強制員工加班嗎？",
    "top_k": 5
  }
}
```

參數說明：
- `question`（必填）：法律問題
- `top_k`（選填，預設 5）：參考條文數量

回傳格式範例：
```
雇主不得強制員工加班，依勞動基準法第 32 條規定，延長工作時間須經勞工同意...

**引用條文：**
- 勞動基準法 第 32 條
- 勞動基準法 第 24 條
```

---

## 2. FastAPI curl 指令範例

服務預設運行於 `http://127.0.0.1:8073`。

### POST /search/semantic — 語義搜尋

```bash
curl -X POST http://127.0.0.1:8073/search/semantic \
  -H "Content-Type: application/json" \
  -d '{
    "query": "加班費計算規定",
    "top_k": 3,
    "filter_category": null
  }'
```

預期 response：
```json
{
  "results": [
    {
      "law_name": "勞動基準法",
      "law_level": "法律",
      "law_category": "勞動",
      "law_url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0030001",
      "article_no": "第 24 條",
      "chapter": "第三章 工資",
      "content": "雇主延長勞工工作時間者，其延長工作時間之工資依下列標準加給...",
      "score": 0.92,
      "modified_date": "2023-06-28"
    }
  ],
  "total": 3,
  "query_time": 0.045
}
```

---

### POST /search/exact — 精確條文查詢

```bash
curl -X POST http://127.0.0.1:8073/search/exact \
  -H "Content-Type: application/json" \
  -d '{
    "query": "勞基法第38條"
  }'
```

預期 response：
```json
{
  "results": [
    {
      "law_name": "勞動基準法",
      "law_level": "法律",
      "law_category": "勞動",
      "law_url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0030001",
      "article_no": "第 38 條",
      "chapter": "第三章 工資",
      "content": "勞工在同一雇主或事業單位，繼續工作滿一定期間者，應依下列規定給予特別休假...",
      "score": null,
      "modified_date": "2023-06-28"
    }
  ]
}
```

---

### POST /search/law — 依法律名稱搜尋

```bash
curl -X POST http://127.0.0.1:8073/search/law \
  -H "Content-Type: application/json" \
  -d '{
    "law_name": "勞動基準法",
    "include_abolished": false
  }'
```

預期 response：
```json
{
  "results": [
    {
      "law_name": "勞動基準法",
      "law_level": "法律",
      "law_category": "勞動",
      "law_url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0030001",
      "article_no": "",
      "chapter": "",
      "content": "",
      "score": null,
      "modified_date": "2023-06-28"
    }
  ]
}
```

---

### POST /law/full — 取得完整法律條文

```bash
curl -X POST http://127.0.0.1:8073/law/full \
  -H "Content-Type: application/json" \
  -d '{
    "law_name": "勞動基準法"
  }'
```

預期 response：
```json
{
  "law": {
    "law_name": "勞動基準法",
    "law_level": "法律",
    "law_category": "勞動",
    "law_url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0030001",
    "modified_date": "2023-06-28",
    "is_abolished": false
  },
  "articles": [
    {
      "article_no": "第 1 條",
      "content": "為規定勞動條件最低標準，保障勞工權益，加強勞雇關係，促進社會與經濟發展，特制定本法...",
      "chapter": "第一章 總則"
    },
    {
      "article_no": "第 2 條",
      "content": "本法用辭定義如左：一、勞工：謂受雇主僱用從事工作獲致工資者...",
      "chapter": "第一章 總則"
    }
  ]
}
```

---

### POST /law/compare — 比較多部法律

```bash
curl -X POST http://127.0.0.1:8073/law/compare \
  -H "Content-Type: application/json" \
  -d '{
    "law_names": ["民法", "公司法"],
    "topic": "股東權利"
  }'
```

預期 response：
```json
{
  "comparison": {
    "民法": [
      {
        "article_no": "第 179 條",
        "content": "無法律上之原因而受利益，致他人受損害者，應返還其利益...",
        "chapter": "第二編 債"
      }
    ],
    "公司法": [
      {
        "article_no": "第 179 條",
        "content": "公司各股東，除有左列情形之一者外，每股有一表決權...",
        "chapter": "第二章 股份有限公司"
      }
    ]
  }
}
```

---

### POST /chat — RAG 問答

```bash
curl -X POST http://127.0.0.1:8073/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "雇主可以強制員工加班嗎？",
    "top_k": 5
  }'
```

預期 response：
```json
{
  "answer": "依勞動基準法第 32 條規定，雇主不得強制員工加班，延長工作時間須經勞工同意，且每日不得超過 4 小時，每月不得超過 46 小時...",
  "citations": [
    { "law_name": "勞動基準法", "article_no": "第 32 條" },
    { "law_name": "勞動基準法", "article_no": "第 24 條" }
  ],
  "query_time": 2.31
}
```

---

### GET /health — 健康檢查

```bash
curl http://127.0.0.1:8073/health
```

預期 response（所有 provider 正常）：
```json
{
  "status": "ok",
  "embedding_provider": "local:Qwen3-Embedding-4B",
  "reranking_provider": "local:Qwen3-Reranker-4B",
  "generation_provider": {
    "name": "ollama:qwen3:8b",
    "status": "ok"
  }
}
```

Generation provider 無法連線時（服務仍正常運行）：
```json
{
  "status": "degraded",
  "embedding_provider": "local:Qwen3-Embedding-4B",
  "reranking_provider": "local:Qwen3-Reranker-4B",
  "generation_provider": {
    "name": "ollama:qwen3:8b",
    "status": "unreachable"
  }
}
```

---

## 3. Session API 多輪對話流程

Session API 支援上下文記憶與指代詞解析，適合需要連續追問的情境。每個 Session TTL 為 30 分鐘，最多保留最近 10 輪對話。

### 步驟一：建立 Session

```bash
curl -X POST http://127.0.0.1:8073/session \
  -H "Content-Type: application/json"
```

response：
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

記下 `session_id`，後續對話都需要帶入。

---

### 步驟二：帶上下文對話

使用 `session_id` 進行第一輪提問：

```bash
curl -X POST http://127.0.0.1:8073/session/550e8400-e29b-41d4-a716-446655440000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "勞動基準法對加班費有什麼規定？",
    "top_k": 5
  }'
```

response：
```json
{
  "answer": "依勞動基準法第 24 條，雇主延長勞工工作時間，應依下列標準加給工資：延長工作時間在 2 小時以內者，按平日每小時工資額加給三分之一以上...",
  "citations": [
    { "law_name": "勞動基準法", "article_no": "第 24 條" }
  ],
  "query_time": 1.85,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

接著追問（系統會自動解析「這個規定」指代前一輪的加班費規定）：

```bash
curl -X POST http://127.0.0.1:8073/session/550e8400-e29b-41d4-a716-446655440000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "這個規定有例外情況嗎？",
    "top_k": 5
  }'
```

response：
```json
{
  "answer": "依勞動基準法第 32 條，天災、事變或突發事件時，雇主有使勞工在正常工作時間以外工作之必要者，得將工作時間延長之，不受第 32 條第 2 項規定之限制...",
  "citations": [
    { "law_name": "勞動基準法", "article_no": "第 32 條" }
  ],
  "query_time": 1.92,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 步驟三：刪除 Session

對話結束後，主動刪除 Session 以釋放記憶體：

```bash
curl -X DELETE http://127.0.0.1:8073/session/550e8400-e29b-41d4-a716-446655440000
```

response：
```json
{
  "deleted": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

若 Session 不存在（已過期或已刪除），回傳：
```json
{
  "deleted": false,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 4. CLI 子命令說明

根目錄 `main.py` 是統一的 CLI 入口，透過 `uv run main.py <subcommand>` 執行。

### serve — 啟動 FastAPI 服務

```bash
uv run main.py serve
```

啟動 FastAPI + uvicorn 服務，預設監聽 `http://127.0.0.1:8073`。

預期輸出：
```
Taiwan Law RAG — http://127.0.0.1:8073
  ✓ Embedding  : local:Qwen3-Embedding-4B
  ✓ Reranking  : local:Qwen3-Reranker-4B
  ✓ Generation : ollama:qwen3:8b
INFO:     Uvicorn running on http://127.0.0.1:8073 (Press CTRL+C to quit)
```

若 Generation provider 無法連線，服務仍會啟動，但狀態顯示為 `✗`：
```
Taiwan Law RAG — http://127.0.0.1:8073
  ✓ Embedding  : local:Qwen3-Embedding-4B
  ✓ Reranking  : local:Qwen3-Reranker-4B
  ✗ Generation : ollama:qwen3:8b (unreachable at http://localhost:11434)
INFO:     Uvicorn running on http://127.0.0.1:8073 (Press CTRL+C to quit)
```

---

### index — 重建搜尋索引

```bash
uv run main.py index
```

從 `data/ChLaw.json/ChLaw.json` 重新建立 FAISS 向量索引與 BM25 索引。資料量大時需要數分鐘。

預期輸出：
```
[1/3] 載入法律資料...
[2/3] 建立向量索引（FAISS）...
[3/3] 建立關鍵字索引（BM25）...
索引重建完成，共處理 12345 個 chunks。
```

---

### eval — 執行評估框架

```bash
uv run main.py eval
```

對 `data/eval/golden_dataset.json` 中的測試集執行 RAG 評估，輸出各項指標摘要。

預期輸出：
```
評估資料集：data/eval/golden_dataset.json（共 50 筆）
執行中... ████████████████████ 100%

=== 評估結果摘要 ===
Precision@5  : 0.82
Recall@5     : 0.76
MRR          : 0.79
Answer ROUGE : 0.61
```

---

### check — 驗證環境與 Provider 狀態

```bash
uv run main.py check
```

不啟動 FastAPI 服務，僅驗證各 provider 的連線狀態並輸出結果。適合在啟動服務前確認環境設定是否正確。

預期輸出（全部正常）：
```
Taiwan Law RAG — 環境檢查
  ✓ Embedding  : local:Qwen3-Embedding-4B
  ✓ Reranking  : local:Qwen3-Reranker-4B
  ✓ Generation : ollama:qwen3:8b
環境設定正常，可執行 uv run main.py serve 啟動服務。
```

預期輸出（Generation 無法連線）：
```
Taiwan Law RAG — 環境檢查
  ✓ Embedding  : local:Qwen3-Embedding-4B
  ✓ Reranking  : local:Qwen3-Reranker-4B
  ✗ Generation : ollama:qwen3:8b (unreachable at http://localhost:11434)
警告：Generation provider 無法連線，/chat 端點將無法使用。
```

未提供子命令時，顯示使用說明：
```bash
uv run main.py
# usage: main.py [-h] {serve,index,eval,check} ...
# 請提供子命令。
# exit code: 1
```

---

## 5. Query Understanding 模組

### 啟用方式

在 `.env` 中設定：

```env
ENABLE_QUERY_REWRITING=true
```

或在啟動時臨時覆蓋：

```bash
ENABLE_QUERY_REWRITING=true uv run main.py serve
```

### 行為差異

| 功能 | `ENABLE_QUERY_REWRITING=false`（預設） | `ENABLE_QUERY_REWRITING=true` |
|---|---|---|
| 語言偵測 | 不執行 | 自動偵測中文 / 英文 |
| 英文查詢翻譯 | 不執行 | 自動翻譯為繁體中文再搜尋 |
| 意圖分類 | 不執行 | 分類為 exact / comparison / definition / procedure / semantic |
| 查詢改寫 | 不執行 | LLM 改寫查詢以提升檢索精準度（exact 意圖跳過） |
| 指代詞擴展 | 不執行 | Session 對話中自動展開「這個」「它」等指代詞 |

### 處理流程

啟用後，每個查詢在送入檢索前會經過以下管線：

```
query
  → 語言偵測（CJK/ASCII 比例判斷 zh/en）
  → 翻譯（英文 → 繁體中文，失敗時 fallback 原始查詢）
  → 意圖分類（5 種 IntentType）
  → 查詢改寫（LLM 改寫，exact 意圖跳過）
  → 指代詞擴展（結合上一輪 Session 查詢）
  → 送入 RetrievalService
```

任何子模組發生例外均會被捕捉，保證查詢永遠非空，不影響服務可用性。

### 範例

英文查詢自動翻譯：
```bash
curl -X POST http://127.0.0.1:8073/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "overtime pay regulations", "top_k": 3}'
# 內部自動翻譯為「加班費規定」再進行搜尋
```

意圖分類影響搜尋策略：
- `exact` 意圖（如「勞基法第 38 條」）→ 直接精確查詢，跳過改寫
- `semantic` 意圖（如「加班費怎麼算」）→ LLM 改寫後向量搜尋
- `comparison` 意圖（如「民法和公司法的差異」）→ 觸發比較邏輯
