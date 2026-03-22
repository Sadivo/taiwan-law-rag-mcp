"""
下載台灣法律資料（ChLaw.json）

資料來源：https://law.moj.gov.tw/api/ch/law/json
下載後解壓縮至 data/ChLaw.json/ChLaw.json

預設行為：
  - 沒有資料 → 直接下載
  - 有資料 → 檢查官方是否有新版本，有的話詢問使用者是否更新
使用 --force 跳過確認直接下載。
"""

import os
import sys
import re
import json
import zipfile
import urllib.request
import urllib.error
import shutil

DATA_URL = "https://law.moj.gov.tw/api/ch/law/json"
SWAGGER_DOCS_URL = "https://law.moj.gov.tw/api/swagger/docs/v1"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "ChLaw.json")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "ChLaw.json")
ZIP_TMP = os.path.join(DATA_DIR, "_ChLaw_tmp.zip")


def get_remote_update_date() -> str | None:
    """從 Swagger docs API 取得官方資料更新日期，不需下載整包 zip"""
    try:
        with urllib.request.urlopen(SWAGGER_DOCS_URL, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        desc = data.get("info", {}).get("description", "")
        m = re.search(r"資料更新時間[：:]\s*(\d{4}/\d{2}/\d{2})", desc)
        return m.group(1) if m else None
    except Exception:
        return None


def get_local_update_date() -> str | None:
    """讀取現有資料的 UpdateDate"""
    if not os.path.exists(OUTPUT_FILE):
        return None
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 官方格式：'2026/3/6 上午 12:00:00'，只取日期部分並標準化
        raw = data.get("UpdateDate", "")
        m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", raw)
        if m:
            return f"{m.group(1)}/{int(m.group(2)):02d}/{int(m.group(3)):02d}"
        return None
    except Exception:
        return None


def download_zip(url: str, dest: str) -> None:
    """下載 zip 檔案，顯示進度"""
    print(f"正在從官方 API 下載資料...")
    print(f"  URL: {url}")

    def _progress(block_num, block_size, total_size):
        if total_size > 0:
            pct = min(block_num * block_size / total_size * 100, 100)
            mb = total_size / 1024 / 1024
            print(f"  進度: {pct:.1f}% / {mb:.1f} MB", end="\r")

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    urllib.request.urlretrieve(url, dest, reporthook=_progress)
    print()


def extract_zip(zip_path: str, output_dir: str) -> None:
    """解壓縮 zip，只取 ChLaw.json"""
    os.makedirs(output_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        target = next((n for n in names if n.endswith("ChLaw.json")), None)
        if target is None:
            raise FileNotFoundError(f"zip 內找不到 ChLaw.json，內容: {names}")
        with zf.open(target) as src, open(os.path.join(output_dir, "ChLaw.json"), "wb") as dst:
            shutil.copyfileobj(src, dst)


def load_law_index(filepath: str) -> dict[str, str]:
    """讀取法律資料，回傳 {LawName: LawModifiedDate} 對照表"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {law["LawName"]: law.get("LawModifiedDate", "") for law in data.get("Laws", [])}


def print_diff(old: dict[str, str], new: dict[str, str]) -> None:
    """比對新舊資料並輸出差異"""
    old_names = set(old)
    new_names = set(new)

    added = sorted(new_names - old_names)
    removed = sorted(old_names - new_names)
    modified = sorted(
        name for name in old_names & new_names
        if old[name] != new[name]
    )

    total = len(added) + len(removed) + len(modified)
    if total == 0:
        print("（無法條異動）")
        return

    print(f"\n{'─'*50}")
    print(f"資料異動摘要：新增 {len(added)} 筆 / 刪除 {len(removed)} 筆 / 修改 {len(modified)} 筆")
    print(f"{'─'*50}")

    if added:
        print(f"\n【新增法律】（{len(added)} 筆）")
        for name in added:
            print(f"  + {name}")

    if removed:
        print(f"\n【刪除法律】（{len(removed)} 筆）")
        for name in removed:
            print(f"  - {name}")

    if modified:
        print(f"\n【修改法律】（{len(modified)} 筆）")
        for name in modified:
            print(f"  ~ {name}  ({old[name]} → {new[name]})")

    print(f"{'─'*50}")


def _do_download(show_diff: bool = True) -> bool:
    """執行下載與解壓縮，回傳是否成功"""
    # 下載前先快照舊資料
    old_index = load_law_index(OUTPUT_FILE) if show_diff and os.path.exists(OUTPUT_FILE) else None

    try:
        download_zip(DATA_URL, ZIP_TMP)
    except urllib.error.URLError as e:
        print(f"[錯誤] 無法下載資料: {e}")
        sys.exit(1)
    print("解壓縮中...")
    extract_zip(ZIP_TMP, OUTPUT_DIR)
    os.remove(ZIP_TMP)
    print("✅ 資料下載完成！")

    # 比對差異
    if old_index is not None:
        new_index = load_law_index(OUTPUT_FILE)
        print_diff(old_index, new_index)

    return True


def download_law_data(force: bool = False) -> bool:
    """
    下載法律資料。

    - 沒有資料 → 直接下載
    - 有資料 + force=True → 直接下載，不詢問
    - 有資料 + force=False → 檢查遠端版本，有新版本時詢問使用者

    Returns:
        True  = 有下載新資料
        False = 跳過
    """
    if not os.path.exists(OUTPUT_FILE):
        print("找不到現有資料，開始下載...")
        return _do_download(show_diff=False)

    if force:
        print("強制重新下載...")
        return _do_download()

    # 有資料，檢查遠端版本
    local_date = get_local_update_date()
    print(f"現有資料更新日期: {local_date or '未知'}")
    print("正在檢查官方是否有新版本...")

    remote_date = get_remote_update_date()
    if remote_date is None:
        print("[警告] 無法取得官方更新日期，使用現有資料繼續。")
        return False

    print(f"官方資料更新日期: {remote_date}")

    if remote_date == local_date:
        print("資料已是最新版本，跳過下載。")
        return False

    # 有新版本，詢問使用者
    print(f"\n發現新版本！（{local_date} → {remote_date}）")
    try:
        answer = input("是否下載更新？下載後需重新建立索引。[y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        # 非互動環境（如 CI）預設跳過
        print("\n非互動環境，跳過更新。如需更新請使用 --force-download。")
        return False

    if answer in ("y", "yes"):
        return _do_download()
    else:
        print("跳過更新，使用現有資料。")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="下載台灣法律資料")
    parser.add_argument("--force", action="store_true", help="強制重新下載，跳過確認")
    args = parser.parse_args()

    updated = download_law_data(force=args.force)
    if updated:
        print("\n資料已更新，請執行 build_index.py 重建索引。")
    else:
        print("\n無需更新。")
