"""
Property-based tests for UX Optimization spec — documentation coverage.

# Feature: ux-optimization, Property 1: 文件涵蓋所有支援的 Provider
"""
import os
import pytest
from hypothesis import given, settings, strategies as st

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_installation_md() -> str:
    """Load docs/INSTALLATION.md relative to the workspace root."""
    workspace_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    path = os.path.join(workspace_root, "docs", "INSTALLATION.md")
    with open(path, encoding="utf-8") as f:
        return f.read()


INSTALLATION_CONTENT = _load_installation_md()

EMBEDDING_PROVIDERS = ["local", "openai", "cohere", "voyageai"]
GENERATION_PROVIDERS = ["ollama", "openai", "anthropic"]
ALL_PROVIDERS = list(set(EMBEDDING_PROVIDERS + GENERATION_PROVIDERS))

# ---------------------------------------------------------------------------
# Property 1: 文件涵蓋所有支援的 Provider
# Validates: Requirements 1.3, 1.4
# ---------------------------------------------------------------------------

@given(st.sampled_from(EMBEDDING_PROVIDERS))
@settings(max_examples=100)
def test_property1_installation_covers_embedding_providers(provider: str):
    """
    **Validates: Requirements 1.3**

    For any embedding provider name in the supported list,
    docs/INSTALLATION.md must contain a .env configuration example for it.
    """
    # Feature: ux-optimization, Property 1: 文件涵蓋所有支援的 Provider
    assert provider in INSTALLATION_CONTENT, (
        f"docs/INSTALLATION.md does not contain a .env example for "
        f"embedding provider: {provider!r}"
    )


@given(st.sampled_from(GENERATION_PROVIDERS))
@settings(max_examples=100)
def test_property1_installation_covers_generation_providers(provider: str):
    """
    **Validates: Requirements 1.4**

    For any generation provider name in the supported list,
    docs/INSTALLATION.md must contain a .env configuration example for it.
    """
    # Feature: ux-optimization, Property 1: 文件涵蓋所有支援的 Provider
    assert provider in INSTALLATION_CONTENT, (
        f"docs/INSTALLATION.md does not contain a .env example for "
        f"generation provider: {provider!r}"
    )


# ---------------------------------------------------------------------------
# Helpers for USAGE.md
# ---------------------------------------------------------------------------

def _load_usage_md() -> str:
    """Load docs/USAGE.md relative to the workspace root."""
    workspace_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    path = os.path.join(workspace_root, "docs", "USAGE.md")
    with open(path, encoding="utf-8") as f:
        return f.read()


USAGE_CONTENT = _load_usage_md()

MCP_TOOLS = [
    "semantic_search",
    "exact_search",
    "search_law_by_name",
    "get_law_full_text",
    "compare_laws",
    "ask_law_question",
]

CLI_SUBCOMMANDS = ["serve", "index", "eval", "check"]

# ---------------------------------------------------------------------------
# Property 2: USAGE.md 涵蓋所有 MCP 工具
# Validates: Requirements 2.1
# ---------------------------------------------------------------------------

@given(st.sampled_from(MCP_TOOLS))
@settings(max_examples=100)
def test_property2_usage_covers_mcp_tools(tool: str):
    """
    **Validates: Requirements 2.1**

    For any MCP tool name in the defined tool list,
    docs/USAGE.md must contain a usage example for that tool.
    """
    # Feature: ux-optimization, Property 2: USAGE.md 涵蓋所有 MCP 工具
    assert tool in USAGE_CONTENT, (
        f"docs/USAGE.md does not contain a usage example for MCP tool: {tool!r}"
    )


# ---------------------------------------------------------------------------
# Property 3: USAGE.md 涵蓋所有 CLI 子命令
# Validates: Requirements 2.4
# ---------------------------------------------------------------------------

@given(st.sampled_from(CLI_SUBCOMMANDS))
@settings(max_examples=100)
def test_property3_usage_covers_cli_subcommands(subcommand: str):
    """
    **Validates: Requirements 2.4**

    For any CLI subcommand in (serve, index, eval, check),
    docs/USAGE.md must contain a description of that subcommand.
    """
    # Feature: ux-optimization, Property 3: USAGE.md 涵蓋所有 CLI 子命令
    assert subcommand in USAGE_CONTENT, (
        f"docs/USAGE.md does not contain a description for CLI subcommand: {subcommand!r}"
    )


# ---------------------------------------------------------------------------
# Helpers for API.md
# ---------------------------------------------------------------------------

def _load_api_md() -> str:
    """Load docs/API.md relative to the workspace root."""
    workspace_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    path = os.path.join(workspace_root, "docs", "API.md")
    with open(path, encoding="utf-8") as f:
        return f.read()


API_CONTENT = _load_api_md()

ENDPOINTS = [
    "/search/semantic",
    "/search/exact",
    "/search/law",
    "/law/full",
    "/law/compare",
    "/chat",
    "/session",
    "/health",
]

# ---------------------------------------------------------------------------
# Property 4: API.md 涵蓋所有 Endpoint
# Validates: Requirements 3.1, 3.2, 3.3
# ---------------------------------------------------------------------------

@given(st.sampled_from(ENDPOINTS))
@settings(max_examples=100)
def test_property4_api_md_covers_all_endpoints(endpoint: str):
    """
    **Validates: Requirements 3.1, 3.2, 3.3**

    For any endpoint path in the defined endpoint list,
    docs/API.md must contain:
    1. The endpoint path string
    2. At least one JSON request example (```json near the endpoint)
    3. At least one JSON response example
    """
    # Feature: ux-optimization, Property 4: API.md 涵蓋所有 Endpoint

    # 1. Endpoint path must appear in API.md
    assert endpoint in API_CONTENT, (
        f"docs/API.md does not contain endpoint path: {endpoint!r}"
    )

    # 2 & 3. Verify JSON examples exist near the endpoint section.
    # Find the position of the endpoint in the document, then check that
    # at least two ```json blocks appear after it (request + response).
    endpoint_pos = API_CONTENT.find(endpoint)
    assert endpoint_pos != -1  # already checked above, but be explicit

    # Look at the content from the endpoint occurrence onward (up to next
    # top-level section or end of file) for ```json blocks.
    # We search within a reasonable window (next 5000 chars) to stay local.
    window = API_CONTENT[endpoint_pos: endpoint_pos + 5000]

    json_block_count = window.count("```json")
    assert json_block_count >= 2, (
        f"docs/API.md does not have at least one JSON request example AND "
        f"one JSON response example near endpoint {endpoint!r} "
        f"(found {json_block_count} ```json block(s) in the surrounding section)"
    )
