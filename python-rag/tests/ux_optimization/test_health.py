"""
tests/ux_optimization/test_health.py
Unit tests and property-based tests for python-rag/api/health.py
"""
from __future__ import annotations

import io
import sys
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from api.health import (
    HealthState,
    ProviderInfo,
    ProviderStatus,
    check_generation_reachable,
    print_startup_summary,
)

# ---------------------------------------------------------------------------
# Unit tests – HealthState.overall_status  (Task 5.1)
# Validates: Requirements 7.3, 7.4
# ---------------------------------------------------------------------------

def _make_state(e: ProviderStatus, r: ProviderStatus, g: ProviderStatus) -> HealthState:
    return HealthState(
        embedding=ProviderInfo(name="emb", status=e),
        reranking=ProviderInfo(name="rer", status=r),
        generation=ProviderInfo(name="gen", status=g),
    )


def test_overall_status_all_ok():
    state = _make_state(ProviderStatus.OK, ProviderStatus.OK, ProviderStatus.OK)
    assert state.overall_status == "ok"


def test_overall_status_one_unreachable():
    state = _make_state(ProviderStatus.OK, ProviderStatus.OK, ProviderStatus.UNREACHABLE)
    assert state.overall_status == "degraded"


def test_overall_status_all_unreachable():
    state = _make_state(
        ProviderStatus.UNREACHABLE, ProviderStatus.UNREACHABLE, ProviderStatus.UNREACHABLE
    )
    assert state.overall_status == "degraded"


def test_overall_status_one_error():
    state = _make_state(ProviderStatus.OK, ProviderStatus.OK, ProviderStatus.ERROR)
    assert state.overall_status == "error"


def test_overall_status_error_beats_unreachable():
    state = _make_state(ProviderStatus.ERROR, ProviderStatus.UNREACHABLE, ProviderStatus.OK)
    assert state.overall_status == "error"


def test_overall_status_all_error():
    state = _make_state(ProviderStatus.ERROR, ProviderStatus.ERROR, ProviderStatus.ERROR)
    assert state.overall_status == "error"


# ---------------------------------------------------------------------------
# Unit tests – print_startup_summary
# ---------------------------------------------------------------------------

def _capture_summary(state: HealthState, host: str = "127.0.0.1", port: int = 8073) -> str:
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        print_startup_summary(state, host, port)
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


def test_print_startup_summary_contains_url():
    state = _make_state(ProviderStatus.OK, ProviderStatus.OK, ProviderStatus.OK)
    output = _capture_summary(state, host="127.0.0.1", port=8073)
    assert "http://127.0.0.1:8073" in output


def test_print_startup_summary_ok_symbol():
    state = HealthState(
        embedding=ProviderInfo(name="local:emb", status=ProviderStatus.OK),
        reranking=ProviderInfo(name="local:rer", status=ProviderStatus.OK),
        generation=ProviderInfo(name="ollama:gen", status=ProviderStatus.OK),
    )
    output = _capture_summary(state)
    assert output.count("✓") == 3
    assert "✗" not in output


def test_print_startup_summary_unreachable_symbol():
    state = HealthState(
        embedding=ProviderInfo(name="local:emb", status=ProviderStatus.OK),
        reranking=ProviderInfo(name="local:rer", status=ProviderStatus.OK),
        generation=ProviderInfo(name="ollama:gen", status=ProviderStatus.UNREACHABLE),
    )
    output = _capture_summary(state)
    assert "✗" in output
    assert output.count("✓") == 2


def test_print_startup_summary_provider_names_present():
    state = HealthState(
        embedding=ProviderInfo(name="local:Qwen3-Embedding-4B", status=ProviderStatus.OK),
        reranking=ProviderInfo(name="local:Qwen3-Reranker-4B", status=ProviderStatus.OK),
        generation=ProviderInfo(name="ollama:qwen3:8b", status=ProviderStatus.UNREACHABLE),
    )
    output = _capture_summary(state)
    assert "local:Qwen3-Embedding-4B" in output
    assert "local:Qwen3-Reranker-4B" in output
    assert "ollama:qwen3:8b" in output


# ---------------------------------------------------------------------------
# Unit tests – check_generation_reachable
# ---------------------------------------------------------------------------

def test_check_generation_reachable_ok():
    provider = MagicMock()
    provider.generate.return_value = ""
    assert check_generation_reachable(provider) == ProviderStatus.OK


def test_check_generation_reachable_exception():
    provider = MagicMock()
    provider.generate.side_effect = ConnectionError("refused")
    assert check_generation_reachable(provider) == ProviderStatus.UNREACHABLE


def test_check_generation_reachable_any_exception():
    provider = MagicMock()
    provider.generate.side_effect = RuntimeError("unexpected")
    assert check_generation_reachable(provider) == ProviderStatus.UNREACHABLE


# ---------------------------------------------------------------------------
# Property 10: /health overall_status 由最差 provider 決定
# Feature: ux-optimization, Property 10: overall_status priority rule
# Validates: Requirements 7.3, 7.4
# ---------------------------------------------------------------------------

provider_status_st = st.sampled_from(list(ProviderStatus))


@given(
    e=provider_status_st,
    r=provider_status_st,
    g=provider_status_st,
)
@settings(max_examples=200)
def test_property_overall_status_priority(e, r, g):
    """**Validates: Requirements 7.3, 7.4**

    Property 10: /health overall_status 由最差 provider 決定
    - error > unreachable > ok
    """
    state = _make_state(e, r, g)
    statuses = {e, r, g}
    overall = state.overall_status

    if ProviderStatus.ERROR in statuses:
        assert overall == "error"
    elif ProviderStatus.UNREACHABLE in statuses:
        assert overall == "degraded"
    else:
        assert overall == "ok"


# ---------------------------------------------------------------------------
# Property 9: Startup Summary 格式正確性
# Feature: ux-optimization, Property 9: Startup Summary format correctness
# Validates: Requirements 6.1, 6.2
# ---------------------------------------------------------------------------

# Strategy for provider names: printable ASCII text, non-empty
provider_name_st = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-:_"),
    min_size=1,
    max_size=40,
)

host_st = st.just("127.0.0.1")
port_st = st.integers(min_value=1024, max_value=65535)


@given(
    emb_name=provider_name_st,
    rer_name=provider_name_st,
    gen_name=provider_name_st,
    emb_status=provider_status_st,
    rer_status=provider_status_st,
    gen_status=provider_status_st,
    host=host_st,
    port=port_st,
)
@settings(max_examples=200)
def test_property_startup_summary_format(
    emb_name, rer_name, gen_name, emb_status, rer_status, gen_status, host, port
):
    """**Validates: Requirements 6.1, 6.2**

    Property 9: Startup Summary 格式正確性
    - 輸出包含 URL
    - 輸出包含所有 provider 名稱
    - 使用正確符號（✓ for ok, ✗ for unreachable/error）
    """
    state = HealthState(
        embedding=ProviderInfo(name=emb_name, status=emb_status),
        reranking=ProviderInfo(name=rer_name, status=rer_status),
        generation=ProviderInfo(name=gen_name, status=gen_status),
    )
    output = _capture_summary(state, host=host, port=port)

    # URL must be present
    assert f"http://{host}:{port}" in output

    # All provider names must appear
    assert emb_name in output
    assert rer_name in output
    assert gen_name in output

    # Correct symbols
    def expected_symbol(status: ProviderStatus) -> str:
        return "✓" if status == ProviderStatus.OK else "✗"

    # Provider lines are the 2nd, 3rd, 4th lines (index 1, 2, 3)
    lines = output.splitlines()
    assert len(lines) >= 4, f"Expected at least 4 lines, got: {output!r}"
    emb_line = lines[1]
    rer_line = lines[2]
    gen_line = lines[3]

    assert emb_name in emb_line
    assert rer_name in rer_line
    assert gen_name in gen_line

    assert expected_symbol(emb_status) in emb_line
    assert expected_symbol(rer_status) in rer_line
    assert expected_symbol(gen_status) in gen_line
