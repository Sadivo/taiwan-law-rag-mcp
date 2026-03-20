import os
import jieba
from typing import List, Dict, Any
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, KEYWORD
from whoosh.analysis import Tokenizer, Token
from whoosh.compat import text_type

class JiebaTokenizer(Tokenizer):
    """
    自定義 Jieba 分詞器以供 Whoosh 使用
    """
    def __call__(self, value, positions=False, chars=False, keeporiginal=False, removestops=True, start_pos=0, start_char=0, mode='', **kwargs):
        assert isinstance(value, text_type), f"{value!r} is not unicode"
        t = Token(positions, chars, removestops=removestops, mode=mode, **kwargs)
        for pos, (word, start, end) in enumerate(jieba.tokenize(value, mode='search')):
            t.text = word
            t.boost = 1.0
            if positions:
                t.pos = start_pos + pos
            if chars:
                t.startchar = start_char + start
                t.endchar = start_char + end
            yield t

def get_jieba_analyzer():
    return JiebaTokenizer()

class BM25Indexer:
    """
    Whoosh BM25 索引，處理精確關鍵字檢索
    """
    def __init__(self, index_dir: str = "data/bm25_index", custom_dict_path: str = None):
        self.index_dir = index_dir
        
        # 載入自訂法律字典
        if custom_dict_path and os.path.exists(custom_dict_path):
            jieba.load_userdict(custom_dict_path)
            print(f"[{self.__class__.__name__}] Loaded userdict from {custom_dict_path}")
        
        analyzer = get_jieba_analyzer()
        
        self.schema = Schema(
            chunk_id=ID(stored=True, unique=True),
            law_name=TEXT(stored=True, analyzer=analyzer),
            article_no=ID(stored=True),
            content=TEXT(stored=True, analyzer=analyzer),
            chapter=TEXT(stored=True, analyzer=analyzer),
            category=KEYWORD(stored=True, commas=True)
        )

    def build_index(self, chunks: List[Dict[str, Any]]):
        """
        批次將 chunks 寫入 Whoosh 索引
        """
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)
            
        print(f"[{self.__class__.__name__}] Building BM25 index in {self.index_dir}...")
        ix = create_in(self.index_dir, self.schema)
        
        # limitmb 用於控制寫入過程的記憶體消耗
        writer = ix.writer(procs=1, limitmb=1024)
        
        for i, chunk in enumerate(chunks):
            meta = chunk.get("metadata", {})
            writer.add_document(
                chunk_id=text_type(chunk.get("id", f"chunk_{i}")),
                law_name=text_type(meta.get("law_name", "")),
                article_no=text_type(meta.get("article_no", "")),
                content=text_type(chunk.get("content", "")),
                chapter=text_type(meta.get("chapter", "")),
                category=text_type(meta.get("law_category", ""))
            )
            
        # 寫完所有文檔後統一 commit，確保速度最佳化
        writer.commit()
        print(f"[{self.__class__.__name__}] BM25 index built successfully and optimized.")
