import re
from typing import Dict, Any, Optional

try:
    from utils.article_parser import normalize_article_no
except ImportError:
    def normalize_article_no(text: str) -> str:
        """
        簡易的回退處理：嘗試提取數字並加上「第 X 條」的格式
        若已經有 utils 模組中的正則處理，則優先使用該模組
        """
        digits = re.findall(r'\d+', text)
        if digits:
            return f"第 {digits[0]} 條"
        return text

class QueryClassifier:
    """
    查詢分類器: 區分精確查詢 vs 語義查詢
    根據 VIBE_CODING_PROMPT 中的設計：
    1. 精確查詢: 包含條號或法律名稱+特定關鍵字
    2. 語義查詢: 一般情境描述或問題
    """
    
    def __init__(self):
        # 模式 1：(法律名稱)第X條，例如: 勞基法第38條、第38條
        self.exact_pattern_1 = re.compile(
            r'(?P<law_name>[\u4e00-\u9fa5]+(?:法|條例|規則|辦法))?\s*第\s*(?P<article_no>\d+(?:-\d+)?)\s*條'
        )
        # 模式 2：(法律名稱) (數字)，例如: 民法 184
        self.exact_pattern_2 = re.compile(
            r'(?P<law_name>[\u4e00-\u9fa5]+(?:法|條例|規則|辦法))\s+(?P<article_no>\d+(?:-\d+)?)(\s*條)?'
        )

    def classify(self, query: str) -> Dict[str, Any]:
        """
        分類邏輯：判斷為精確查詢或是語境查詢
        回傳:
        {
          "type": "exact" | "semantic",
          "law_name": str | None,
          "article_no": str | None
        }
        """
        query = query.strip()
        
        # 嘗試模式 1
        match = self.exact_pattern_1.search(query)
        if match:
            law_name = match.group('law_name')
            article_no = match.group('article_no')
            return {
                "type": "exact",
                "law_name": law_name.strip() if law_name else None,
                "article_no": normalize_article_no(f"第{article_no}條")
            }
            
        # 嘗試模式 2
        match = self.exact_pattern_2.search(query)
        if match:
            law_name = match.group('law_name')
            article_no = match.group('article_no')
            return {
                "type": "exact",
                "law_name": law_name.strip() if law_name else None,
                "article_no": normalize_article_no(f"第{article_no}條")
            }
            
        # 另外一種：只有法律名稱的查詢（也是精確的一種，可能要返回整篇）
        # 但在分類上，我們通常視只有關鍵字為 Semantic，除非它命中精確條號
        # 所以預設返回語義查詢
        return {
            "type": "semantic",
            "law_name": None,
            "article_no": None
        }

if __name__ == "__main__":
    classifier = QueryClassifier()
    print("勞基法第38條  ->", classifier.classify("勞基法第38條"))
    print("民法 184       ->", classifier.classify("民法 184"))
    print("公司法股東會  ->", classifier.classify("公司法股東會"))
    print("加班費如何計算 ->", classifier.classify("加班費如何計算"))
