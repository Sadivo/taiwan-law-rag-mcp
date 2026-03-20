from typing import Dict, Any

from .law_aliases import LAW_ALIASES

# 從 LAW_ALIASES 反向建立對照，讓每一個法律正式名稱可以對應到多個別名，作為 Metadata 的一環
REVERSE_ALIASES = {}
for alias, formal_name in LAW_ALIASES.items():
    if formal_name not in REVERSE_ALIASES:
        REVERSE_ALIASES[formal_name] = []
    # 避免本名也在別名裡 (例如"公司法": "公司法")
    if alias != formal_name:
        REVERSE_ALIASES[formal_name].append(alias)


def enrich_metadata(article: Dict[str, Any], context_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    擴充與整合給 Embedding 與 Metadata 過濾使用的中介資料
    
    Args:
        article: 單一條文物件 (對應 LawArticle)
        context_info: 來自上方的附屬資訊，如 law_name, chapter 等
        
    Returns:
        整理擴充後的 metadata 字典，供 Vector DB 及應用端使用
    """
    law_name = context_info.get("law_name", "")
    
    # 建構擴充後的 Metadata 框架，採用符合 VIBE_CODING_PROMPT 的結構
    metadata = {
        "law_name": law_name,
        "law_level": context_info.get("law_level", ""),
        "law_category": context_info.get("law_category", ""),
        "law_url": context_info.get("law_url", ""),
        "article_no": context_info.get("article_no", article.get("ArticleNo", "")),
        "chapter": context_info.get("chapter", ""),
        "modified_date": context_info.get("modified_date", ""),
        "is_abolished": context_info.get("is_abolished", False),
        "has_english": context_info.get("has_english", False),
        "aliases": REVERSE_ALIASES.get(law_name, [])
    }
    
    return metadata
