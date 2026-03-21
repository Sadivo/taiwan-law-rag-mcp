@echo off
setlocal EnableDelayedExpansion

echo ===================================================
echo 台灣法律 RAG MCP 系統 - 環境初始化與安裝腳本
echo ===================================================

echo [1/4] 檢查系統環境...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python，請確定已安裝 Python 3.10+ 並加入 PATH。
    exit /b 1
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Node.js，請確定已安裝 Node.js 18+ 並加入 PATH。
    exit /b 1
)

where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [警告] 找不到 uv，開始安裝 uv...
    pip install uv
    if %errorlevel% neq 0 (
        echo [錯誤] uv 安裝失敗，請手動確認。
        exit /b 1
    )
)

echo.
echo [2/4] 初始化 Python 環境 (python-rag)...
cd python-rag
echo 正在建立虛擬環境與安裝依賴...
uv venv
call .venv\Scripts\activate.bat
uv pip sync requirements.txt
if %errorlevel% neq 0 (
    echo [錯誤] Python 依賴安裝失敗。
    exit /b 1
)
cd ..

echo.
echo [3/4] 初始化 Node 環境 (mcp-server)...
cd mcp-server
echo 正在安裝 npm 套件...
call npm install
if %errorlevel% neq 0 (
    echo [錯誤] npm 安裝失敗。
    exit /b 1
)
echo 正在編譯 TypeScript...
call npm run build
if %errorlevel% neq 0 (
    echo [錯誤] TypeScript 編譯失敗。
    exit /b 1
)
cd ..

echo.
echo [4/4] 建立必要的資料夾...
if not exist "data\bm25_index" mkdir "data\bm25_index"

echo ===================================================
echo 初始化完成！全部環境已準備就緒。
echo 1. 啟動伺服器: 在 python-rag 執行 "uv run uvicorn main:app"
echo 2. 建立索引: 在專案根目錄執行 "uv run scripts\build_index.py"
echo 3. 測試查詢: 在專案根目錄執行 "uv run scripts\test_query.py"
echo ===================================================

endlocal
