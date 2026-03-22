import os
import sys
import subprocess
import argparse
import time

def run_script(script_path, desc, *args):
    print(f"\n{'='*50}")
    print(f"執行: {desc}")
    print(f"腳本: {script_path}")
    print(f"{'='*50}\n")
    
    cmd = [sys.executable, script_path] + list(args)
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print(f"\n[錯誤] {desc} 執行失敗 (Code: {result.returncode})")
        sys.exit(result.returncode)
    
    print(f"\n[成功] {desc} 執行完成")

def main():
    parser = argparse.ArgumentParser(description="一鍵建立台灣法律 RAG 索引")
    parser.add_argument("--skip-download", action="store_true", help="跳過資料下載，使用現有 ChLaw.json")
    parser.add_argument("--force-download", action="store_true", help="強制重新下載資料，即使已是最新版本")
    parser.add_argument("--skip-data", action="store_true", help="跳過資料載入與切塊階段，僅重建索引")
    parser.add_argument("--test-limit", type=int, default=None, help="限制處理的資料筆數 (用於快速測試)")
    parser.add_argument("--batch-size", type=int, default=None, help="Batch size for embedding，不指定則自動依 VRAM 決定")
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    download_script = os.path.join(base_dir, "download_data.py")
    run_phase2_script = os.path.join(base_dir, "run_phase2.py")
    rebuild_index_script = os.path.abspath(os.path.join(base_dir, "..", "python-rag", "indexing", "rebuild_index.py"))
    
    start_time = time.time()

    # 0. 下載 / 更新法律資料
    if not args.skip_download and not args.skip_data:
        download_args = ["--force"] if args.force_download else []
        run_script(download_script, "Phase 0: 下載法律資料", *download_args)
    else:
        print("\n跳過資料下載...")
    
    # 1. 執行資料載入與切塊 (Phase 2)
    if not args.skip_data:
        run_script(run_phase2_script, "Phase 2: 資料處理與切塊")
    else:
        print("\n跳過 Phase 2 資料處理...")
        
    # 2. 執行索引建立 (Phase 3)
    chunks_path = os.path.abspath(os.path.join(base_dir, "..", "data", "chunks.json"))
    output_dir = os.path.abspath(os.path.join(base_dir, "..", "data"))
    
    index_args = [
        "--chunks-file", chunks_path,
        "--output-dir", output_dir
    ]
    if args.test_limit:
        index_args.extend(["--test-limit", str(args.test_limit)])
    if args.batch_size:
        index_args.extend(["--batch-size", str(args.batch_size)])
        
    run_script(rebuild_index_script, "Phase 3: 建立 FAISS 與 BM25 索引", *index_args)
    
    print("\n" + "="*50)
    print(f"🎉 全部索引建立完整！總耗時: {time.time()-start_time:.2f} 秒")
    print("="*50)

if __name__ == "__main__":
    main()
