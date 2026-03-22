from typing import List, Dict, Any

try:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
except ImportError:
    torch = None
    AutoModelForSequenceClassification = None
    AutoTokenizer = None

class Reranker:
    """
    Qwen3-Reranker-4B 重排序
    1. 載入模型 Qwen/Qwen3-Reranker-4B
    2. Input: (query, doc_content)
    3. Output: 重新計算分數並排序
    """
    def __init__(self, model_name: str = "Qwen/Qwen3-Reranker-4B", device: str = None):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        
        if torch is not None:
            self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
            self._load_model()
        else:
            self.device = "cpu"
            print("Warning: torch is not installed.")
        
    def _load_model(self):
        if AutoModelForSequenceClassification is None:
            print("Warning: transformers is not installed.")
            return

        # 在載入前先檢查 VRAM 是否足夠（4B reranker fp16 約需 8GB）
        if self.device == 'cuda':
            total_vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"[{self.__class__.__name__}] GPU VRAM: {total_vram_gb:.1f} GB")
            if total_vram_gb < 9.0:
                fallback_model = "Qwen/Qwen3-Reranker-0.6B"
                print(f"[{self.__class__.__name__}] Insufficient VRAM for {self.model_name} (~8GB needed), "
                      f"falling back to {fallback_model}")
                self.model_name = fallback_model

        try:
            print(f"Loading {self.model_name} on {self.device}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            # 先在 CPU 載入再移到 GPU，避免 float32 爆 VRAM
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            if self.device == 'cuda':
                self.model = self.model.half().to('cuda')
            else:
                self.model = self.model.to(self.device)
            self.model.eval()
            used_gb = torch.cuda.memory_allocated() / 1e9 if self.device == 'cuda' else 0
            print(f"Model loaded successfully. VRAM usage: {used_gb:.1f} GB")
        except Exception as e:
            print(f"Error loading model: {e}")

    def rerank(self, query: str, docs: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        傳入 20 筆混合檢索的文檔，返回精確評分後的 Top-10
        """
        if not docs:
            return []
            
        if self.model is None or self.tokenizer is None:
            # 回退：直接返回原本的排序
            return docs[:top_k]
            
        pairs = [[query, doc.get("content", "")] for doc in docs]
        
        results = []
        try:
            with torch.no_grad():
                inputs = self.tokenizer(
                    pairs, 
                    padding=True, 
                    truncation=True, 
                    return_tensors='pt', 
                    max_length=512
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # 計算 logits
                scores = self.model(**inputs, return_dict=True).logits.view(-1, ).float()
                
            for i, score in enumerate(scores):
                doc = docs[i].copy()
                doc['rerank_score'] = float(score)
                results.append(doc)
                
            results.sort(key=lambda x: x['rerank_score'], reverse=True)
            return results[:top_k]
        except Exception as e:
            print(f"Reranking error: {e}")
            return docs[:top_k]
