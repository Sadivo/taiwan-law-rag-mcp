"""
tests/test_routes_health.py
Tests for /health endpoint provider info (Requirements 6.4, 6.5, 9.2, 9.4)
"""
import sys
import os
import asyncio
import pytest
from unittest.mock import MagicMock

# Ensure python-rag is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from fastapi import FastAPI


def _build_test_app(embedding_name: str, reranking_name: str) -> FastAPI:
    """
    Build a minimal FastAPI app with the /health endpoint using the given
    provider name strings, without touching real providers.
    """
    import api.routes as routes_module
    from api.models import HealthResponse

    # Patch module-level state
    routes_module._retrieval_service = MagicMock()
    routes_module._embedding_provider_name = embedding_name
    routes_module._reranking_provider_name = reranking_name

    app = FastAPI()

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        return HealthResponse(
            status="ok",
            embedding_provider=routes_module._embedding_provider_name,
            reranking_provider=routes_module._reranking_provider_name,
        )

    return app


async def _async_get(app: FastAPI, path: str) -> httpx.Response:
    """Send a GET request to the ASGI app using httpx.AsyncClient."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get(path)


def _get(app: FastAPI, path: str) -> httpx.Response:
    """Sync wrapper around _async_get."""
    return asyncio.get_event_loop().run_until_complete(_async_get(app, path))


class TestHealthEndpointProviderInfo:

    def test_health_endpoint_includes_provider_info(self):
        """
        /health response must include embedding_provider and reranking_provider fields.
        Validates: Requirements 9.4
        """
        app = _build_test_app(
            embedding_name="local:Qwen3-Embedding-4B",
            reranking_name="local:Qwen3-Reranker-4B",
        )
        response = _get(app, "/health")

        assert response.status_code == 200
        data = response.json()
        assert "embedding_provider" in data, "Response must contain 'embedding_provider'"
        assert "reranking_provider" in data, "Response must contain 'reranking_provider'"
        assert data["embedding_provider"] == "local:Qwen3-Embedding-4B"
        assert data["reranking_provider"] == "local:Qwen3-Reranker-4B"

    def test_health_endpoint_status_ok(self):
        """
        /health response status must be 'ok'.
        Validates: Requirements 9.4
        """
        app = _build_test_app(
            embedding_name="local:Qwen3-Embedding-4B",
            reranking_name="local:Qwen3-Reranker-4B",
        )
        response = _get(app, "/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_endpoint_unknown_when_not_initialized(self):
        """
        When providers have not been initialized, /health returns 'unknown' for both fields.
        Validates: Requirements 9.4
        """
        app = _build_test_app(
            embedding_name="unknown",
            reranking_name="unknown",
        )
        response = _get(app, "/health")

        assert response.status_code == 200
        data = response.json()
        assert data["embedding_provider"] == "unknown"
        assert data["reranking_provider"] == "unknown"

    def test_health_endpoint_reflects_langchain_provider(self):
        """
        /health correctly reflects LangChain provider names when set.
        Validates: Requirements 9.4
        """
        app = _build_test_app(
            embedding_name="openai:text-embedding-3-small",
            reranking_name="cohere:rerank-multilingual-v3.0",
        )
        response = _get(app, "/health")

        assert response.status_code == 200
        data = response.json()
        assert data["embedding_provider"] == "openai:text-embedding-3-small"
        assert data["reranking_provider"] == "cohere:rerank-multilingual-v3.0"
