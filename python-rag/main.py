from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv
load_dotenv()  # 載入 .env 檔（若存在）

from api import routes
from api.models import HealthResponse

# 設定日誌
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = FastAPI(
    title="Taiwan Law RAG API",
    description="台灣法律 RAG MCP 系統的檢索 API",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "*"], # 在開發環境允許所有或 localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載路由
app.include_router(routes.router)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        embedding_provider=routes._embedding_provider_name,
        reranking_provider=routes._reranking_provider_name,
    )

if __name__ == "__main__":
    import uvicorn
    # 提供直接執行 main.py 的測試方式
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
