from typing import List, Dict, Any

class Deduplicator:
    """
    laws deduplication
    1. 確保檢索結果的多樣性
    2. 同一部法律文件保留最多 N 條結果 (預設 3 條)
    """
    def __init__(self, max_per_law: int = 3):
        self.max_per_law = max_per_law

    def deduplicate(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        遍歷排好序的 docs，依序放入 results，若某 law_name 出現次數達到 max_per_law，則捨棄後續同 law_name 的檔案
        """
        law_counts = {}
        results = []
        
        for doc in docs:
            # 取得 law_name。若 chunk 沒有 law_name 或不明確，則算作 "unknown"
            law_name = doc.get("law_name", "unknown")
            
            if law_name not in law_counts:
                law_counts[law_name] = 0
                
            if law_counts[law_name] < self.max_per_law:
                results.append(doc)
                law_counts[law_name] += 1
                
        return results
