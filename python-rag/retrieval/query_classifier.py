import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional

try:
    from utils.article_parser import normalize_article_no
except ImportError:
    def normalize_article_no(text: str) -> str:
        digits = re.findall(r'\d+', text)
        if digits:
            return f"第 {digits[0]} 條"
        return text


class IntentType(str, Enum):
    EXACT = "exact"
    SEMANTIC = "semantic"
    COMPARISON = "comparison"
    DEFINITION = "definition"
    PROCEDURE = "procedure"


@dataclass
class ClassificationResult:
    intent: IntentType
    law_name: Optional[str]
    article_no: Optional[str]


class QueryClassifier:
    """
    查詢分類器：支援五種 IntentType
    優先順序：exact > comparison > definition > procedure > semantic
    """

    def __init__(self):
        # exact patterns
        self.exact_pattern_1 = re.compile(
            r'(?P<law_name>[\u4e00-\u9fa5]+(?:法|條例|規則|辦法))?\s*第\s*(?P<article_no>\d+(?:-\d+)?)\s*條'
        )
        self.exact_pattern_2 = re.compile(
            r'(?P<law_name>[\u4e00-\u9fa5]+(?:法|條例|規則|辦法))\s+(?P<article_no>\d+(?:-\d+)?)(\s*條)?'
        )
        # comparison pattern
        self.comparison_pattern = re.compile(
            r'比較|差異|vs\.?|和.{0,10}的不同|相較|不同之處'
        )
        # definition pattern
        self.definition_pattern = re.compile(
            r'什麼是|定義|是指|何謂|係指|的意思'
        )
        # procedure pattern
        self.procedure_pattern = re.compile(
            r'如何|步驟|流程|怎麼辦|程序|怎麼|如何辦理|怎樣'
        )

    def classify(self, query: str) -> ClassificationResult:
        """
        依優先順序分類：exact > comparison > definition > procedure > semantic
        回傳 ClassificationResult
        """
        query = query.strip()

        # 1. exact（最高優先）
        match = self.exact_pattern_1.search(query)
        if match:
            law_name = match.group('law_name')
            article_no = match.group('article_no')
            return ClassificationResult(
                intent=IntentType.EXACT,
                law_name=law_name.strip() if law_name else None,
                article_no=normalize_article_no(f"第{article_no}條"),
            )

        match = self.exact_pattern_2.search(query)
        if match:
            law_name = match.group('law_name')
            article_no = match.group('article_no')
            return ClassificationResult(
                intent=IntentType.EXACT,
                law_name=law_name.strip() if law_name else None,
                article_no=normalize_article_no(f"第{article_no}條"),
            )

        # 2. comparison
        if self.comparison_pattern.search(query):
            return ClassificationResult(
                intent=IntentType.COMPARISON,
                law_name=None,
                article_no=None,
            )

        # 3. definition
        if self.definition_pattern.search(query):
            return ClassificationResult(
                intent=IntentType.DEFINITION,
                law_name=None,
                article_no=None,
            )

        # 4. procedure
        if self.procedure_pattern.search(query):
            return ClassificationResult(
                intent=IntentType.PROCEDURE,
                law_name=None,
                article_no=None,
            )

        # 5. semantic（預設）
        return ClassificationResult(
            intent=IntentType.SEMANTIC,
            law_name=None,
            article_no=None,
        )


if __name__ == "__main__":
    classifier = QueryClassifier()
    tests = [
        "勞基法第38條",
        "民法 184",
        "比較勞基法和民法的差異",
        "什麼是勞動契約",
        "加班費怎麼算",
        "公司法股東會",
        "比較勞基法第38條",  # exact 優先
    ]
    for q in tests:
        result = classifier.classify(q)
        print(f"{q!r:30s} -> {result.intent.value}, law={result.law_name}, art={result.article_no}")
