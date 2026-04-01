"""
scripts/setup.py
一鍵初始化開發環境的 Setup Script

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class StepError(Exception):
    """步驟執行失敗時拋出，包含失敗原因與建議修復指令。"""

    def __init__(self, message: str, fix_command: str) -> None:
        super().__init__(message)
        self.message = message
        self.fix_command = fix_command


# ---------------------------------------------------------------------------
# Step functions
# ---------------------------------------------------------------------------

def step_venv() -> None:
    """確認 .venv 存在，否則執行 uv venv。"""
    if not os.path.exists(".venv"):
        try:
            subprocess.run(["uv", "venv"], check=True)
        except subprocess.CalledProcessError as e:
            raise StepError(
                message=f"建立虛擬環境失敗（exit code {e.returncode}）",
                fix_command="uv venv",
            ) from e
        except FileNotFoundError:
            raise StepError(
                message="找不到 uv 指令，請先安裝 uv",
                fix_command="pip install uv",
            )


def step_sync() -> None:
    """執行 uv sync 安裝依賴套件。"""
    try:
        subprocess.run(["uv", "sync"], check=True)
    except subprocess.CalledProcessError as e:
        raise StepError(
            message=f"安裝依賴套件失敗（exit code {e.returncode}）",
            fix_command="uv sync",
        ) from e
    except FileNotFoundError:
        raise StepError(
            message="找不到 uv 指令，請先安裝 uv",
            fix_command="pip install uv",
        )


def step_env() -> None:
    """若 .env 不存在則從 .env.example 複製；若已存在則跳過。"""
    if os.path.exists(".env"):
        print("  .env 已存在，跳過複製步驟")
        return

    if not os.path.exists(".env.example"):
        raise StepError(
            message="找不到 .env.example，無法建立 .env",
            fix_command="確認專案根目錄存在 .env.example 檔案",
        )

    shutil.copy(".env.example", ".env")
    print("  已從 .env.example 複製 .env，請填寫必要欄位（如 PROVIDER_API_KEY）")


def step_check() -> None:
    """執行 uv run main.py check 驗證設定。"""
    try:
        subprocess.run(["uv", "run", "main.py", "check"], check=True)
    except subprocess.CalledProcessError as e:
        raise StepError(
            message=f"環境驗證失敗（exit code {e.returncode}），請確認 .env 設定正確",
            fix_command="uv run main.py check",
        ) from e
    except FileNotFoundError:
        raise StepError(
            message="找不到 uv 指令，請先安裝 uv",
            fix_command="pip install uv",
        )


# ---------------------------------------------------------------------------
# Step runner
# ---------------------------------------------------------------------------

STEPS = [
    ("確認虛擬環境", step_venv),
    ("安裝依賴套件", step_sync),
    ("設定 .env 檔案", step_env),
    ("驗證環境設定", step_check),
]


def run_step(n: int, total: int, desc: str, fn) -> None:
    """輸出進度訊息後執行步驟函式；失敗時 raise StepError。"""
    print(f"[{n}/{total}] {desc}")
    fn()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    total = len(STEPS)
    for i, (desc, fn) in enumerate(STEPS, 1):
        try:
            run_step(i, total, desc, fn)
        except StepError as e:
            print(f"✗ 步驟 {i} 失敗：{e.message}", file=sys.stderr)
            print(f"  建議修復指令：{e.fix_command}", file=sys.stderr)
            sys.exit(1)

    print("\n✓ 環境初始化完成！啟動服務：uv run main.py serve")


if __name__ == "__main__":
    main()
