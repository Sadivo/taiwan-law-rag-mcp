# 優化與擴充計畫

> 基礎功能完成後的進階優化方向，目標是讓專案在技術面試中展現更深的工程深度。

---

## 優先順序總覽

| 優先級 | 項目 | 預估工時 | 亮點 | 狀態 |
|---|---|---|---|---|
| ⭐⭐⭐ | Phase 10：評估框架 | 4-6h | 量化技術決策，有數據說話 | ✅ 已完成 |
| ⭐⭐⭐ | Phase 11：法律問答生成 | 4-6h | 完整 RAG loop，demo 效果強 | ✅ 已完成 |
| ⭐⭐ | Phase 12：查詢意圖理解 | 3-4h | 展示對 RAG 核心痛點的理解 | 待實作 |

---

## Phase 10：評估框架（Evaluation Pipeline）✅ 已完成

> 詳細實作記錄：[plan/log/phase10_evaluation_pipeline.md](log/phase10_evaluation_pipeline.md)

### 目標
建立可量化的 RAG 系統評估機制，能夠比較不同 provider 組合、retrieval 策略的效果差異。

### 為什麼重要
大多數 RAG side project 只有「能跑」，沒有「能量化」。一張「hybrid retrieval 比純 vector 搜尋 Recall@10 高 18%」的圖表，比任何文字描述都有說服力。

### 實作成果

- `python-rag/evaluation/` 模組：DatasetLoader、MetricsCalculator、Evaluator、ReportGenerator
- `data/eval/golden_dataset.json`：20 筆人工標注查詢（勞動基準法、民法、消費者保護法）
- `scripts/run_evaluation.py`：CLI 評估腳本，支援 `--strategy`、`--k`、`--dry-run` 等參數
- 62 個單元測試全部通過

### 快速使用

```bash
# 驗證資料集
uv run scripts/run_evaluation.py --dry-run

# 執行完整評估（需設定 embedding provider）
EMBEDDING_PROVIDER=openai OPENAI_API_KEY=sk-xxx uv run scripts/run_evaluation.py
```

---

## Phase 11：法律問答生成（RAG Generation）✅ 已完成

> 詳細實作記錄：[plan/log/phase11_rag_generation.md](log/phase11_rag_generation.md)

### 目標
在現有 retrieval 基礎上加入 generation 層，讓系統從「搜尋工具」升級為「法律 AI 助理」。

### 為什麼重要
目前系統只做 retrieval，沒有 generation，不是完整的 RAG loop。加入生成層後，demo 時可以直接問問題、得到有引用來源的回答，視覺效果差很多。

### 實作內容

#### 11.1 Generation Provider 抽象層
延伸現有 Provider 架構，加入 `GenerationProvider`：
- 本地：Ollama（Qwen3-8B 或 llama3）
- 線上：OpenAI、Anthropic Claude

#### 11.2 RAG Chain 實作
```
用戶問題
  → Retrieval（現有 hybrid retrieval）
  → Context 組裝（相關條文 + 引用資訊）
  → Prompt 建構（system prompt + context + question）
  → LLM 生成回答
  → 串流輸出（SSE）
```

#### 11.3 新增 API 端點
- `POST /chat`：接收問題，回傳生成回答 + 引用條文
- `POST /chat/stream`：串流版本（SSE）

#### 11.4 新增 MCP Tool
- `ask_law_question`：整合 retrieval + generation，直接回答法律問題

#### 11.5 Prompt 設計
```
你是一位台灣法律助理，請根據以下法律條文回答問題。
回答時必須引用具體條文，不得捏造法律內容。

相關法律條文：
{retrieved_articles}

問題：{user_question}

請用繁體中文回答，並在回答末尾列出引用的條文來源。
```

### 新增檔案
```
python-rag/
└── generation/
    ├── __init__.py
    ├── base.py                  # GenerationProvider ABC + GenerationProviderError
    ├── langchain_provider.py    # LangChainGenerationProvider（統一支援 ollama/openai/anthropic）
    └── rag_chain.py             # RAGChain（整合 retrieval + generation）

python-rag/api/
└── chat_routes.py               # POST /chat 與 POST /chat/stream 端點

python-rag/tests/generation/
├── test_base.py                 # Property 1（3 tests）
├── test_langchain_provider.py   # Properties 2–4（3 tests）
├── test_factory.py              # Property 5（1 test）
├── test_rag_chain.py            # Properties 6–10（5 tests）
└── test_chat_routes.py          # Properties 11–12（2 tests）

mcp-server/src/tools/
└── ask_question.ts              # ask_law_question MCP tool

mcp-server/src/tests/
└── ask_question.test.ts         # Property 13（fast-check，1 test）
```

### 驗收標準
- `POST /chat` 能回傳包含引用條文的法律回答 ✅
- `POST /chat/stream` 能串流輸出 ✅
- MCP tool `ask_law_question` 在 Claude Desktop 中可正常使用 ✅
- 回答中包含正確的條文引用 ✅
- 14 個 Python property tests + 2 個 TypeScript tests 全部通過 ✅

---

## Phase 12：查詢意圖理解（Query Understanding）

### 目標
升級 `QueryClassifier`，讓系統更智慧地理解用戶意圖，提升 retrieval 品質。

### 為什麼重要
展示對 RAG 核心痛點的理解：用戶的原始 query 往往不是最好的搜尋輸入，query rewriting 和意圖理解是提升 RAG 效果的關鍵技術。

### 實作內容

#### 12.1 Query Rewriting
將模糊的用戶問題改寫為更適合 retrieval 的形式：
- 「加班費怎麼算？」→「加班費計算方式 延長工時工資標準」
- 「被老闆開除怎麼辦？」→「雇主終止勞動契約 資遣費 預告期間」

#### 12.2 多輪對話上下文
支援對話歷史，理解指代關係：
- 「那第二條呢？」→ 結合上一輪的法律名稱
- 「還有其他相關規定嗎？」→ 擴展搜尋範圍

#### 12.3 查詢語言偵測
自動偵測中文/英文查詢，對英文查詢做翻譯後再搜尋。

#### 12.4 意圖分類擴充
從現有的 exact/semantic 二分類，擴充為：
- `exact`：已知條號
- `semantic`：情境描述
- `comparison`：比較多部法律
- `definition`：查詢法律定義
- `procedure`：查詢法律程序

### 新增檔案
```
python-rag/retrieval/
├── query_rewriter.py       # Query rewriting 邏輯
└── context_manager.py      # 多輪對話上下文管理

python-rag/api/
└── session_routes.py       # 支援 session 的對話端點
```

### 驗收標準
- Query rewriting 對模糊問題的 Recall@10 提升 ≥ 10%（用 Phase 10 的評估框架驗證）
- 多輪對話能正確解析指代關係
- 意圖分類準確率 ≥ 85%

---

## 執行順序建議

```
Phase 10（評估框架）
  → 先有量化基準，後續優化才有數據支撐

Phase 11（問答生成）
  → 完整 RAG loop，demo 效果最強

Phase 12（查詢意圖）
  → 用 Phase 10 的框架驗證改善效果
```
