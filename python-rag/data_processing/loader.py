import json
import logging

logger = logging.getLogger(__name__)

def load_law_data(file_path: str) -> list[dict]:
    """
    載入全國法規資料庫 (ChLaw.json) 等法律 JSON 資料
    支援處理 UTF-8 BOM 編碼格式
    """
    try:
        # 使用 utf-8-sig 可以自動處理並移除 UTF-8 的 BOM 標記
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
            
        if isinstance(data, list):
            logger.info(f"成功載入資料，共 {len(data)} 筆法律 (List Format)")
            return data
            
        if isinstance(data, dict):
            laws = data.get("Laws", data.get("laws", []))
            if not laws:
                logger.warning("資料庫中未找到 Laws 節點，回傳空集。")
            else:
                logger.info(f"成功載入資料，共 {len(laws)} 筆法律 (Dict Format)")
            return laws
            
        raise ValueError("JSON 格式不符合預期，應為 List 或包含 'Laws' 鍵的 Object。")
        
    except FileNotFoundError:
        logger.error(f"找不到檔案: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"解析 JSON 失敗: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"載入資料時發生未預期錯誤: {str(e)}")
        raise
