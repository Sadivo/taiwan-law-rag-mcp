import sys
import os
import json

# 設定 python-rag 到載入路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'python-rag'))

from data_processing.loader import load_law_data
from data_processing.law_aliases import normalize_law_name
from data_processing.chunker import process_law_articles
from utils.article_parser import normalize_article_no

def run_tests():
    print("Testing normalize_law_name...")
    assert normalize_law_name("勞基法") == "勞動基準法"
    
    print("Testing normalize_article_no...")
    assert normalize_article_no("第38條") == "第 38 條"
    assert normalize_article_no("第 38 條之 1") == "第 38-1 條"
    
    print("Creating mock law data...")
    mock_data = {
        "Laws": [
            {
                "LawName": "勞動基準法",
                "LawLevel": "法律",
                "LawCategory": "行政>勞動部",
                "LawURL": "https://law.moj.gov.tw/123",
                "LawModifiedDate": "20231201",
                "LawAbolished": "N",
                "LawHasEng": "Y",
                "LawArticles": [
                    {
                        "ArticleType": "C",
                        "ArticleContent": "第一章 總則"
                    },
                    {
                        "ArticleType": "A",
                        "ArticleNo": "第 1 條",
                        "ArticleContent": "為規定勞動條件最低標準，保障勞工權益，加強勞雇關係..."
                    },
                    {
                        "ArticleType": "A",
                        "ArticleNo": "第 2 條",
                        "ArticleContent": "A" * 300 + "\n" + "B" * 300
                    }
                ]
            }
        ]
    }
    
    # 儲存 mock
    mock_file = os.path.join(os.environ.get('TEMP', '.'), 'mock_law.json')
    with open(mock_file, 'w', encoding='utf-8-sig') as f:
        json.dump(mock_data, f, ensure_ascii=False)
        
    print("Testing loader...")
    laws = load_law_data(mock_file)
    assert len(laws) == 1
    
    print("Testing chunker...")
    chunks = process_law_articles(laws)
    print(f"Generated {len(chunks)} chunks.")
    
    for c in chunks:
        print(f"ID: {c['id']}\nMetadata: {c['metadata']}\n")
        
    assert len(chunks) == 3
    assert chunks[0]['id'] == "勞動基準法_第 1 條"
    assert chunks[0]['metadata']['chapter'] == "第一章 總則"
    assert "勞基法" in chunks[0]['metadata']['aliases']
    assert chunks[1]['id'] == "勞動基準法_第 2 條_part1"
    assert chunks[2]['id'] == "勞動基準法_第 2 條_part2"
    
    print("\n✅ ALL TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
