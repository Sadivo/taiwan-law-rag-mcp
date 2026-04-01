"""
tests/test_setup.py
Unit tests and property-based tests for scripts/setup.py

Validates: Requirements 5.2, 5.3, 5.4, 5.5
"""
from __future__ import annotations

import io
import sys
import importlib
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Import helper — setup.py lives in scripts/
# ---------------------------------------------------------------------------

import scripts.setup as _setup_module


def _get_setup():
    """Return the scripts.setup module (already imported)."""
    return _setup_module


# ---------------------------------------------------------------------------
# Unit Tests — Task 10.1
# ---------------------------------------------------------------------------

class TestStepEnvSkipsWhenEnvExists:
    """
    .env 已存在時 step_env() 不應覆蓋它。
    Validates: Requirements 5.3
    """

    def test_env_exists_not_overwritten(self, tmp_path, monkeypatch):
        setup = _get_setup()
        monkeypatch.chdir(tmp_path)

        # 建立 .env 與 .env.example，內容不同
        env_file = tmp_path / ".env"
        env_file.write_text("ORIGINAL=1")
        example_file = tmp_path / ".env.example"
        example_file.write_text("EXAMPLE=1")

        setup.step_env()

        # .env 內容不應被覆蓋
        assert env_file.read_text() == "ORIGINAL=1"

    def test_env_exists_prints_skip_message(self, tmp_path, monkeypatch, capsys):
        setup = _get_setup()
        monkeypatch.chdir(tmp_path)

        (tmp_path / ".env").write_text("KEY=value")
        (tmp_path / ".env.example").write_text("KEY=")

        setup.step_env()

        captured = capsys.readouterr()
        assert "跳過" in captured.out or "已存在" in captured.out


class TestAllStepsSuccessOutput:
    """
    全部步驟成功時輸出應包含啟動指令提示。
    Validates: Requirements 5.5
    """

    def test_success_output_contains_serve_command(self, capsys):
        setup = _get_setup()
        noop = MagicMock()
        fake_steps = [("s1", noop), ("s2", noop), ("s3", noop), ("s4", noop)]
        with patch.object(setup, "STEPS", fake_steps):
            setup.main()

        captured = capsys.readouterr()
        assert "uv run main.py serve" in captured.out

    def test_success_output_contains_completion_message(self, capsys):
        setup = _get_setup()
        noop = MagicMock()
        fake_steps = [("s1", noop), ("s2", noop), ("s3", noop), ("s4", noop)]
        with patch.object(setup, "STEPS", fake_steps):
            setup.main()

        captured = capsys.readouterr()
        assert "✓" in captured.out


# ---------------------------------------------------------------------------
# Property 7: Setup Script 進度訊息格式
# Validates: Requirements 5.2
# ---------------------------------------------------------------------------

@given(
    total=st.integers(min_value=1, max_value=10),
    offset=st.integers(min_value=0, max_value=9),
)
@settings(max_examples=100)
def test_property7_progress_message_format(total, offset):
    """
    # Feature: ux-optimization, Property 7: Setup Script 進度訊息格式
    Validates: Requirements 5.2

    For any step index n out of total steps total, run_step() should print
    a line matching the pattern [n/total] <description> before executing the step.
    """
    # Derive n in [1, total]
    n = (offset % total) + 1

    setup = _get_setup()

    captured_output = io.StringIO()
    mock_fn = MagicMock()
    desc = "測試步驟"

    with patch("sys.stdout", captured_output):
        setup.run_step(n, total, desc, mock_fn)

    output = captured_output.getvalue()
    expected_prefix = f"[{n}/{total}]"
    assert expected_prefix in output
    assert desc in output
    mock_fn.assert_called_once()


# ---------------------------------------------------------------------------
# Property 8: Setup Script 失敗處理
# Validates: Requirements 5.4
# ---------------------------------------------------------------------------

@given(
    step_index=st.integers(min_value=0, max_value=3),
    error_message=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
    fix_cmd=st.text(min_size=1, max_size=80).filter(lambda s: s.strip()),
)
@settings(max_examples=50)
def test_property8_failure_handling(step_index, error_message, fix_cmd):
    """
    # Feature: ux-optimization, Property 8: Setup Script 失敗處理
    Validates: Requirements 5.4

    For any step that raises a StepError, the setup script should print
    the failure reason and a suggested fix command to stderr, then exit
    with a non-zero exit code.
    """
    setup = _get_setup()

    # Build a fake STEPS list where step at step_index raises StepError
    def make_failing():
        raise setup.StepError(message=error_message, fix_command=fix_cmd)

    noop = MagicMock()
    # Build steps: all noop before the failing one, then failing, rest don't matter
    fake_steps = []
    for i in range(4):
        if i == step_index:
            fake_steps.append((f"步驟{i+1}", make_failing))
        else:
            fake_steps.append((f"步驟{i+1}", noop))

    fake_stderr = io.StringIO()

    with patch.object(setup, "STEPS", fake_steps):
        with patch("sys.stderr", fake_stderr):
            with pytest.raises(SystemExit) as exc_info:
                setup.main()

    # exit code must be non-zero
    assert exc_info.value.code != 0

    # stderr must contain the error message and fix command
    stderr_output = fake_stderr.getvalue()
    assert error_message in stderr_output
    assert fix_cmd in stderr_output
