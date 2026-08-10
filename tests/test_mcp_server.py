"""Phase 5: thin MCP wrapper over the TasteGraph HTTP client."""

import importlib.util

import pytest

from tastebench.cli import build_parser

HAS_MCP = importlib.util.find_spec("mcp") is not None


def test_cli_registers_mcp_command():
    args = build_parser().parse_args(["tastegraph", "mcp", "--base-url", "http://h:9", "--api-key", "k"])
    assert args.func.__name__ == "_cmd_tg_mcp"
    assert args.base_url == "http://h:9"
    assert args.api_key == "k"


@pytest.mark.skipif(HAS_MCP, reason="mcp extra installed; ImportError path not exercised")
def test_build_server_without_extra_raises_helpful_error():
    from tastebench.tastegraph.mcp_server import build_server

    with pytest.raises(ImportError, match="tastebench\\[mcp\\]"):
        build_server("http://127.0.0.1:8000")


@pytest.mark.skipif(not HAS_MCP, reason="requires the 'mcp' extra")
def test_build_server_exposes_builder_tools():
    from tastebench.tastegraph.mcp_server import build_server

    server = build_server("http://127.0.0.1:8000")
    import asyncio

    names = {t.name for t in asyncio.run(server.list_tools())}
    assert {"taste_context", "taste_rerank", "taste_judge"} <= names
