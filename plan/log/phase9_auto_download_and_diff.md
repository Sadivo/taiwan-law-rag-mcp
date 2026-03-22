# Phase 9：自動下載法律資料與版本比對

## 背景

原本 `data/ChLaw.json/` 被 commit 進 repo，造成 repo 體積過大且資料難以維護。
此階段目標：
1. 將資料從 git 移除，改為執行時自動下載
2. 支援版本比對，讓使用者知道資料有哪些異動

---

## 實作內容

### 1. `.gitignore` 調整

移除 `!data/ChLaw.json` 例外規則，改為整個 `data/` 都忽略。
執行 `git rm -r --cached data/ChLaw.json/` 從追蹤中移除。

### 2. `scripts/download_data.py`（新增）

核心邏輯：

**版本檢查（輕量）**
- 呼叫 `https://law.moj.gov.tw/api/swagger/docs/v1`（幾 KB 的 JSON）
- 解析 `info.description` 內的 `資料更新時間：YYYY/MM/DD`
- 與本地 `ChLaw.json` 的 `UpdateDate` 欄位比對

**下載流程**
| 情境 | 行為 |
|---|---|
| 沒有本地資料 | 直接下載，不詢問，不顯示 diff |
| 有資料，版本相同 | 跳過 |
| 有資料，發現新版本 | 顯示新舊日期，`[y/N]` 詢問後下載 |
| `--force` | 跳過所有確認直接下載 |
| 非互動環境（EOFError） | 自動跳過，不卡住 |

**異動比對（diff）**
下載完成後，比對新舊資料的 `{LawName: LawModifiedDate}` 對照表，輸出：
- 新增法律
- 刪除法律
- 修改法律（顯示舊日期 → 新日期）

### 3. `scripts/build_index.py` 更新

加入 Phase 0 下載步驟，在 Phase 2 資料處理前執行。
新增參數：
- `--skip-download`：跳過下載，直接用現有資料
- `--force-download`：強制重新下載

---

## 設計決策

- 版本比對不下載整包 zip，只 GET swagger docs JSON，節省頻寬
- 首次下載不顯示 diff（沒有舊資料可比對）
- 更新確認設計為 `[y/N]`，預設 N，避免誤操作
- 非互動環境自動跳過，不影響 CI/自動化流程
