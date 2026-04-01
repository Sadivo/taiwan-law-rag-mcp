# Phase 12：查詢意圖理解（Query Understanding）

## 目標

升級 `QueryClassifier`，新增 Query Rewriting、語言偵測、多輪對話上下文管理，讓系統更智慧地理解用戶意圖，提升 retrieval 品質。

## 新增 / 修改的檔案

```
python-rag/retrieval/
├── query_classifier.py     # 擴充：IntentType（5種）、ClassificationResult dataclass
├── query_rewriter.py       # 新增：LanguageDetector、QueryRewriter、RewrittenQuery
├── context_manager.py      # 新增：ConversationTurn、Session、ContextManager（TTL=30min）
└── query_understanding.py  # 新增：QueryUnderstanding 整合入口

python-rag/generation/
└── rag_chain.py            # 擴充：接受 QueryUnderstanding、session_id 參數、依 intent 選擇 retrieval 策略

python-rag/api/
├── models.py               # 擴充：SessionChatRequest/Response、CreateSessionResponse、DeleteSessionResponse
├── session_routes.py       # 新增：POST /session、POST /session/{id}/chat、DELETE /session/{id}
└── chat_routes.py          # 擴充：ENABLE_QUERY_REWRITING 環境變數控制

python-rag/main.py          # 擴充：掛載 session_routes.router

python-rag/tests/query_understanding/
├── __init__.py
├── test_query_classifier.py    # Property 1 + 單元測試（24 tests）
├── test_language_detector.py   # Property 5 + 單元測試（12 tests）
├── test_query_rewriter.py      # Properties 2, 3, 4 + 單元測試（13 tests）
├── test_context_manager.py     # Properties 6, 7 + 單元測試（13 tests）
├── test_query_understanding.py # Properties 8, 9 + 整合測試（10 tests）
└── test_session_routes.py      # Session API 端點測試（9 tests）
```

## 使用方式

### 啟用 Query Rewriting

```bash
ENABLE_QUERY_REWRITING=true uv run python-rag/main.py
```

### Session API

```bash
# 建立 Session
curl -X POST http://localhost:8073/session

# 多輪對話
curl -X POST http://localhost:8073/session/{session_id}/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "加班費怎麼算", "top_k": 5}'

# 刪除 Session
curl -X DELETE http://localhost:8073/session/{session_id}
```

### 執行測試

```bash
uv run python -m pytest python-rag/tests/query_understanding/ -v
```

## 測試結果

68 個測試全部通過，涵蓋 9 個 Correctness Properties（Hypothesis PBT）與各模組單元/整合測試。

## 設計決策

- `LanguageDetector` 純規則實作（CJK 比例 > 0.3 → zh，ASCII 字母比例 > 0.5 → en），不依賴外部 API
- `QueryRewriter` 使用 `concurrent.futures` 實作超時（Windows 不支援 SIGALRM）
- `ContextManager` 惰性清除過期 Session（TTL = 1800 秒）
- `QueryUnderstanding.process()` 捕捉所有子模組例外，保證不向上傳播
- `RAGChain` 向後相容：無 `query_understanding` 時維持原有行為
