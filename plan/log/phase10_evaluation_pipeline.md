# Phase 10：評估框架（Evaluation Pipeline）

## 目標

建立可量化的 RAG 系統評估機制，能夠系統性地比較不同 retrieval 策略（Vector-only、BM25-only、Hybrid）與不同 RRF_k 值的效果差異，將技術決策從主觀判斷轉為有數據支撐的量化比較。

---

## 實作內容

### 新增模組結構

```
python-rag/
└── evaluation/
    ├── __init__.py         # 模組入口，re-export 所有公開符號
    ├── exceptions.py       # 自訂例外層級
    ├── models.py           # EvalQuery、StrategyMetrics、EvaluationResult dataclass
    ├── dataset.py          # DatasetLoader：載入、驗證、篩選 Golden Dataset
    ├── metrics.py          # MetricsCalculator：Recall@K、MRR、NDCG@K
    ├── evaluator.py        # Evaluator + RetrievalStrategy 策略模式
    └── report.py           # ReportGenerator：Markdown 報告 + ASCII 圖表

data/eval/
├── golden_dataset.json     # 20 筆人工標注查詢（勞動基準法、民法、消費者保護法）
└── results/                # 評估報告輸出目錄（eval_YYYYMMDD_HHMMSS.md）

scripts/
└── run_evaluation.py       # CLI 評估入口腳本

python-rag/tests/
├── test_eval_dataset.py    # DatasetLoader 單元測試（13 tests）
├── test_eval_metrics.py    # MetricsCalculator 單元測試（19 tests）
├── test_eval_evaluator.py  # Evaluator 單元測試（17 tests）
└── test_eval_report.py     # ReportGenerator 單元測試（13 tests）
```

### 例外層級

```
EvaluationPipelineError (base)
├── DatasetNotFoundError
├── DatasetFormatError
├── DatasetValidationError
└── ReportWriteError
```

### 評估策略

`build_strategies()` 預設產生以下策略組合：

| 策略名稱 | 說明 |
|---|---|
| `vector` | 純向量搜尋 |
| `bm25` | 純 BM25 關鍵字搜尋 |
| `hybrid_rrf10` | Hybrid，RRF k=10 |
| `hybrid_rrf30` | Hybrid，RRF k=30 |
| `hybrid_rrf60` | Hybrid，RRF k=60 |
| `hybrid_rrf{k}_reranked` | 加上 Reranker 的 Hybrid（需要 reranking provider） |

### Golden Dataset

- 20 筆查詢，涵蓋 semantic（13 筆）與 exact（7 筆）兩種類型
- 涵蓋勞動基準法、民法、消費者保護法三部法律
- 所有 `expected_articles` 均已驗證存在於 chunks 資料中
- `data/` 目錄不納入版本控制，需自行建立；範例格式見 `scripts/golden_dataset.example.json`

---

## 使用方式

### 驗證資料集（不需要 provider）

```bash
uv run scripts/run_evaluation.py --dry-run
```

### 執行完整評估

```bash
# 使用 OpenAI embedding
EMBEDDING_PROVIDER=openai OPENAI_API_KEY=sk-xxx uv run scripts/run_evaluation.py

# 只跑特定策略
uv run scripts/run_evaluation.py --strategy bm25 --k 5

# 指定輸出目錄
uv run scripts/run_evaluation.py --output-dir data/eval/results
```

### 執行測試

```bash
uv run python -m pytest python-rag/tests/test_eval_dataset.py python-rag/tests/test_eval_metrics.py python-rag/tests/test_eval_evaluator.py python-rag/tests/test_eval_report.py -v
```

---

## 測試結果

62 個單元測試全部通過（0 failures）：

- `test_eval_dataset.py`：13 passed
- `test_eval_metrics.py`：19 passed
- `test_eval_evaluator.py`：17 passed
- `test_eval_report.py`：13 passed

---

## 設計決策

**策略模式（Strategy Pattern）**：每種 `RetrievalStrategy` 封裝一個 retrieve 函式，讓 `Evaluator` 以統一介面執行不同策略，方便後續新增策略。

**容錯設計**：單一查詢 retrieval 失敗時，記錄至 `EvaluationResult.errors` 並繼續，不中斷整體評估流程。

**指標計算**：`MetricsCalculator` 為純靜態方法模組，無狀態，方便單元測試與複用。Recall@K 採用 hits/effective_k 比例計算（非二元），與 Property 4 規格一致。
