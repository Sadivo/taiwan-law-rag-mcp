from collections import OrderedDict
import time
from typing import Any, Optional

class QueryCache:
    """
    LRU Cache 實作
    使用 collections.OrderedDict 提供快速 O(1) 的查詢與更新，以及 TTL 支援。
    """
    def __init__(self, maxsize: int = 100, ttl: int = 3600):
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            # 檢查是否過期
            if time.time() - timestamp < self.ttl:
                # 重新標記為最近使用
                self.cache.move_to_end(key)
                return value
            else:
                # 過期則移除
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        # 如果已經存在，先刪除，這樣加入才會在最後面（最近使用）
        if key in self.cache:
            del self.cache[key]
            
        self.cache[key] = (value, time.time())
        # 超過大小限制，移除最舊的項目 (FIFO in OrderedDict)
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

# 全域共用的快取實例
query_cache = QueryCache(maxsize=100, ttl=3600)
