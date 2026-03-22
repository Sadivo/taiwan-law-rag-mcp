# Phase 7 實作紀錄與 GPU 加速失敗問題追蹤

## 實作紀錄 (Phase 7: 整合測試)
- **環境初始化 (`scripts/setup.bat`)**：完成自動化環境建立與檢測腳本，涵蓋 Python `uv` 虛擬環境套件安裝與 Node.js MCP Server 編譯。
- **一鍵索引建立 (`scripts/build_index.py`)**：實作打包了資料載入、切塊、FAISS 與 BM25 向量化的建置流程。期間修復了呼叫子目錄腳本因相對路徑導致 `chunks.json` 找不到的路徑錯置問題。
- **查詢測試腳本 (`scripts/test_query.py`)**：修正了 `HybridRetriever` 實例化時遺漏 `embedder` 的問題，並於 `Embedder` 類別內擴充了 `embed_query` 方法，以支援測試腳本進行單一句子查詢轉換。
- **專案發布文檔 (`README.md`)**：完成整體系統的介紹、安裝方式及與 Claude MCP 的整合設定說明。

---

## 待解決問題紀錄：GPU 無法正確啟用 (PyTorch CUDA 議題)

### 問題描述
雖然目前程式能正常透過 `build_index.py` 產生索引，並能通過檢測跑進「Generating Embeddings...」的嵌入階段，但系統將運算壓力全數丟給了 CPU，導致 GPU 的使用率趨近於 0%。這會使得近 5 萬條法規 chunks 的向量化處理時間過長（預估需要數十分鐘以上）。

### 排查歷程與失敗點
1. **偵測到 PyTorch 為 CPU 版本**：
   - 初步診斷發現，預設由 `uv` 或 `pip` 解析安裝的 PyTorch 模組為 CPU 版（`+cpu`），並未啟用 CUDA 加速。
2. **嘗試強制安裝 CUDA 版本的衝突**：
   - 企圖透過 `--index-url https://download.pytorch.org/whl/cu121` 安裝 CUDA 版本的 `torch`、`torchvision`、`torchaudio` 進行環境覆寫。
   - 但安裝後出現了套件版號不符合的核心衝突：`RuntimeError: operator torchvision::nms does not exist`。
3. **移除導致衝突的關聯套件**：
   - 因為純文字 RAG 架構不需要影像處理模組，後續嘗試直接解除安裝了 `torchvision` 與 `torchaudio`。
   - **結果**：解除安裝後確實讓 `transformers` 恢復了運作，但系統底層依然沒能正確把資源分配給 GPU，導致它回退到使用 CPU 繼續無力地運算。

### 建議的後續修復行動 (Action Items)
1. **純淨重建測試**：先刪除目前的 `.venv` 以免套件受到快取污染，針對 CUDA 再次重新安裝嚴格指定版本的核心庫，例如：
   ```bash
   uv pip install torch==2.1.2+cu121 --extra-index-url https://download.pytorch.org/whl/cu121
   ```
2. **NVIDIA 驅動檢測**：確認本機 Windows 環境是否有安裝相容的 NVIDIA 驅動以及對應版本的 CUDA Toolkit，以防作業系統層級無法調用。
3. **加入裝置載入印出偵錯**：在後續修復的過程中，可以在 `embedder.py` 初始化時加入 `print(torch.cuda.is_available(), torch.cuda.get_device_name(0))`，嚴格確認模型啟動前 GPU 是否被正確載入。
