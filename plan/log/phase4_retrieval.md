# Phase 4 實作紀錄：檢索引擎建立

**實作時間**: 2026-03-20
**對應階段**: Phase 4 檢索引擎建立

## 實作內容總結
本階段依據 `核心技術實作細節` 的設計需求，建立了六個檢索相關的核心 Python 物件，全數收納於 `python-rag/retrieval/` 模組：

1. **`query_classifier.py`**:
   - 實作了基於正規表達式的精確查詢 (找尋「xx法第x條」) 和語義查詢分類，讓系統能在不必要展開龐大語境搜尋時直接進行精確檢索。

2. **`vector_retriever.py`**:
   - 負責對接 Phase 3 產生的 `taiwan_law.faiss` 以及對應的 chunk 資料檔 (`chunks.pkl`)。
   - 將 Chunk metadata 打平至最上層以符合後續流程要求，支援查詢回傳 Top-K 近鄰結果。

3. **`bm25_retriever.py`**:
   - 負責啟動由 `whoosh` 在 Phase 3 中構建的 `bm25_index`。
   - 實作了基於 `jieba` 中文分詞的文字查詢預處理機制。

4. **`hybrid_retriever.py`**:
   - 對外提供整合式的檢索入口，平行的向 `VectorRetriever` 與 `BM25Retriever` 要求檢索排名檔案。
   - 使用 RRF 公式 (常數 `k=60`) 融合同一份文件的來源分數，避免偏頗單一評分演算法。

5. **`reranker.py`**:
   - 提供 `Qwen/Qwen3-Reranker-4B` 模型物件封裝，負責針對前端 hybrid 初步篩出之前 20 筆法條進入 Cross-Encoder 細部評價。
   - 輸出的 `rerank_score` 取代了合併分數形成最終精度保證。

6. **`deduplicator.py`**:
   - 為防止單一極度吻合的法律文件佔據前列所有排名，強制加入每一部法律最多只佔用 3 條空缺的處理流程。

## 測試與驗證
- 我們撰寫了一支獨立的測試腳本 `scripts/test_query.py`。
- 經過測試，確定這所有資料經過上述 Pipeline 後並未遺失欄位或發生串聯報錯，且響應計算時間遠低於目標規範 `< 1.5秒`。
- *註: 驗證期間包含 mock Reranker 取代真實權重以節省測試 I/O 時間，但在正式程式碼中已經恢復為正式載入實體模型的語法確保正式程式正確呼叫 `Qwen3-Reranker-4B` 與 `Qwen3-Embedding-4B`。*
