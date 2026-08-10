"""Thin MCP server exposing TasteGraph builder tools (Phase 5).

Wraps the existing HTTP API via :class:`TasteGraphClient` — no new engine logic. Point it at a
running server with ``TASTEGRAPH_BASE_URL`` (default ``http://127.0.0.1:8000``) and optional
``TASTEGRAPH_API_KEY``, then run ``tastebench tastegraph mcp`` (stdio transport).

Requires the optional extra: ``pip install 'tastebench[mcp]'``.
"""

from __future__ import annotations

import os
from typing import Optional

from .client import TasteGraphClient


def _require_mcp():
    try:
        from mcp.server.fastmcp import FastMCP  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "The TasteGraph MCP server requires the 'mcp' extra: pip install 'tastebench[mcp]'"
        ) from exc


def build_server(base_url: Optional[str] = None, api_key: Optional[str] = None):
    """Build a FastMCP server whose tools mirror the builder tools in skills/tools.json."""
    _require_mcp()
    from mcp.server.fastmcp import FastMCP

    base_url = base_url or os.environ.get("TASTEGRAPH_BASE_URL", "http://127.0.0.1:8000")
    api_key = api_key or os.environ.get("TASTEGRAPH_API_KEY")
    client = TasteGraphClient(base_url, api_key)

    mcp = FastMCP("tastegraph")

    @mcp.tool()
    def taste_context(subject_id: str) -> dict:
        """Structured taste read (principles / avoid / confidence) for a subject."""
        return client.agent_context(subject_id)

    @mcp.tool()
    def taste_search(user_id: str, k: int = 8) -> dict:
        """Discover on-taste content for a subject."""
        return client.search(user_id=user_id, k=k)

    @mcp.tool()
    def taste_rerank(user_id: str, candidates: list[str]) -> dict:
        """Reorder candidate ids by the subject's taste."""
        return client.rerank(user_id, candidates)

    @mcp.tool()
    def taste_ask(user_id: str, question: str, k: int = 5) -> dict:
        """Taste-personalized Q&A for a subject."""
        return client.ask(user_id, question, k=k)

    @mcp.tool()
    def taste_enhance(subject_id: str, prompt: str) -> dict:
        """Rewrite a draft on-taste for a brand or voice subject."""
        return client.enhance(subject_id, prompt)

    @mcp.tool()
    def taste_judge(subject_id: str, candidates: list[str]) -> dict:
        """Score competing drafts against a subject before send."""
        return client.judge(subject_id, candidates)

    @mcp.tool()
    def taste_brand_ingest(id: str, references: list[str], type: str = "brand") -> dict:
        """Build a brand/voice subject from reference snippets."""
        return client.brand_ingest(id, [{"content": r} for r in references], type=type)

    return mcp


def main(base_url: Optional[str] = None, api_key: Optional[str] = None) -> int:  # pragma: no cover - stdio loop
    """Run the MCP server over stdio."""
    build_server(base_url, api_key).run()
    return 0
