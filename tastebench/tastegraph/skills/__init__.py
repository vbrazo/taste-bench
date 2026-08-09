"""Packaged TasteGraph agent skills (OpenAI-style function tools)."""

from __future__ import annotations

import json
from pathlib import Path

_TOOLS_PATH = Path(__file__).with_name("tools.json")


def load_tools() -> list[dict]:
    """Return the list of tool definitions from tools.json."""
    data = json.loads(_TOOLS_PATH.read_text(encoding="utf-8"))
    return list(data.get("tools") or [])


def list_tools() -> list[str]:
    """Return tool function names in declaration order."""
    names = []
    for t in load_tools():
        fn = t.get("function") or {}
        name = fn.get("name")
        if name:
            names.append(name)
    return names


def skills_payload() -> dict:
    """Wire payload for GET /v1/skills."""
    return {"tools": load_tools(), "names": list_tools()}
