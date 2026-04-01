"""
tests/ux_optimization/test_health_endpoint.py
Unit tests for GET /health endpoint logic in python-rag/main.py

Tests ok / degraded / error states and the 503 when health state is uninitialized.
We test the endpoint function directly (bypassing TestClient) because the installed
starlette/httpx versions are incompatible for TestClient usage.

Validates: Requirements 7.3, 7.4, 7.5
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from api.health import HealthState, ProviderInfo, ProviderStatus, set_health_state
import api.health as health_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(e: ProviderStatus, r: ProviderStatus, g: ProviderStatus) -> HealthState:
    return HealthState(
        embedding=ProviderInfo(name="local:emb", status=e),
        reranking=ProviderInfo(name="local:rer", status=r),
        generation=ProviderInfo(name="ollama:gen", status=g),
    )


def _run(coro):
    """Run a coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Import the health_check endpoint function from main
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_health_state():
    """Reset health singleton before each test."""
    health_module._health_state = None
    yield
    health_module._health_state = None


# We import health_check lazily to avoid triggering lifespan at import time.
def _get_health_check():
    import main as m
    return m.health_check


# ---------------------------------------------------------------------------
# Tests: all providers ok → HTTP 200, status=ok
# Validates: Requirements 7.3
# ---------------------------------------------------------------------------

def test_health_ok_returns_200():
    set_health_state(_make_state(ProviderStatus.OK, ProviderStatus.OK, ProviderStatus.OK))
    health_check = _get_health_check()
    result = _run(health_check())
    assert result.status == "ok"


def test_health_ok_provider_names():
    set_health_state(_make_state(ProviderStatus.OK, ProviderStatus.OK, ProviderStatus.OK))
    health_check = _get_health_check()
    result = _run(health_check())
    assert result.embedding_provider == "local:emb"
    assert result.reranking_provider == "local:rer"
    assert result.generation_provider.name == "ollama:gen"
    assert result.generation_provider.status == "ok"


# ---------------------------------------------------------------------------
# Tests: generation unreachable → HTTP 200, status=degraded
# Validates: Requirements 7.4
# ---------------------------------------------------------------------------

def test_health_degraded_status():
    set_health_state(_make_state(ProviderStatus.OK, ProviderStatus.OK, ProviderStatus.UNREACHABLE))
    health_check = _get_health_check()
    result = _run(health_check())
    assert result.status == "degraded"


def test_health_degraded_generation_status():
    set_health_state(_make_state(ProviderStatus.OK, ProviderStatus.OK, ProviderStatus.UNREACHABLE))
    health_check = _get_health_check()
    result = _run(health_check())
    assert result.generation_provider.status == "unreachable"


# ---------------------------------------------------------------------------
# Tests: any provider error → raises HTTPException with 503
# Validates: Requirements 7.5
# ---------------------------------------------------------------------------

def test_health_error_raises_503():
    from fastapi import HTTPException
    set_health_state(_make_state(ProviderStatus.ERROR, ProviderStatus.OK, ProviderStatus.OK))
    health_check = _get_health_check()
    with pytest.raises(HTTPException) as exc_info:
        _run(health_check())
    assert exc_info.value.status_code == 503


def test_health_error_with_unreachable_raises_503():
    from fastapi import HTTPException
    set_health_state(_make_state(ProviderStatus.ERROR, ProviderStatus.UNREACHABLE, ProviderStatus.OK))
    health_check = _get_health_check()
    with pytest.raises(HTTPException) as exc_info:
        _run(health_check())
    assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# Tests: HealthState not initialized → raises HTTPException with 503
# Validates: Requirements 7.5
# ---------------------------------------------------------------------------

def test_health_uninitialized_raises_503():
    from fastapi import HTTPException
    # health_module._health_state is already None (reset by fixture)
    health_check = _get_health_check()
    with pytest.raises(HTTPException) as exc_info:
        _run(health_check())
    assert exc_info.value.status_code == 503
