import re

def normalize_article_no(raw_no: str) -> str:
    """
    條號文字正規化，將不同表記方法統一
    例：'第38條' -> '第 38 條', '第38之1條', '第 38 條之 1' -> '第 38-1 條'
    """
    if not isinstance(raw_no, str):
        return str(raw_no) if raw_no else ""
        
    raw_no = raw_no.strip().replace(' ', '')
    if not raw_no:
        return ""
        
    # 辨識 '第X條' 或 '第X條之Y'、'第X-Y條' 等格式
    # 第一部分的數字: X
    # 若有之Y或-Y: \D*(\d+)? 表示可以匹配 '之1' 或 '-1' 中的數字 1
    match = re.search(r'第?(\d+)(?:[條\-\_之]+(\d+))?[條\s]*$', raw_no)
    
    if match:
        main_no = match.group(1)
        sub_no = match.group(2)
        if sub_no:
            # 正規為 '第 X-Y 條' (以方便精確查找或作為統一格式)
            # 或者依據文件範例使用 '第 X 條之 Y'。此處我們先將其轉為 '第 X-Y 條'
            return f"第 {main_no}-{sub_no} 條"
        return f"第 {main_no} 條"
        
    # 如果都抓不到（例如是 '附表一'），維持原樣但去除多餘空白
    return raw_no
