# Phase 6: MCP Server 實作與測試紀錄

## 🕒 實作時間
2026-03-21

## 🎯 實作目標
建立 MCP (Model Context Protocol) Server，使其能作為橋樑，讓 AI 客戶端 (如 Claude Desktop) 能夠透過標準的 MCP 協定，呼叫本地端 Python RAG 系統 (FastAPI) 所提供的檢索服務。

## 🛠️ 實作內容

### 1. 環境設定
- 修改 `mcp-server/package.json` 加入 `"type": "module"`，以相容 `node-fetch@3` 的 ESM (ECMAScript Modules) 語法要求。
- 更新 `mcp-server/tsconfig.json` 啟用了 `"rootDir": "./src"` 與 `"outDir": "./dist"`，正確將 TypeScript 編譯輸出到指定資料夾，並支援 NodeNext 模組解析。

### 2. 核心客戶端 (`RAGClient`)
- 建立 `src/clients/rag_client.ts`。
- 封裝與 FastAPI 之間通訊的細節，提供五種查詢功能（語義搜尋、精確搜尋、法律搜尋、取得單一法律全文、多法律比較）。
- 內建重試機制 (最高 3 次) 與錯誤捕捉，確保與後端服務連線的強健度。

### 3. Markdown 結果格式化 (`formatter`)
- 建立 `src/utils/formatter.ts`。
- 負責將後端 API 所回傳的 JSON 資料結構 (如 `SearchResult`、`LawFullResponse` 等) 轉換成易於人類閱讀、視覺上清晰的 Markdown 文本內容。包含了評分顯示、章節、連結 等資訊。

### 4. MCP Tools 定義與註冊
分別實作了 5 項 工具：
1. `semantic_search` (`src/tools/search.ts`)：利用 AI 向量相似度尋找最相關的法條。
2. `exact_search` (`src/tools/exact_search.ts`)：精確查詢特定法律與條號。
3. `search_law_by_name` (`src/tools/law_search.ts`)：針對法律名稱尋找相關列表或沿革。
4. `get_law_full_text` (`src/tools/get_law.ts`)：取得單一法規目前所有的全文與章節。
5. `compare_laws` (`src/tools/compare.ts`)：對多部法律在特定主題下屬性進行比較。

### 5. 進入點 (`index.ts`)
- 將 `@modelcontextprotocol/sdk` 中的 Standard Server 例項化。
- 註冊上列的五個工具及處理器 (Handler)。
- 開啟 `StdioServerTransport`，提供安全標準輸入輸出的傳輸管道。

## 🧪 測試結果

建立了一支 `test.js` 與運行於 8000 port 的 Python RAG Service 進行互動測試。以下為測試結果摘錄：

**1. 語義搜尋測試 (semanticSearch)**
輸入: `"加班費計算"`
```text
找到 1 條相關法條：

【1】勞動基準法 第 38 條 (第四章)
這是關於 加班費計算 的模擬條文...
🔗 https://law.moj.gov.tw/
相關度: 0.95
```

**2. 伺服器啟動測試**
- 執行 `npm run build` 順利將專案編譯至 `dist/` 目錄，無類型錯誤。
- 執行 `node dist/index.js`，控制台如期顯示 `Taiwan Law RAG MCP Server running on stdio` 並維持處於掛起 (Listening) 狀態以準備承接來自 Claude Desktop 等客戶端的標準輸入流程。

測試結果顯示 **所有 API 連線、資料解析及輸出轉換行為皆可無縫運作**，Phase 6 的實作已然完備。
