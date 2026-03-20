import hashlib
from typing import List, Dict, Any

from data_processing.metadata_enricher import enrich_metadata
from utils.article_parser import normalize_article_no

def process_law_articles(laws: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    將法規清單依據條文層級 (Article-Level) 進行 Chunking 切塊
    
    Args:
        laws: 由 loader 讀取入記憶體的多部法規陣列
        
    Returns:
        包含 id, content, metadata 的 chunks 陣列，準備送入 Vector DB
    """
    chunks = []
    
    for law in laws:
        law_name = law.get("LawName", "")
        # 從母法提取通用上下文，對應 MoJ Open Data 格式
        context_info = {
            "law_name": law_name,
            "law_level": law.get("LawLevel", ""),
            "law_category": law.get("LawCategory", ""),
            "law_url": law.get("LawURL", ""),
            "modified_date": law.get("LawModifiedDate", ""),
            "is_abolished": str(law.get("LawAbolished", "")).strip() == "廢止",
            "has_english": str(law.get("LawHasEng", "")).strip() == "Y",
            "chapter": ""
        }
        
        articles = law.get("LawArticles", [])
        for article in articles:
            article_type = article.get("ArticleType", "")
            
            # C 型別: 代表標籤 (如：第 一 章 總則)，不是實質條文
            if article_type == "C":
                context_info["chapter"] = article.get("ArticleContent", "").strip()
                continue
                
            # A 型別: 實質條文
            if article_type == "A":
                raw_article_no = article.get("ArticleNo", "")
                norm_article_no = normalize_article_no(raw_article_no)
                
                # 更新至 context 供 enrich 使用
                context_info["article_no"] = norm_article_no
                
                content = article.get("ArticleContent", "").strip()
                if not content:
                    continue
                    
                # 取得統一的擴充 Metadata
                base_metadata = enrich_metadata(article, context_info)
                
                # 若條文過長 (>500字)，試行以段落進行拆分
                if len(content) > 500:
                    paragraphs = content.split('\n')
                    current_chunk_text = ""
                    part_idx = 1
                    
                    for para in paragraphs:
                        para = para.strip()
                        if not para:
                            continue
                            
                        # 如果合併後超過長度，則先寫入現有的
                        if len(current_chunk_text) + len(para) > 500 and current_chunk_text:
                            chunk_id = f"{law_name}_{norm_article_no}_part{part_idx}"
                            chunks.append({
                                "id": chunk_id,
                                "content": current_chunk_text.strip(),
                                "metadata": base_metadata.copy()
                            })
                            current_chunk_text = para
                            part_idx += 1
                        else:
                            current_chunk_text += ("\n" + para if current_chunk_text else para)
                            
                    # 處理最後剩餘的部分
                    if current_chunk_text:
                        chunk_id = f"{law_name}_{norm_article_no}_part{part_idx}"
                        chunks.append({
                            "id": chunk_id,
                            "content": current_chunk_text.strip(),
                            "metadata": base_metadata.copy()
                        })
                else:
                    # 一般正常長度條文
                    chunk_id = f"{law_name}_{norm_article_no}"
                    chunks.append({
                        "id": chunk_id,
                        "content": content,
                        "metadata": base_metadata.copy()
                    })
                    
    return chunks
