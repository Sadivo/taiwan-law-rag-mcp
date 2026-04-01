# Phase 13：UX 優化（UX Optimization）

## 目標

讓「第一次使用的人能在 5 分鐘內跑起來」，涵蓋四個面向：補齊文件、統一 CLI 入口、一鍵 setup、以及啟動健康檢查與錯誤訊息改善。

---

## 新增 / 修改的檔案

| 檔案 | 說明 |
|---|---|
| `docs/INSTALLATION.md` | 完整安裝指南（前置需求、虛擬環境、.env 設定、啟動、驗證） |
| `docs/USAGE.md` | 使用說明（MCP 工具範例、curl 指令、Session 流程、CLI 子命令、Query Rewriting） |
| `docs/API.md` | API 參考文件（所有 endpoint 的 schema、request/response 範例、錯誤格式） |
| `main.py` | CLI Dispatcher（argparse，支援 serve/index/eval/check 四個子命令） |
| `scripts/setup.py` | 一鍵 Setup Script（venv → sync → .env → check，含進度訊息與錯誤處理） |
| `python-rag/api/health.py` | Health Checker 模組（ProviderStatus、HealthState、print_startup_summary） |
| `python-rag/api/models.py` | 擴充 HealthResponse（新增 GenerationProviderInfo） |
| `python-rag/main.py` | 改用 lifespan 初始化，整合 health state，啟動時輸出 Startup Summary |
| `python-rag/tests/ux_optimization/` | 文件覆蓋率 PBT、health 模組單元測試與 PBT、/health endpoint 測試 |
| `tests/test_cli_dispatcher.py` | CLI Dispatcher 單元測試與 PBT（Property 5、6） |
| `tests/test_setup.py` | Setup Script 單元測試與 PBT（Property 7、8） |
| `pyproject.toml` | 新增 `[tool.pytest.ini_options]`（testpaths、pythonpath） |

---

## 使用方式

```bash
# 一鍵初始化環境
uv run scripts/setup.py

# 啟動服務
uv run main.py serve

# 重建索引
uv run main.py index

# 執行評估
uv run main.py eval

# 驗證環境（不啟動 FastAPI）
uv run main.py check
```

啟動後輸出範例：
```
Taiwan Law RAG — http://127.0.0.1:8073
  ✓ Embedding  : local:Qwen3-Embedding-4B
  ✓ Reranking  : local:Qwen3-Reranker-4B
  ✗ Generation : ollama:qwen3:8b (unreachable at http://localhost:11434)
```

---

## 測試結果

41 個測試全部通過（含 10 個 Property-Based Tests）：

- Property 1：INSTALLATION.md 涵蓋所有 Provider
- Property 2：USAGE.md 涵蓋所有 MCP 工具
- Property 3：USAGE.md 涵蓋所有 CLI 子命令
- Property 4：API.md 涵蓋所有 Endpoint
- Property 5：CLI Dispatcher 識別所有合法子命令
- Property 6：CLI Dispatcher 例外處理
- Property 7：Setup Script 進度訊息格式
- Property 8：Setup Script 失敗處理
- Property 9：Startup Summary 格式正確性
- Property 10：/health overall_status 由最差 provider 決定

---

## 設計決策

- **包裝層原則**：所有改動均為包裝層，不修改 `python-rag/` 內部核心邏輯
- **lifespan 初始化**：將 FastAPI 的 provider 初始化從 lazy（首次請求）改為 eager（啟動時），確保 Startup Summary 在服務就緒前輸出
- **Generation 容錯**：Generation provider 初始化失敗不中止服務，標記為 `unreachable`，搜尋功能仍可用
- **TestClient 相容性**：starlette 0.27.0 + httpx 0.28.1 不相容，/health endpoint 測試改為直接呼叫 async 函式
