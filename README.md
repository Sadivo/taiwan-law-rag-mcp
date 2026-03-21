# 台灣法律 RAG MCP 系統 (Taiwan Law RAG MCP)

這是一個專為台灣法律設計的 RAG (Retrieval-Augmented Generation) 系統，並提供 Model Context Protocol (MCP) Server 介面，可與 Claude Desktop 或任何支援 MCP 的 LLM 客戶端無縫整合。

系統結合了 Qwen3-Embedding-4B 的語意向量搜尋以及 Whoosh 的 BM25 關鍵字搜尋，透過 Reciprocal Rank Fusion (RRF) 混合檢索機制，再以 Qwen3-Reranker-4B 進行精準的重排序，能提供高召回率與高準確率的法條搜尋結果。

## 🌟 核心特色

- **混合檢索架構 (Hybrid Search)**：結合 FAISS 向量搜尋與 Whoosh 關鍵字全文搜尋。
- **高精度重排序 (Reranking)**：利用 Qwen3-Reranker-4B 模型計算 Query 與 Document 的 Cross-Encoder 相關度。
- **條文級切塊 (Article-Level Chunking)**：精確保留法律名稱、條號、章節等 Metadata，讓結果具備高度上下文。
- **MCP 整合支援**：透過 `@modelcontextprotocol/sdk` 提供 `semantic_search`, `exact_search`, `search_law_by_name`, `get_law_full_text`, `compare_laws` 等工具。

---

## 🏗️ 系統架構

專案主要分為兩大元件：

1. **Python RAG 引擎 (`python-rag/`)**：
   - 使用 FastAPI 提供 HTTP 檢索介面。
   - 負責資料載入、文本切塊、向量化、FAISS/BM25 索引建立與混合檢索邏輯。

2. **MCP Server (`mcp-server/`)**：
   - 使用 TypeScript 開發。
   - 作為中介層，將 LLM 傳入的 MCP 請求轉為對 Python RAG 引擎的呼叫，並將結果格式化為 Markdown 傳回給大模型。

---

## 🚀 快速開始

### 1. 系統需求
- **OS**: Windows (或其他支援的作業系統)
- **Python**: 3.10+
- **Node.js**: 18+
- **管理工具**: `uv` (新世代的 Python 依賴管理工具)
- **硬體建議**: 建議配備 NVidia GPU (支援 CUDA) 以加速向量化與 Rerank 處理，記憶體 16GB 以上。

### 2. 初始化與安裝

在專案根目錄下，我們提供了一個整合好的自動化腳本來設定 Python 與 Node.js 環境：

```cmd
scripts\setup.bat
```
該腳本將會：
- 檢查必要環境 (Python, Node.js, uv)
- 於 `python-rag` 內使用 `uv` 建立虛擬環境 (`.venv`) 並安裝依存套件。
- 於 `mcp-server` 內執行 `npm install` 並編譯 TypeScript (`npm run build`)。

### 3. 載入資料與建立索引 (Phase 2 & Phase 3)

初次使用時，請執行一鍵建立腳本來進行資料切塊與向量/關鍵字索引建立：

```cmd
# 確保位於專案根目錄
uv run scripts\build_index.py
```
> **提示**：這會需要一段時間進行 Embedding 計算，請耐心等候。

### 4. 啟動 Python FastAPI 服務

在啟動 MCP Server 前，必須先啟動後端的檢索搜尋引擎：

```cmd
cd python-rag
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 🧪 測試與驗證

執行我們提供的測試腳本，自動對幾個問題進行分類與檢索驗證（包含語義檢索、精確查找）：

```cmd
# 在專案根目錄執行
uv run scripts\test_query.py
```

預期能在 1.5 秒之內回傳查詢結果，例如查詢「加班費如何計算」時會將勞基法第 24 條等高相關結果排在最前面。

---

## 🔌 將 MCP Server 加入 Claude Desktop

設定檔位於：`%APPDATA%\Claude\claude_desktop_config.json`

在 JSON 中加入以下配置：

```json
{
  "mcpServers": {
    "taiwan-law": {
      "command": "node",
      "args": [
        "C:\\絕對路徑\\taiwan-law-rag-mcp\\mcp-server\\dist\\index.js"
      ],
      "env": {
        "RAG_API_URL": "http://localhost:8000"
      }
    }
  }
}
```
重啟 Claude Desktop 後即可透過對話直接使用台灣法規工具。

---

## 📄 授權

本專案供學習與開發交流用途，資料來源請遵循原提供者之相關授權條款。
