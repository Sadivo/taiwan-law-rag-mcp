@echo off
setlocal EnableDelayedExpansion

echo ===================================================
echo  台灣法律 RAG MCP 系統 - 環境安裝腳本
echo ===================================================
echo.

:: ── 1. 檢查必要工具 ────────────────────────────────
echo [1/3] 檢查必要工具...

where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 uv，請先安裝：https://docs.astral.sh/uv/getting-started/installation/
    exit /b 1
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Node.js，請先安裝 Node.js 18+：https://nodejs.org/
    exit /b 1
)

echo [OK] uv 與 Node.js 已就緒
echo.

:: ── 2. 安裝 Python 依賴 ────────────────────────────
echo [2/3] 安裝 Python 依賴 (uv sync)...
cd /d "%~dp0.."
uv sync
if %errorlevel% neq 0 (
    echo [錯誤] Python 依賴安裝失敗。
    exit /b 1
)
echo [OK] Python 依賴安裝完成
echo.

:: ── 3. 安裝並編譯 MCP Server ───────────────────────
echo [3/3] 安裝並編譯 MCP Server...
cd mcp-server
call npm install
if %errorlevel% neq 0 (
    echo [錯誤] npm install 失敗。
    exit /b 1
)
call npm run build
if %errorlevel% neq 0 (
    echo [錯誤] TypeScript 編譯失敗。
    exit /b 1
)
cd ..
echo [OK] MCP Server 編譯完成
echo.

:: ── 4. 建立 .env ───────────────────────────────────
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [OK] 已從 .env.example 建立 .env，請填入你的 API 金鑰
) else (
    echo [跳過] .env 已存在
)

echo.
echo ===================================================
echo  安裝完成！接下來：
echo.
echo  1. 編輯 .env 設定 Provider 與 API 金鑰
echo  2. 建立索引：uv run scripts\build_index.py
echo  3. 啟動服務：uv run python-rag\main.py
echo  4. 設定 Claude Desktop MCP（詳見 README.md）
echo ===================================================

endlocal
