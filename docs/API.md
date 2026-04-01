# Taiwan Law RAG — API 參考文件

Base URL：`http://127.0.0.1:8073`

所有 request body 均為 `application/json`，所有 response 均為 `application/json`。

---

## 目錄

- [搜尋類](#搜尋類)
  - [POST /search/semantic](#post-searchsemantic)
  - [POST /search/exact](#post-searchexact)
  - [POST /search/law](#post-searchlaw)
- [法律條文類](#法律條文類)
  - [POST /law/full](#post-lawfull)
  - [POST /law/compare](#post-lawcompare)
- [問答類](#問答類)
  - [POST /chat](#post-chat)
- [Session API](#session-api)
  - [POST /session](#post-session)
  - [POST /session/{id}/chat](#post-sessionidchat)
  - [DELETE /session/{id}](#delete-sessionid)
- [健康檢查](#健康檢查)
  - [GET /health](#get-health)
- [錯誤回應](#錯誤回應)

---

## 共用 Schema

### SearchResult

| 欄位 | 型別 | 說明 |
|---|---|---|
| `law_name` | string | 法律名稱 |
| `law_level` | string | 法律層級（憲法 / 法律） |
| `law_category` | string | 法律類別 |
| `law_url` | string | 官方連結 |
| `article_no` | string | 條號，例如 `第 38 條` |
| `chapter` | string | 章節 |
| `content` | string | 條文內容 |
| `score` | number \| null | 相關度分數 |
| `modified_date` | string | 修正日期 |

### Citation

| 欄位 | 型別 | 說明 |
|---|---|---|
| `law_name` | string | 法律名稱 |
| `article_no` | string | 條號 |

---

## 搜尋類

### POST /search/semantic

語義向量搜尋，依語意相似度找出最相關的法律條文。

**Request Body**

| 欄位 | 型別 | 必填 | 預設 | 說明 |
|---|---|---|---|---|
| `query` | string | ✓ | — | 搜尋關鍵字或問題 |
| `top_k` | integer | | 10 | 返回結果數量 |
| `filter_category` | string \| null | | null | 過濾法律類別（可選） |

**Response Schema（HTTP 200）**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `results` | SearchResult[] | 搜尋結果列表 |
| `total` | integer | 結果總數 |
| `query_time` | number | 查詢耗時（秒） |

**Request 範例**

```json
{
  "query": "加班費計算規定",
  "top_k": 3,
  "filter_category": null
}
```

**Response 範例**

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
      "score": 0.912,
      "modified_date": "2023-06-28"
    }
  ],
  "total": 1,
  "query_time": 0.043
}
```

**HTTP 狀態碼**

| 狀態碼 | 說明 |
|---|---|
| 200 | 成功 |
| 422 | 請求格式錯誤（缺少必填欄位或型別錯誤） |
| 500 | 伺服器內部錯誤 |

---

### POST /search/exact

精確條文查詢，依法律名稱與條號進行 BM25 關鍵字搜尋。

**Request Body**

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `query` | string | ✓ | 精確搜尋查詢句，例如：`勞基法第38條` |

**Response Schema（HTTP 200）**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `results` | SearchResult[] | 搜尋結果列表 |

**Request 範例**

```json
{
  "query": "勞基法第38條"
}
```

**Response 範例**

```json
{
  "results": [
    {
      "law_name": "勞動基準法",
      "law_level": "法律",
      "law_category": "勞動",
      "law_url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0030001",
      "article_no": "第 38 條",
      "chapter": "第四章 工作時間、休息、休假",
      "content": "勞工在同一雇主或事業單位，繼續工作滿一定期間者，應依下列規定給予特別休假...",
      "score": null,
      "modified_date": "2023-06-28"
    }
  ]
}
```

**HTTP 狀態碼**

| 狀態碼 | 說明 |
|---|---|
| 200 | 成功 |
| 422 | 請求格式錯誤 |
| 500 | 伺服器內部錯誤 |

---

### POST /search/law

依法律名稱搜尋，找出符合名稱的法律列表。

**Request Body**

| 欄位 | 型別 | 必填 | 預設 | 說明 |
|---|---|---|---|---|
| `law_name` | string | ✓ | — | 法律名稱或關鍵字 |
| `include_abolished` | boolean | | false | 是否包含已廢止法律 |

**Response Schema（HTTP 200）**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `results` | SearchResult[] | 搜尋結果列表 |

**Request 範例**

```json
{
  "law_name": "勞動基準法",
  "include_abolished": false
}
```

**Response 範例**

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

**HTTP 狀態碼**

| 狀態碼 | 說明 |
|---|---|
| 200 | 成功 |
| 422 | 請求格式錯誤 |
| 500 | 伺服器內部錯誤 |

---

## 法律條文類

### POST /law/full

取得指定法律的完整條文內容。

**Request Body**

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `law_name` | string | ✓ | 法律完整名稱，例如：`勞動基準法` |

**Response Schema（HTTP 200）**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `law` | Law | 法律基本資訊 |
| `articles` | Article[] | 所有條文列表 |

**Law 物件**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `law_name` | string | 法律名稱 |
| `law_level` | string | 法律層級 |
| `law_category` | string | 法律類別 |
| `law_url` | string | 官方連結 |
| `modified_date` | string | 修正日期 |
| `is_abolished` | boolean | 是否已廢止 |

**Article 物件**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `article_no` | string | 條號 |
| `content` | string | 條文內容 |
| `chapter` | string | 所屬章節 |

**Request 範例**

```json
{
  "law_name": "勞動基準法"
}
```

**Response 範例**

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
      "article_no": "第 38 條",
      "content": "勞工在同一雇主或事業單位，繼續工作滿一定期間者，應依下列規定給予特別休假...",
      "chapter": "第四章 工作時間、休息、休假"
    }
  ]
}
```

**HTTP 狀態碼**

| 狀態碼 | 說明 |
|---|---|
| 200 | 成功 |
| 422 | 請求格式錯誤 |
| 500 | 伺服器內部錯誤 |

---

### POST /law/compare

比較多部法律在指定主題下的相關條文差異。

**Request Body**

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `law_names` | string[] | ✓ | 要比較的法律名稱列表（至少兩部） |
| `topic` | string | ✓ | 比較主題或關鍵字 |

**Response Schema（HTTP 200）**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `comparison` | object | 以法律名稱為 key，相關條文列表（Article[]）為 value 的對應表 |

**Request 範例**

```json
{
  "law_names": ["民法", "公司法"],
  "topic": "股東權利"
}
```

**Response 範例**

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

**HTTP 狀態碼**

| 狀態碼 | 說明 |
|---|---|
| 200 | 成功 |
| 422 | 請求格式錯誤 |
| 500 | 伺服器內部錯誤 |

---

## 問答類

### POST /chat

完整 RAG 問答，結合語義檢索與 LLM 生成，回傳法律問題的自然語言答案與引用條文。

**Request Body**

| 欄位 | 型別 | 必填 | 預設 | 限制 | 說明 |
|---|---|---|---|---|---|
| `question` | string | ✓ | — | 最少 1 字元 | 法律問題 |
| `top_k` | integer | | 5 | 1–50 | retrieval 條文數量 |

**Response Schema（HTTP 200）**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `answer` | string | LLM 生成的自然語言答案 |
| `citations` | Citation[] | 引用的法律條文列表 |
| `query_time` | number | 查詢耗時（秒） |

**Request 範例**

```json
{
  "question": "員工被資遣時可以領到哪些補償？",
  "top_k": 5
}
```

**Response 範例**

```json
{
  "answer": "依據勞動基準法，員工遭資遣時可領取資遣費。工作年資每滿一年發給相當於一個月平均工資之資遣費，未滿一年者以比例計算，最高以六個月平均工資為限（勞基法第17條）。此外，雇主應依規定預告期間通知勞工，或給付預告期間工資（勞基法第16條）。",
  "citations": [
    {
      "law_name": "勞動基準法",
      "article_no": "第 16 條"
    },
    {
      "law_name": "勞動基準法",
      "article_no": "第 17 條"
    }
  ],
  "query_time": 2.341
}
```

**HTTP 狀態碼**

| 狀態碼 | 說明 |
|---|---|
| 200 | 成功 |
| 422 | 請求格式錯誤 |
| 503 | Generation 服務不可用（LLM 未啟動或連線失敗） |

---

## Session API

Session API 支援多輪對話，系統會自動記憶對話歷史並解析指代詞（如「這條法律」、「它」）。

- Session TTL：30 分鐘無活動後自動清除
- 每個 Session 最多保留最近 10 輪對話

### POST /session

建立新的對話 Session。

**Request Body**

無（空 body 或省略）。

**Response Schema（HTTP 200）**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `session_id` | string | Session 唯一識別碼（UUID v4） |

**Request 範例**

```bash
curl -X POST http://127.0.0.1:8073/session
```

**Response 範例**

```json
{
  "session_id": "a3f2c1d4-8e7b-4f9a-b2c3-1d4e5f6a7b8c"
}
```

**HTTP 狀態碼**

| 狀態碼 | 說明 |
|---|---|
| 200 | 成功，回傳新 session_id |
| 500 | 伺服器內部錯誤 |

---

### POST /session/{id}/chat

在指定 Session 中進行對話，系統會結合歷史對話上下文處理問題。

**路徑參數**

| 參數 | 型別 | 說明 |
|---|---|---|
| `id` | string | Session ID（由 `POST /session` 取得） |

**Request Body**

| 欄位 | 型別 | 必填 | 預設 | 限制 | 說明 |
|---|---|---|---|---|---|
| `question` | string | ✓ | — | 最少 1 字元 | 法律問題 |
| `top_k` | integer | | 5 | 1–50 | retrieval 條文數量 |

**Response Schema（HTTP 200）**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `answer` | string | LLM 生成的自然語言答案 |
| `citations` | Citation[] | 引用的法律條文列表 |
| `query_time` | number | 查詢耗時（秒） |
| `session_id` | string | 本次對話的 Session ID |

**Request 範例**

```json
{
  "question": "那特別休假的天數怎麼計算？",
  "top_k": 5
}
```

**Response 範例**

```json
{
  "answer": "依勞動基準法第38條，特別休假天數依年資計算：繼續工作滿6個月以上未滿1年者，3天；滿1年以上未滿2年者，7天；滿2年以上未滿3年者，10天；滿3年以上未滿5年者，每年14天；滿5年以上未滿10年者，每年15天；滿10年以上者，每年在15天的基礎上，每滿1年加給1天，最多加至30天。",
  "citations": [
    {
      "law_name": "勞動基準法",
      "article_no": "第 38 條"
    }
  ],
  "query_time": 1.872,
  "session_id": "a3f2c1d4-8e7b-4f9a-b2c3-1d4e5f6a7b8c"
}
```

**HTTP 狀態碼**

| 狀態碼 | 說明 |
|---|---|
| 200 | 成功 |
| 422 | 請求格式錯誤 |
| 503 | Generation 服務不可用 |

---

### DELETE /session/{id}

刪除指定 Session，釋放記憶體中的對話歷史。

**路徑參數**

| 參數 | 型別 | 說明 |
|---|---|---|
| `id` | string | 要刪除的 Session ID |

**Request Body**

無。

**Response Schema（HTTP 200）**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `deleted` | boolean | 是否成功刪除（若 Session 不存在則為 `false`） |
| `session_id` | string | 被刪除的 Session ID |

**Request 範例**

```bash
curl -X DELETE http://127.0.0.1:8073/session/a3f2c1d4-8e7b-4f9a-b2c3-1d4e5f6a7b8c
```

**Response 範例（Session 存在）**

```json
{
  "deleted": true,
  "session_id": "a3f2c1d4-8e7b-4f9a-b2c3-1d4e5f6a7b8c"
}
```

**Response 範例（Session 不存在）**

```json
{
  "deleted": false,
  "session_id": "a3f2c1d4-8e7b-4f9a-b2c3-1d4e5f6a7b8c"
}
```

**HTTP 狀態碼**

| 狀態碼 | 說明 |
|---|---|
| 200 | 成功（無論 Session 是否存在） |
| 500 | 伺服器內部錯誤 |

---

## 健康檢查

### GET /health

回傳服務健康狀態與各 provider 資訊。此 endpoint 不執行任何 I/O 操作，應在 500ms 內回應。

**Request Body**

無。

**Response Schema**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `status` | string | 整體健康狀態，見下方說明 |
| `embedding_provider` | string | Embedding provider 名稱，格式為 `type:model` |
| `reranking_provider` | string | Reranking provider 名稱，格式為 `type:model` |
| `generation_provider` | GenerationProviderInfo | Generation provider 資訊 |

**GenerationProviderInfo 物件**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `name` | string | Provider 名稱，格式為 `type:model` |
| `status` | string | `ok` 或 `unreachable` |

**`status` 欄位可能值**

| 值 | HTTP 狀態碼 | 含義 |
|---|---|---|
| `ok` | 200 | 所有 provider 均正常運作 |
| `degraded` | 200 | 至少一個 provider 無法連線（通常是 Generation provider），但服務仍可提供搜尋功能 |
| `error` | 503 | Embedding 或 Reranking provider 初始化失敗，核心功能不可用 |

**Request 範例**

```bash
curl http://127.0.0.1:8073/health
```

**Response 範例（全部正常）**

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

**Response 範例（Generation 無法連線，HTTP 200）**

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

**Response 範例（核心 provider 錯誤，HTTP 503）**

```json
{
  "status": "error",
  "embedding_provider": "local:Qwen3-Embedding-4B",
  "reranking_provider": "local:Qwen3-Reranker-4B",
  "generation_provider": {
    "name": "ollama:qwen3:8b",
    "status": "unreachable"
  }
}
```

**HTTP 狀態碼**

| 狀態碼 | 說明 |
|---|---|
| 200 | 服務正常（`status: ok`）或部分降級（`status: degraded`） |
| 503 | 核心 provider 初始化失敗（`status: error`） |

---

## 錯誤回應

### 驗證錯誤（HTTP 422）

當 request body 缺少必填欄位或型別不符時，FastAPI 自動回傳：

```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

| 欄位 | 說明 |
|---|---|
| `detail` | 錯誤列表 |
| `detail[].loc` | 錯誤位置，第一個元素為 `"body"`，第二個為欄位名稱 |
| `detail[].msg` | 人類可讀的錯誤訊息 |
| `detail[].type` | 錯誤類型代碼 |

### 服務不可用（HTTP 503）

當 Generation provider 無法連線或 LLM 回傳錯誤時：

```json
{
  "detail": "Generation service error: Connection refused"
}
```

### 伺服器內部錯誤（HTTP 500）

當搜尋或資料處理發生非預期錯誤時：

```json
{
  "detail": "index not found or corrupted"
}
```

### 錯誤回應格式總結

| HTTP 狀態碼 | 觸發情境 | `detail` 格式 |
|---|---|---|
| 422 | 請求格式錯誤、缺少必填欄位 | 物件陣列（含 `loc`、`msg`、`type`） |
| 500 | 搜尋服務內部錯誤 | 字串 |
| 503 | Generation / Session 服務不可用 | 字串 |
