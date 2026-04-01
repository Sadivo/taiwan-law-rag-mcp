"""
main.py — CLI Dispatcher for Taiwan Law RAG
統一命令列入口，支援 serve / index / eval / check 四個子命令
"""
from __future__ import annotations

import argparse
import os
import sys


def cmd_serve(args) -> None:
    """啟動 FastAPI server（等同於 uv run python-rag/main.py）"""
    rag_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python-rag")
    if rag_dir not in sys.path:
        sys.path.insert(0, rag_dir)

    import uvicorn

    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8073") or "8073")
    uvicorn.run("main:app", host=host, port=port)


def cmd_index(args) -> None:
    """執行 python-rag/indexing/rebuild_index.py 的索引重建流程"""
    rag_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python-rag")
    if rag_dir not in sys.path:
        sys.path.insert(0, rag_dir)

    from indexing.rebuild_index import main as rebuild_main
    rebuild_main()


def cmd_eval(args) -> None:
    """執行評估框架"""
    rag_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python-rag")
    if rag_dir not in sys.path:
        sys.path.insert(0, rag_dir)

    try:
        from evaluation.run_evaluation import main as eval_main
    except ImportError:
        # 若 run_evaluation.py 不存在，嘗試 evaluator 模組
        try:
            from evaluation.evaluator import main as eval_main
        except (ImportError, AttributeError) as exc:
            raise ImportError(
                "找不到評估模組的 main() 函式。"
                "請確認 python-rag/evaluation/run_evaluation.py 或 evaluator.py 存在。"
            ) from exc

    eval_main()


def cmd_check(args) -> None:
    """執行 Health Check 並輸出每個 provider 的狀態，不啟動 FastAPI"""
    rag_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python-rag")
    if rag_dir not in sys.path:
        sys.path.insert(0, rag_dir)

    from dotenv import load_dotenv
    load_dotenv()

    from providers.factory import ProviderFactory
    from api.health import (
        HealthState,
        ProviderInfo,
        ProviderStatus,
        check_generation_reachable,
        print_startup_summary,
    )

    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8073") or "8073")

    # 初始化 embedding + reranking（失敗則拋出）
    embedding_provider, reranking_provider = ProviderFactory.from_env()

    # 初始化 generation（失敗標記 unreachable）
    generation_provider = None
    try:
        generation_provider = ProviderFactory.generation_from_env()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Generation provider 初始化失敗：%s", exc)

    # 組裝 HealthState
    def _display_name(provider) -> str:
        if hasattr(provider, "_embedder"):
            model = getattr(provider._embedder, "model_name", "")
            short = model.split("/")[-1] if model else type(provider).__name__
            return f"local:{short}"
        if hasattr(provider, "_reranker"):
            model = getattr(provider._reranker, "model_name", "")
            short = model.split("/")[-1] if model else type(provider).__name__
            return f"local:{short}"
        if hasattr(provider, "_config"):
            cfg = provider._config
            ptype = getattr(cfg, "provider_type", "unknown")
            model = getattr(cfg, "model_name", None) or ""
            short = model.split("/")[-1] if model else ptype
            return f"{ptype}:{short}" if short else ptype
        return type(provider).__name__

    def _gen_display_name() -> str:
        ptype = os.getenv("GENERATION_PROVIDER", "ollama")
        model = os.getenv("GENERATION_MODEL_NAME", "")
        if model:
            return f"{ptype}:{model.split('/')[-1]}"
        return ptype

    if generation_provider is None:
        gen_name = _gen_display_name()
        gen_status = ProviderStatus.UNREACHABLE
    else:
        gen_name = _display_name(generation_provider) or _gen_display_name()
        gen_status = check_generation_reachable(generation_provider)

    state = HealthState(
        embedding=ProviderInfo(name=_display_name(embedding_provider), status=ProviderStatus.OK),
        reranking=ProviderInfo(name=_display_name(reranking_provider), status=ProviderStatus.OK),
        generation=ProviderInfo(name=gen_name, status=gen_status),
    )

    print_startup_summary(state, host, port)

    # exit 1 if error, 0 if ok or degraded
    if state.overall_status == "error":
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Taiwan Law RAG — 統一 CLI 入口",
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    # serve
    serve_parser = subparsers.add_parser("serve", help="啟動 FastAPI server")
    serve_parser.set_defaults(func=cmd_serve)

    # index
    index_parser = subparsers.add_parser("index", help="重建向量與 BM25 索引")
    index_parser.set_defaults(func=cmd_index)

    # eval
    eval_parser = subparsers.add_parser("eval", help="執行評估框架")
    eval_parser.set_defaults(func=cmd_eval)

    # check
    check_parser = subparsers.add_parser("check", help="執行 Health Check（不啟動 FastAPI）")
    check_parser.set_defaults(func=cmd_check)

    args = parser.parse_args()

    # 未提供子命令時印出 help 並以 exit code 1 結束
    if args.subcommand is None:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except Exception as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
