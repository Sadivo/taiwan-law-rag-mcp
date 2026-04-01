"""
tests/test_cli_dispatcher.py
Unit tests and property-based tests for the CLI Dispatcher (root main.py)

Validates: Requirements 4.1, 4.6, 4.7
"""
from __future__ import annotations

import os
import sys
import importlib
import importlib.util
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROOT_MAIN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")


def _load_cli_module():
    """Load the root main.py (CLI dispatcher) explicitly by file path."""
    spec = importlib.util.spec_from_file_location("cli_main", _ROOT_MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_main(*argv):
    """Run cli_main.main() with the given argv, capturing SystemExit."""
    cli_module = _load_cli_module()
    with patch.object(sys, "argv", ["main.py", *argv]):
        with pytest.raises(SystemExit) as exc_info:
            cli_module.main()
    return exc_info.value.code


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

class TestNoSubcommand:
    """未提供子命令時 exit code 為 1 (Requirement 4.6)"""

    def test_no_subcommand_exits_with_code_1(self, capsys):
        code = run_main()
        assert code == 1

    def test_no_subcommand_prints_help(self, capsys):
        cli_module = _load_cli_module()
        with patch.object(sys, "argv", ["main.py"]):
            with pytest.raises(SystemExit):
                cli_module.main()
        captured = capsys.readouterr()
        # help output should mention subcommands
        assert "serve" in captured.out or "usage" in captured.out.lower()


class TestUnknownSubcommand:
    """未知子命令時 exit code 為 2（argparse 預設行為）(Requirement 4.6)"""

    def test_unknown_subcommand_exits_with_code_2(self):
        code = run_main("unknown_subcommand_xyz")
        assert code == 2


class TestExceptionHandling:
    """子命令拋出例外時 stderr 包含錯誤訊息且 exit code 為 1 (Requirement 4.7)"""

    def test_exception_in_serve_writes_to_stderr_and_exits_1(self, capsys):
        cli_module = _load_cli_module()
        with patch.object(sys, "argv", ["main.py", "serve"]):
            with patch.object(cli_module, "cmd_serve", side_effect=RuntimeError("serve failed")):
                with pytest.raises(SystemExit) as exc_info:
                    cli_module.main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "serve failed" in captured.err

    def test_exception_in_index_writes_to_stderr_and_exits_1(self, capsys):
        cli_module = _load_cli_module()
        with patch.object(sys, "argv", ["main.py", "index"]):
            with patch.object(cli_module, "cmd_index", side_effect=ValueError("index error")):
                with pytest.raises(SystemExit) as exc_info:
                    cli_module.main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "index error" in captured.err

    def test_exception_message_appears_in_stderr(self, capsys):
        cli_module = _load_cli_module()
        error_msg = "something went terribly wrong"
        with patch.object(sys, "argv", ["main.py", "check"]):
            with patch.object(cli_module, "cmd_check", side_effect=Exception(error_msg)):
                with pytest.raises(SystemExit) as exc_info:
                    cli_module.main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert error_msg in captured.err


# ---------------------------------------------------------------------------
# Property 5: CLI Dispatcher 識別所有合法子命令
# Validates: Requirements 4.1
# ---------------------------------------------------------------------------

VALID_SUBCOMMANDS = ["serve", "index", "eval", "check"]
HANDLER_MAP = {
    "serve": "cmd_serve",
    "index": "cmd_index",
    "eval": "cmd_eval",
    "check": "cmd_check",
}


@given(subcommand=st.sampled_from(VALID_SUBCOMMANDS))
@settings(max_examples=20)
def test_property5_all_valid_subcommands_dispatched(subcommand):
    """
    # Feature: ux-optimization, Property 5: CLI Dispatcher 識別所有合法子命令
    Validates: Requirements 4.1

    For any subcommand in (serve, index, eval, check), invoking main.py <subcommand>
    should dispatch to the corresponding handler without raising an unhandled exception.
    """
    import io
    cli_module = _load_cli_module()

    handler_name = HANDLER_MAP[subcommand]
    mock_handler = MagicMock()

    with patch.object(sys, "argv", ["main.py", subcommand]):
        with patch.object(cli_module, handler_name, mock_handler):
            # Should not raise SystemExit (no exception in handler)
            cli_module.main()

    mock_handler.assert_called_once()


# ---------------------------------------------------------------------------
# Property 6: CLI Dispatcher 例外處理
# Validates: Requirements 4.7
# ---------------------------------------------------------------------------

@given(
    subcommand=st.sampled_from(VALID_SUBCOMMANDS),
    error_message=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
)
@settings(max_examples=30)
def test_property6_exception_handling(subcommand, error_message):
    """
    # Feature: ux-optimization, Property 6: CLI Dispatcher 例外處理
    Validates: Requirements 4.7

    For any subcommand and any exception raised during its execution,
    the CLI Dispatcher should write a human-readable message to stderr
    and exit with a non-zero exit code.
    """
    import io
    cli_module = _load_cli_module()

    handler_name = HANDLER_MAP[subcommand]
    fake_stderr = io.StringIO()

    with patch.object(sys, "argv", ["main.py", subcommand]):
        with patch.object(cli_module, handler_name, side_effect=Exception(error_message)):
            with patch("sys.stderr", fake_stderr):
                with pytest.raises(SystemExit) as exc_info:
                    cli_module.main()

    # exit code must be non-zero
    assert exc_info.value.code != 0

    # stderr must contain the error message
    assert error_message in fake_stderr.getvalue()
