import os
import sys
import json
import time

# 將專案根目錄加到 sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'python-rag'))

from data_processing.loader import load_law_data
from data_processing.chunker import process_law_articles

def main():
    print("=" * 50)
    print("🚀 Starting Data Processing (Phase 2)")
    print("=" * 50)
    
    input_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'ChLaw.json', 'ChLaw.json'))
    output_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'chunks.json'))
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    t0 = time.time()
    print(f"Loading data from {input_file}...")
    laws = load_law_data(input_file)
    print(f"Loaded in {time.time()-t0:.2f}s")
    
    t1 = time.time()
    print("Chunking articles...")
    chunks = process_law_articles(laws)
    print(f"Generated {len(chunks)} chunks in {time.time()-t1:.2f}s")
    
    t2 = time.time()
    print(f"Saving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"Saved in {time.time()-t2:.2f}s")
    
    print("=" * 50)
    print("✨ Phase 2 Completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()
