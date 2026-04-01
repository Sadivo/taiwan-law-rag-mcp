# Phase 13：操作體驗優化（UX Optimization）

> 狀態：🔲 規劃中

## 背景

Phase 10–12 完成後，系統功能已相當完整，但操作體驗仍有明顯痛點：
- 文件（INSTALLATION / USAGE / API）全部是空的
- 沒有統一 CLI 入口，使用者需要記憶多個指令路徑
- 環境設定變數多且複雜，新手容易卡關
- Provider 初始化失敗時錯誤訊息不夠明確

本 Phase 目標是讓「第一次使用的人能在 5 分鐘內跑起來」。

---

## 優先順序與任務清單

### Phase 13.1：補齊文件（最快見效）

**目標**：讓新使用者有文件可以看

- [ ] `docs/INSTALLATION.md`：從零到能跑的步驟（含 uv、Ollama、MCP 設定）
- [ ] `docs/USAGE.md`：常見使用情境 + curl 範例 + MCP 呼叫範例
- [ ] `docs/API.md`：所有 endpoint 說明 + request/response 範例

預估工時：1–2h

---

### Phase 13.2：統一 CLI 入口

**目標**：根目錄有一個明確的入口點，不需要記憶 `python-rag/main.py` 的路徑

根目錄 `main.py` 改為 CLI dispatcher，提供子命令：

```
uv run main.py serve    # 啟動 FastAPI（等同 uv run python-rag/main.py）
uv run main.py index    # 重建索引
uv run main.py eval     # 執行評估
uv run main.py check    # 環境健康檢查（不啟動服務）
```

或透過 `pyproject.toml` 的 `[project.scripts]` 定義 `taiwan-law` 指令。

預估工時：2–3h

---

### Phase 13.3：Setup Script / Makefile

**目標**：一鍵完成環境初始化

`scripts/setup.py` 或 `Makefile` 流程：
1. 確認 `.venv` 存在，否則執行 `uv venv`
2. 執行 `uv sync`
3. 若 `.env` 不存在，從 `.env.example` 複製並提示填寫
4. 執行 `uv run main.py check` 驗證設定

預估工時：1h

---

### Phase 13.4：啟動健康檢查 + 錯誤訊息改善

**目標**：啟動時明確告知每個 provider 的狀態，不讓錯誤延遲到第一次請求才爆出

啟動摘要範例：
```
Taiwan Law RAG — http://127.0.0.1:8073
  ✓ Embedding  : local:bge-m3
  ✓ Reranking  : local:bge-reranker
  ✗ Generation : ollama (unreachable at http://localhost:11434)
```

`/health` endpoint 擴充，回傳每個 provider 的狀態：
```json
{
  "status": "degraded",
  "embedding_provider": "local:bge-m3",
  "reranking_provider": "local:bge-reranker",
  "generation_provider": { "name": "ollama", "status": "unreachable" }
}
```

預估工時：1h

---

## 執行順序

```
13.1 文件
  → 13.2 CLI 入口
    → 13.3 Setup Script
      → 13.4 健康檢查
```

## 新增 / 修改的檔案（預計）

```
docs/
├── INSTALLATION.md     ← 新增
├── USAGE.md            ← 新增
└── API.md              ← 新增

main.py                 ← 改為 CLI dispatcher

scripts/
└── setup.py            ← 新增（或 Makefile）

python-rag/main.py      ← 加入啟動摘要輸出
python-rag/api/routes.py ← /health 擴充
```
