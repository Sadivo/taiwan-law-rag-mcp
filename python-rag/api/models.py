from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class SearchResult(BaseModel):
    law_name: str = Field(default="", description="法律名稱")
    law_level: str = Field(default="", description="法律層級 (憲法/法律)")
    law_category: str = Field(default="", description="法律類別")
    law_url: str = Field(default="", description="官方連結")
    article_no: str = Field(default="", description="條號 (如: '第 38 條')")
    chapter: str = Field(default="", description="章節")
    content: str = Field(default="", description="條文內容")
    score: Optional[float] = Field(default=None, description="相關度分數")
    modified_date: str = Field(default="", description="修正日期")

# --- Requests ---

class SemanticSearchRequest(BaseModel):
    query: str = Field(..., description="搜尋關鍵字或問題")
    top_k: int = Field(10, description="返回結果數量")
    filter_category: Optional[str] = Field(None, description="過濾法律類別（可選）")

class ExactSearchRequest(BaseModel):
    query: str = Field(..., description="精確搜尋查詢句，例如：勞基法第38條")

class LawSearchRequest(BaseModel):
    law_name: str = Field(..., description="法律名稱")
    include_abolished: bool = Field(False, description="是否包含已廢止法律")

class LawFullRequest(BaseModel):
    law_name: str = Field(..., description="法律名稱")

class CompareRequest(BaseModel):
    law_names: List[str] = Field(..., description="要比較的法律名稱列表")
    topic: str = Field(..., description="比較主題或關鍵字")

class RebuildIndexRequest(BaseModel):
    force: bool = Field(False, description="是否強制重建索引")

# --- Responses ---

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query_time: float

class ExactSearchResponse(BaseModel):
    results: List[SearchResult]

class LawSearchResponse(BaseModel):
    results: List[SearchResult]

class Article(BaseModel):
    article_no: str
    content: str
    chapter: str = ""

class Law(BaseModel):
    law_name: str
    law_level: str
    law_category: str
    law_url: str
    modified_date: str
    is_abolished: bool

class LawFullResponse(BaseModel):
    law: Law
    articles: List[Article]

class CompareResponse(BaseModel):
    comparison: Dict[str, List[Article]]

class RebuildIndexResponse(BaseModel):
    status: str
    chunks: int
    time: float

class HealthResponse(BaseModel):
    status: str
    embedding_provider: str   # e.g. "local:Qwen3-Embedding-4B"
    reranking_provider: str   # e.g. "cohere:rerank-multilingual-v3.0"

class Citation(BaseModel):
    law_name: str
    article_no: str

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="法律問題")
    top_k: int = Field(5, ge=1, le=50, description="retrieval 條文數量")

class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    query_time: float


# --- Session API models ---

class SessionChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="法律問題")
    top_k: int = Field(5, ge=1, le=50, description="retrieval 條文數量")

class CreateSessionResponse(BaseModel):
    session_id: str

class SessionChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    query_time: float
    session_id: str

class DeleteSessionResponse(BaseModel):
    deleted: bool
    session_id: str
