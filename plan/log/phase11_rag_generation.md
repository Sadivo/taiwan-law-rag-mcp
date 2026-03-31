# Phase 11：RAG Generation — 完整問答生成層

## 目標

在現有 retrieval 基礎上加入 generation 層，實現完整的 RAG loop，將系統從「法律搜尋工具」升級為「法律 AI 助理」。

## 新增 / 修改的檔案

| 檔案 | 說明 |
|---|---|
| `python-rag/generation/__init__.py` | generation 模組初始化 |
| `python-rag/generation/base.py` | `GenerationProvider` ABC + `GenerationProviderError` |
| `python-rag/generation/langchain_provider.py` | `LangChainGenerationProvider`（支援 ollama / openai / anthropic） |
| `python-rag/generation/rag_chain.py` | `RAGChain`：整合 retrieval + generation |
| `python-rag/api/chat_routes.py` | `POST /chat` 與 `POST /chat/stream` FastAPI 端點 |
| `python-rag/api/models.py` | 新增 `Citation`、`ChatRequest`、`ChatResponse` Pydantic model |
| `python-rag/providers/factory.py` | 擴充 `ProviderFactory`，新增 `generation_from_env()` |
| `python-rag/main.py` | 掛載 `chat_routes` router |
| `mcp-server/src/tools/ask_question.ts` | `ask_law_question` MCP Tool |
| `mcp-server/src/clients/rag_client.ts` | 新增 `chat()` 方法與 TypeScript interface |
| `mcp-server/src/index.ts` | 註冊 `ask_law_question` tool |
| `mcp-server/src/tests/ask_question.test.ts` | MCP Tool property-based tests（fast-check） |
| `python-rag/tests/generation/` | Python property-based tests（Hypothesis） |
| `.env.example` | 新增 generation 相關環境變數 |

## 使用方式

### 環境變數設定

```env
GENERATION_PROVIDER=ollama        # ollama | openai | anthropic
GENERATION_API_KEY=               # openai / anthropic 需填入
GENERATION_MODEL_NAME=qwen3:8b    # 模型名稱
GENERATION_TOP_K=5                # retrieval 取回條文數
GENERATION_MAX_TOKENS=1024        # LLM 最大 token 數
OLLAMA_BASE_URL=http://localhost:11434
```

### API 使用

```bash
# 完整回答
curl -X POST http://localhost:8073/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "勞工加班費如何計算？", "top_k": 5}'

# 串流回答（SSE）
curl -X POST http://localhost:8073/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "勞工加班費如何計算？"}'
```

### MCP Tool

```
ask_law_question(question="勞工加班費如何計算？", top_k=5)
```

## 測試結果

- Python generation tests：14 passed
- Python all tests（excluding index-dependent）：111 passed
- MCP server tests：2 passed（2 test files）

## 設計決策

- `GenerationProvider` 與現有 `EmbeddingProvider` / `RerankingProvider` 採用相同抽象模式
- `LangChainGenerationProvider` 透過 `BaseChatModel` 統一支援多後端，切換只需改 `.env`
- retrieval 結果為空時直接回傳固定訊息，不呼叫 LLM，節省 API 費用
- SSE 串流格式：`data: {token}\n\n`，結束 `data: [DONE]\n\n`，錯誤 `data: [ERROR] {message}\n\n`
