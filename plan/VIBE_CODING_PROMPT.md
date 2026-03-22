# 台灣法律 RAG MCP 系統 - Vibe Coding 提示詞

## 🎯 專案目標
建立一個台灣法律專用的 RAG MCP Server，整合 Qwen3 模型進行語義檢索，提供精準的法律條文查詢服務。

---

## 📋 專案規格

### 技術棧
```yaml
後端引擎 (Python):
  - Python: 3.10+
  - Framework: FastAPI
  - Vector DB: FAISS (主要) + ChromaDB (備用)
  - 全文檢索: Whoosh (BM25)
  - Embedding: Qwen/Qwen3-Embedding-4B (本地 GPU)
  - Reranker: Qwen/Qwen3-Reranker-4B (本地 GPU)
  - 分詞: jieba
  - 依賴: sentence-transformers, faiss-gpu, whoosh

MCP Server (TypeScript):
  - Runtime: Node.js 18+
  - Framework: @modelcontextprotocol/sdk
  - HTTP Client: node-fetch
  
環境:
  - OS: Windows
  - GPU: 有 (用於 Qwen3 模型)
  - 資料路徑: ./data/ChLaw.json
```

### 功能優先級
1. ⭐⭐⭐⭐⭐ 語義搜尋 (加班費計算規定)
2. ⭐⭐⭐⭐⭐ 精確條文查詢 (勞基法第38條)
3. ⭐⭐⭐⭐ 法律名稱搜尋 (支援別名，如勞基法→勞動基準法)
4. ⭐⭐⭐⭐ 取得完整法律
5. ⭐⭐⭐ 結果去重 (同一法律最多 3 條)
6. ⭐⭐ 快取機制 (LRU Cache)
7. ⭐ 法律比較功能

### 輸出格式
```typescript
interface SearchResult {
  law_name: string;          // 法律名稱
  law_level: string;         // 法律層級 (憲法/法律)
  law_category: string;      // 法律類別
  law_url: string;           // 官方連結
  article_no: string;        // 條號 (如: "第 38 條")
  chapter: string;           // 章節
  content: string;           // 條文內容
  score: number;             // 相關度分數
  modified_date: string;     // 修正日期
}
```

---

## 📁 專案結構

```
taiwan-law-rag-mcp/
├── README.md                      # 專案說明
├── .env.example                   # 環境變數範例
├── .gitignore
│
├── data/                          # 資料目錄
│   └── ChLaw.json                 # 原始法律資料 (25MB, 1343部法律)
│
├── python-rag/                    # Python RAG 引擎
│   ├── requirements.txt           # Python 依賴
│   ├── config.py                  # 配置檔
│   ├── main.py                    # FastAPI 主程式
│   │
│   ├── data_processing/           # 資料處理模組
│   │   ├── __init__.py
│   │   ├── loader.py              # 載入 ChLaw.json
│   │   ├── chunker.py             # 條文級切塊 (→ 55k chunks)
│   │   ├── metadata_enricher.py  # 擴充 metadata
│   │   └── law_aliases.py         # 法律別名對照表
│   │
│   ├── indexing/                  # 索引建立模組
│   │   ├── __init__.py
│   │   ├── embedder.py            # Qwen3-Embedding-4B 向量化
│   │   ├── faiss_indexer.py      # FAISS 索引建立 (HNSW+IVF)
│   │   ├── bm25_indexer.py       # Whoosh BM25 索引
│   │   └── rebuild_index.py       # 重建索引腳本
│   │
│   ├── retrieval/                 # 檢索模組
│   │   ├── __init__.py
│   │   ├── query_classifier.py   # 查詢分類 (精確/語義)
│   │   ├── vector_retriever.py   # FAISS 向量檢索
│   │   ├── bm25_retriever.py     # BM25 檢索
│   │   ├── hybrid_retriever.py   # 混合檢索 (RRF 融合)
│   │   ├── reranker.py            # Qwen3-Reranker-4B 重排序
│   │   └── deduplicator.py        # 結果去重 (同法律最多3條)
│   │
│   ├── api/                       # API 路由
│   │   ├── __init__.py
│   │   ├── routes.py              # FastAPI 路由定義
│   │   ├── models.py              # Pydantic 資料模型
│   │   └── cache.py               # LRU Cache 實作
│   │
│   ├── utils/                     # 工具函數
│   │   ├── __init__.py
│   │   ├── article_parser.py     # 條號正規化
│   │   ├── law_name_normalizer.py # 法律名稱正規化
│   │   └── logger.py              # 日誌配置
│   │
│   └── tests/                     # 測試
│       ├── test_retrieval.py
│       └── test_api.py
│
├── mcp-server/                    # MCP Server
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── index.ts               # MCP Server 主程式
│   │   ├── tools/                 # MCP Tools 定義
│   │   │   ├── search.ts          # 語義搜尋
│   │   │   ├── exact_search.ts    # 精確條文查詢
│   │   │   ├── law_search.ts      # 法律名稱搜尋
│   │   │   ├── get_law.ts         # 取得完整法律
│   │   │   └── compare.ts         # 法律比較
│   │   ├── clients/
│   │   │   └── rag_client.ts      # 呼叫 Python RAG API
│   │   └── utils/
│   │       ├── formatter.ts       # 格式化輸出
│   │       └── error_handler.ts   # 錯誤處理
│   │
│   └── dist/                      # 編譯輸出
│
├── scripts/                       # 腳本工具
│   ├── setup.bat                  # Windows 初始化腳本
│   ├── build_index.py             # 建立索引
│   ├── test_query.py              # 測試查詢
│   └── update_data.py             # 更新資料
│
└── docs/                          # 文檔
    ├── INSTALLATION.md            # 安裝指南
    ├── USAGE.md                   # 使用說明
    └── API.md                     # API 文檔
```

---

## 🔧 核心技術實作細節

### 1. 資料處理 (data_processing/)

#### chunker.py - 條文級切塊策略
```python
"""
切塊策略: 條文級 (Article-Level Chunking)

輸入: ChLaw.json (1343 部法律, 51107 條)
輸出: ~55,000 chunks

每個 chunk:
{
  "id": "勞動基準法_第38條",
  "content": "勞工在同一雇主或事業單位...",
  "metadata": {
    "law_name": "勞動基準法",
    "law_level": "法律",
    "law_category": "行政>勞動部>勞動條件及就業平等目",
    "law_url": "https://law.moj.gov.tw/...",
    "article_no": "第 38 條",
    "chapter": "第四章 工作時間、休息、休假",
    "modified_date": "20180621",
    "is_abolished": false,
    "has_english": true
  }
}

處理邏輯:
1. 遍歷每部法律的 LawArticles
2. ArticleType == "C" → 記錄章節標題 (作為 context)
3. ArticleType == "A" → 創建 chunk
4. 長條文 (>500字) → 按段落拆分 (保留條號資訊)
5. 擴充 metadata (aliases, keywords)
"""
```

#### law_aliases.py - 法律別名對照表
```python
"""
法律別名對照表 (台灣常用口語)

功能:
- 將口語名稱轉換為正式法律名稱
- 支援模糊匹配

範例:
"勞基法" → "勞動基準法"
"健保法" → "全民健康保險法"
"公司法" → "公司法"
"證交法" → "證券交易法"
"民法" → "民法"
"刑法" → "中華民國刑法"

實作:
LAW_ALIASES = {
    "勞基法": "勞動基準法",
    "勞保條例": "勞工保險條例",
    # ... 約 50-100 個常用別名
}
"""
```

---

### 2. 索引建立 (indexing/)

#### embedder.py - Qwen3 向量化
```python
"""
使用 Qwen3-Embedding-4B 進行向量化

模型規格:
- 模型: Qwen/Qwen3-Embedding-4B
- 維度: 4096
- Max Tokens: 8192
- 語言: 支援繁體中文

批次處理:
- batch_size: 64 (根據 GPU VRAM 調整)
- 進度條: tqdm
- 錯誤處理: 失敗重試 3 次

優化:
- 文本增強: 包含法律名稱、條號、章節
  格式: "法律: {law_name}\n條號: {article_no}\n內容: {content}"
- GPU 加速: device='cuda'
- 正規化: normalize_embeddings=True

輸出:
- embeddings.npy: (55000, 4096) numpy array
- chunk_ids.json: chunk ID 對照表
"""
```

#### faiss_indexer.py - FAISS 索引
```python
"""
FAISS 索引建立 (高性能向量檢索)

索引類型: HNSW + IVF 混合
- IndexIVFPQ: 倒排檔案 + 乘積量化
- HNSW: 近似最近鄰搜尋

參數:
- nlist: 100 (聚類數量)
- m: 32 (HNSW 連接數)
- nbits: 8 (PQ 量化位元)

建立流程:
1. 載入 embeddings (4096 維)
2. 訓練量化器 (使用全部向量)
3. 添加向量到索引
4. 保存索引: taiwan_law.faiss
5. 保存 chunk metadata: chunks.pkl

檢索性能:
- 55k 向量
- 查詢時間: <50ms
- Recall@10: >95%
"""
```

#### bm25_indexer.py - BM25 全文檢索
```python
"""
Whoosh BM25 索引 (關鍵字檢索)

Schema:
- chunk_id: ID (唯一)
- law_name: TEXT (中文分詞)
- article_no: ID (條號)
- content: TEXT (中文分詞, 主要檢索欄位)
- chapter: TEXT (章節)
- category: KEYWORD (法律類別)

中文分詞:
- 使用 jieba 分詞
- 自訂詞典: 加入法律專業詞彙

建立流程:
1. 定義 Schema
2. 創建索引目錄
3. 批次添加文檔 (1000/batch)
4. commit 並優化

檢索優勢:
- 精確關鍵字匹配
- 補足向量檢索的不足 (專有名詞、條號)
"""
```

---

### 3. 檢索模組 (retrieval/)

#### query_classifier.py - 查詢分類
```python
"""
查詢分類器: 區分精確查詢 vs 語義查詢

分類邏輯:

1. 精確查詢 (Exact Query):
   - 包含條號: "勞基法第38條", "民法 184"
   - 包含法律名稱 + 關鍵字: "公司法股東會"
   - 正則匹配: r'第\s*\d+\s*條'
   
   處理策略:
   → 直接查詢 (法律名稱 + 條號 filter)
   → 跳過向量檢索 (節省時間)

2. 語義查詢 (Semantic Query):
   - 法律問題: "加班費如何計算"
   - 情境描述: "員工離職後競業禁止"
   
   處理策略:
   → 混合檢索 (Vector + BM25)
   → Reranking

返回:
{
  "type": "exact" | "semantic",
  "law_name": str | None,  # 提取的法律名稱
  "article_no": str | None  # 提取的條號
}
"""
```

#### hybrid_retriever.py - 混合檢索
```python
"""
混合檢索: Vector Search + BM25

Pipeline:
1. 並行檢索:
   - Vector: FAISS (Top-30)
   - BM25: Whoosh (Top-30)

2. 分數融合 (Reciprocal Rank Fusion):
   RRF(d) = Σ 1/(k + rank_i(d))
   - k = 60 (常數)
   - rank_i(d): 文檔 d 在第 i 個檢索器的排名

3. 合併去重

4. 重排序 (Qwen3-Reranker):
   - Top-20 進入 Cross-Encoder
   - 計算 query-document 相關度分數
   - 重新排序

5. 法律去重:
   - 同一部法律最多保留 3 條
   - 確保結果多樣性

6. 返回 Top-10

參數:
- alpha: Vector 權重 (0.5 = 平衡)
- max_per_law: 每部法律最多條數 (3)
"""
```

#### reranker.py - Qwen3 重排序
```python
"""
使用 Qwen3-Reranker-4B 進行重排序

模型: Qwen/Qwen3-Reranker-4B
架構: Cross-Encoder (BERT-style)

輸入: [(query, doc1), (query, doc2), ...]
輸出: [score1, score2, ...]  # 0-1 之間

優點:
- 完整的 query-document attention
- 精度比 Bi-Encoder 高 +40%

缺點:
- 速度慢 (無法預計算)
- 只用於 Top-K 重排序

使用:
1. 初步檢索得到 Top-20
2. Cross-Encoder 計算精確分數
3. 重新排序得到 Top-10

批次處理:
- batch_size: 32
- GPU 加速
"""
```

---

### 4. API 路由 (api/)

#### routes.py - FastAPI 路由定義
```python
"""
FastAPI 路由定義

端點:
1. POST /search/semantic
   - 語義搜尋
   - 請求: {"query": str, "top_k": int, "filter_category": str}
   - 返回: {"results": [SearchResult], "total": int, "query_time": float}

2. POST /search/exact
   - 精確條文查詢
   - 請求: {"query": str}  # "勞基法第38條"
   - 返回: {"results": [SearchResult]}

3. POST /search/law
   - 法律名稱搜尋
   - 請求: {"law_name": str, "include_abolished": bool}
   - 返回: {"results": [SearchResult]}

4. POST /law/full
   - 取得完整法律
   - 請求: {"law_name": str}
   - 返回: {"law": Law, "articles": [Article]}

5. POST /law/compare
   - 法律比較
   - 請求: {"law_names": [str], "topic": str}
   - 返回: {"comparison": {law_name: [Article]}}

6. POST /index/rebuild
   - 重建索引
   - 請求: {"force": bool}
   - 返回: {"status": str, "chunks": int, "time": float}

中間件:
- CORS: 允許 localhost
- 日誌: 記錄所有請求
- 錯誤處理: 統一格式
"""
```

#### cache.py - LRU Cache
```python
"""
LRU Cache 快取機制

使用 functools.lru_cache + 自訂持久化

策略:
- 記憶體快取: 100 個查詢
- 過期時間: 1 小時
- 快取鍵: hash(query + filters)

實作:
class QueryCache:
    def __init__(self, maxsize=100, ttl=3600):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                self.cache.move_to_end(key)  # LRU
                return value
        return None
    
    def set(self, key, value):
        # 移除過期項目
        # 加入新項目
        # 維持 maxsize

效能提升:
- 冷啟動: 1.5 秒
- 快取命中: 0.05 秒 (30x 加速)
"""
```

---

### 5. MCP Server (mcp-server/)

#### index.ts - MCP Server 主程式
```typescript
"""
MCP Server 主程式

初始化:
1. 載入配置 (RAG API URL)
2. 註冊 5 個 Tools
3. 啟動 stdio transport

Tools:
- semantic_search: 語義搜尋
- exact_search: 精確條文查詢
- search_law_by_name: 法律名稱搜尋
- get_law_full_text: 取得完整法律
- compare_laws: 法律比較

錯誤處理:
- RAG API 連線失敗 → 友善錯誤訊息
- 超時處理 (30秒)
- 重試機制 (3次)

日誌:
- 記錄所有工具呼叫
- 性能監控
"""
```

#### tools/search.ts - 語義搜尋工具
```typescript
"""
語義搜尋 MCP Tool

定義:
{
  name: "semantic_search",
  description: "根據法律問題或關鍵字進行語義搜尋",
  inputSchema: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "法律問題或關鍵字，例如：加班費計算規定"
      },
      top_k: {
        type: "number",
        description: "返回結果數量",
        default: 10
      },
      filter_category: {
        type: "string",
        description: "過濾法律類別（可選）"
      }
    },
    required: ["query"]
  }
}

實作:
async function semanticSearch(args) {
  // 1. 呼叫 RAG API
  const response = await fetch('http://localhost:8000/search/semantic', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(args)
  });
  
  // 2. 解析結果
  const data = await response.json();
  
  // 3. 格式化輸出
  return {
    content: [{
      type: "text",
      text: formatSearchResults(data.results)
    }]
  };
}

輸出格式:
```
找到 10 條相關法條：

【1】勞動基準法 第 38 條 (第四章 工作時間、休息、休假)
勞工在同一雇主或事業單位，繼續工作滿一定期間者，應依下列規定給予特別休假...
🔗 https://law.moj.gov.tw/...
相關度: 0.95

【2】勞動基準法 第 24 條 (第四章 工作時間、休息、休假)
...
```
"""
```

---

## 🚀 實作步驟指引

### Phase 1: 環境設置 (30分鐘)

1. **建立專案結構**
```bash
mkdir taiwan-law-rag-mcp
cd taiwan-law-rag-mcp
mkdir -p data python-rag mcp-server scripts docs
```

2. **準備 Python 環境 (使用 uv)**
```bash
# 在專案根目錄 (taiwan-law-rag-mcp) 下執行
uv init
uv add -r python-rag/requirements.txt
```

requirements.txt (位於 `python-rag/requirements.txt`):
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sentence-transformers>=2.2.2
faiss-gpu==1.7.2  # 或 faiss-cpu 如果沒有 GPU
whoosh==2.7.4
jieba==0.42.1
numpy==1.24.3
pydantic==2.5.0
python-multipart==0.0.6
```

3. **準備 Node.js 環境**
```bash
cd ../mcp-server
npm init -y
npm install @modelcontextprotocol/sdk node-fetch
npm install -D typescript @types/node
npx tsc --init
```

---

### Phase 2: 資料處理 (2小時)

**檔案建立順序:**

1. `python-rag/data_processing/loader.py`
   - 載入 ChLaw.json
   - 處理 UTF-8 BOM
   - 驗證資料結構

2. `python-rag/data_processing/law_aliases.py`
   - 定義法律別名對照表
   - 實作正規化函數

3. `python-rag/data_processing/metadata_enricher.py`
   - 擴充 metadata
   - 提取關鍵字

4. `python-rag/data_processing/chunker.py`
   - 條文級切塊
   - 處理長條文
   - 生成 chunk ID

5. `python-rag/utils/article_parser.py`
   - 條號正規化
   - 正則匹配

**測試點:**
- 產生 55,000 chunks
- 每個 chunk 包含完整 metadata
- 驗證 chunk ID 唯一性

---

### Phase 3: 索引建立 (3小時)

**檔案建立順序:**

1. `python-rag/indexing/embedder.py`
   - 載入 Qwen3-Embedding-4B
   - 批次向量化
   - 保存 embeddings.npy

2. `python-rag/indexing/faiss_indexer.py`
   - 建立 FAISS 索引
   - HNSW + IVF 混合
   - 保存索引檔案

3. `python-rag/indexing/bm25_indexer.py`
   - 建立 Whoosh 索引
   - 中文分詞
   - 批次添加文檔

4. `python-rag/indexing/rebuild_index.py`
   - 整合完整索引建立流程
   - CLI 介面
   - 進度顯示

**測試點:**
- FAISS 索引: 55k 向量
- BM25 索引: 55k 文檔
- 檢索速度: <100ms

---

### Phase 4: 檢索引擎 (4小時)

**檔案建立順序:**

1. `python-rag/retrieval/query_classifier.py`
   - 精確 vs 語義分類
   - 正則匹配條號

2. `python-rag/retrieval/vector_retriever.py`
   - FAISS 檢索
   - 相似度計算

3. `python-rag/retrieval/bm25_retriever.py`
   - Whoosh 檢索
   - 分詞處理

4. `python-rag/retrieval/hybrid_retriever.py`
   - RRF 融合
   - 並行檢索

5. `python-rag/retrieval/reranker.py`
   - Qwen3-Reranker-4B
   - 批次重排序

6. `python-rag/retrieval/deduplicator.py`
   - 法律去重
   - 最多 3 條/法律

**測試點:**
- Recall@10 > 90%
- Precision@10 > 80%
- 查詢時間 < 1.5 秒

---

### Phase 5: FastAPI 服務 (2小時)

**檔案建立順序:**

1. `python-rag/api/models.py`
   - Pydantic 資料模型
   - 請求/回應格式

2. `python-rag/api/cache.py`
   - LRU Cache 實作
   - TTL 機制

3. `python-rag/api/routes.py`
   - 6 個 API 端點
   - 錯誤處理

4. `python-rag/main.py`
   - FastAPI app
   - CORS 配置
   - 啟動邏輯

**測試點:**
- 啟動服務: `uvicorn main:app --host 0.0.0.0 --port 8000`
- 測試 API: `curl http://localhost:8000/search/semantic`
- 效能: 1000 req/s

---

### Phase 6: MCP Server (2小時)

**檔案建立順序:**

1. `mcp-server/src/clients/rag_client.ts`
   - HTTP 客戶端
   - 重試機制

2. `mcp-server/src/utils/formatter.ts`
   - 格式化輸出
   - Markdown 渲染

3. `mcp-server/src/tools/search.ts`
   - semantic_search 工具

4. `mcp-server/src/tools/exact_search.ts`
   - exact_search 工具

5. `mcp-server/src/tools/law_search.ts`
   - search_law_by_name 工具

6. `mcp-server/src/tools/get_law.ts`
   - get_law_full_text 工具

7. `mcp-server/src/tools/compare.ts`
   - compare_laws 工具

8. `mcp-server/src/index.ts`
   - MCP Server 主程式
   - 工具註冊

**測試點:**
- 編譯: `npm run build`
- 測試連線
- Claude Desktop 整合

---

### Phase 7: 整合測試 (1小時)

**檔案建立順序:**

1. `scripts/setup.bat`
   - Windows 初始化
   - 環境檢查

2. `scripts/build_index.py`
   - 一鍵建立索引

3. `scripts/test_query.py`
   - 測試查詢腳本

4. `README.md`
   - 完整說明文檔

**測試案例:**
```python
# 1. 語義搜尋
"加班費如何計算" → 勞基法第24條

# 2. 精確查詢
"勞基法第38條" → 特別休假

# 3. 法律別名
"勞基法" → 勞動基準法

# 4. 法律比較
["民法", "公司法"], "股東權利"
```

---

## 💻 Cursor/Windsurf 使用指南

### 建議的 Prompt 順序

#### 1️⃣ 建立專案結構
```
請根據上面的專案結構，建立所有目錄和空白檔案。
使用 Windows 批次檔 (setup.bat) 自動建立。
```

#### 2️⃣ 資料處理模組
```
實作 python-rag/data_processing/loader.py，
功能:
1. 載入 ./data/ChLaw.json (處理 UTF-8 BOM)
2. 驗證資料結構 (1343 部法律)
3. 提供迭代器介面

參考上面的技術規格。
```

#### 3️⃣ 切塊模組
```
實作 python-rag/data_processing/chunker.py，
使用條文級切塊策略，
輸出 ~55,000 chunks，
每個 chunk 包含完整 metadata。

參考上面的切塊策略說明。
```

#### 4️⃣ 向量化模組
```
實作 python-rag/indexing/embedder.py，
使用 Qwen/Qwen3-Embedding-4B，
批次處理 (batch_size=64)，
保存為 embeddings.npy。

GPU 加速，顯示進度條。
```

#### 5️⃣ FAISS 索引
```
實作 python-rag/indexing/faiss_indexer.py，
使用 HNSW + IVF 混合索引，
參數: nlist=100, m=32, nbits=8。

保存為 taiwan_law.faiss。
```

#### 6️⃣ 混合檢索
```
實作 python-rag/retrieval/hybrid_retriever.py，
結合 Vector Search 和 BM25，
使用 RRF 融合，
整合 Qwen3-Reranker-4B。

返回 Top-10 結果。
```

#### 7️⃣ FastAPI 服務
```
實作 python-rag/main.py 和 api/routes.py，
提供 6 個 API 端點，
包含 LRU Cache，
CORS 支援。

啟動: uvicorn main:app
```

#### 8️⃣ MCP Server
```
實作 mcp-server/src/index.ts，
註冊 5 個 MCP Tools，
呼叫 Python RAG API (http://localhost:8000)，
格式化輸出為 Markdown。

使用 @modelcontextprotocol/sdk。
```

---

## 🎨 Cursor Composer 技巧

### 1. 使用 @-mentions
```
@loader.py @chunker.py 
請確保這兩個檔案的介面相容，
loader 提供的資料格式要能被 chunker 處理。
```

### 2. 分階段實作
```
只實作 semantic_search 功能，
暫時不要實作其他 4 個工具。
測試通過後再繼續。
```

### 3. 參考現有檔案
```
參考 @embedder.py 的批次處理邏輯，
在 @reranker.py 中實作類似的批次重排序。
```

### 4. 測試驅動
```
先寫 @test_retrieval.py 的測試案例，
再實作 @hybrid_retriever.py 讓測試通過。
```

---

## 📊 效能指標

### 索引建立
- 資料載入: ~5 秒
- 切塊處理: ~30 秒
- 向量化: ~10 分鐘 (GPU)
- FAISS 索引: ~2 分鐘
- BM25 索引: ~1 分鐘
- **總計: ~15 分鐘**

### 查詢效能
- 精確查詢: <50 ms
- 語義搜尋: <1.5 秒
  - Vector Search: ~100 ms
  - BM25 Search: ~50 ms
  - Reranking: ~800 ms
  - 其他: ~200 ms
- 快取命中: <50 ms

### 記憶體使用
- FAISS 索引: ~2 GB
- Qwen3-Embedding: ~8 GB (GPU)
- Qwen3-Reranker: ~8 GB (GPU)
- Python 程序: ~1 GB
- **總計: ~20 GB (GPU VRAM + RAM)**

---

## ⚠️ 常見問題

### Q1: GPU 記憶體不足
**A:** 降低 batch_size
```python
# embedder.py
batch_size = 32  # 從 64 降低到 32
```

### Q2: FAISS 索引太慢
**A:** 使用較小的索引
```python
# faiss_indexer.py
nlist = 50  # 從 100 降低到 50
```

### Q3: Reranker 太慢
**A:** 減少重排序的文檔數
```python
# hybrid_retriever.py
rerank_top_k = 10  # 從 20 降低到 10
```

### Q4: BM25 中文分詞不準
**A:** 添加自訂詞典
```python
# bm25_indexer.py
jieba.load_userdict('law_terms.txt')
```

---

## 🔍 Debug 指南

### 檢查點 1: 資料載入
```python
from data_processing.loader import load_law_data
data = load_law_data('./data/ChLaw.json')
print(f"載入 {len(data['Laws'])} 部法律")  # 應為 1343
```

### 檢查點 2: 切塊
```python
from data_processing.chunker import chunk_laws
chunks = chunk_laws(data['Laws'])
print(f"產生 {len(chunks)} 個 chunks")  # 應約 55000
print(chunks[0])  # 檢查格式
```

### 檢查點 3: 向量化
```python
from indexing.embedder import embed_chunks
embeddings = embed_chunks(chunks[:100])  # 測試 100 個
print(embeddings.shape)  # 應為 (100, 4096)
```

### 檢查點 4: FAISS 檢索
```python
from retrieval.vector_retriever import VectorRetriever
retriever = VectorRetriever.load('taiwan_law.faiss')
results = retriever.search("加班費", top_k=5)
print(results)
```

### 檢查點 5: API 測試
```bash
# 啟動服務
cd python-rag
uvicorn main:app --reload

# 測試 (另一個終端)
curl -X POST http://localhost:8000/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "加班費計算", "top_k": 5}'
```

### 檢查點 6: MCP Server 測試
```bash
cd mcp-server
npm run build
node dist/index.js
# 在 Claude Desktop 中測試
```

---

## 📝 Claude Desktop 配置

### Windows 配置檔位置
```
%APPDATA%\Claude\claude_desktop_config.json
```

### 配置內容
```json
{
  "mcpServers": {
    "taiwan-law": {
      "command": "node",
      "args": [
        "C:\\path\\to\\taiwan-law-rag-mcp\\mcp-server\\dist\\index.js"
      ],
      "env": {
        "RAG_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

### 使用範例
在 Claude Desktop 中:
```
請使用台灣法律工具，搜尋「加班費計算規定」
```

Claude 會自動呼叫 MCP Tool:
```typescript
semantic_search({
  query: "加班費計算規定",
  top_k: 10
})
```

---

## ✅ 完成檢查清單

### Phase 1: 資料處理 ✅
- [ ] ChLaw.json 載入成功
- [ ] 產生 55,000 chunks
- [ ] Metadata 完整

### Phase 2: 索引建立 ✅
- [ ] Qwen3-Embedding 向量化
- [ ] FAISS 索引建立
- [ ] BM25 索引建立

### Phase 3: 檢索引擎 ✅
- [ ] 混合檢索運作
- [ ] Reranking 整合
- [ ] 去重機制

### Phase 4: API 服務 ✅
- [ ] 6 個端點正常
- [ ] Cache 運作
- [ ] 錯誤處理

### Phase 5: MCP Server ✅
- [ ] 5 個工具註冊
- [ ] Claude Desktop 整合
- [ ] 格式化輸出

### Phase 6: 測試 ✅
- [ ] 語義搜尋測試
- [ ] 精確查詢測試
- [ ] 效能達標

---

## 🎉 預期成果

### 使用體驗
```
用戶: 加班費怎麼計算?

Claude: [呼叫 semantic_search]

找到 3 條相關法條：

【1】勞動基準法 第 24 條 (第四章 工作時間、休息、休假)
雇主延長勞工工作時間者，其延長工作時間之工資，依下列標準加給：
一、延長工作時間在二小時以內者，按平日每小時工資額加給三分之一以上。
二、再延長工作時間在二小時以內者，按平日每小時工資額加給三分之二以上。
三、依第三十二條第四項規定，延長工作時間者，按平日每小時工資額加倍發給。
🔗 https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0030001
相關度: 0.96

【2】勞動基準法 第 32 條 (第四章 工作時間、休息、休假)
...

根據勞動基準法第 24 條，加班費的計算方式為：
- 前 2 小時：平日時薪 × 1.34
- 第 3-4 小時：平日時薪 × 1.67
- 例假日或休息日：平日時薪 × 2
```

---

這份提示詞包含了完整的實作細節，可以直接貼給 Cursor/Windsurf 開始 vibe coding！

需要我解釋任何部分嗎？或者你想先從哪個模組開始實作？
