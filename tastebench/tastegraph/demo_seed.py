"""Shared seed logic for the 10-minute OSS demo.

`seed_demo` takes a *client-like* object (duck-typed on ``create_entity`` / ``link`` /
``rerank`` — e.g. :class:`TasteGraphClient` or a TestClient shim) so the CLI and the tests
drive the exact same path. It is idempotent: a duplicate ``create_entity`` surfaces as an
``urllib.error.HTTPError`` with code 400 (``Entity '...' already exists.``) which is swallowed,
and links are safe to re-apply.
"""

from __future__ import annotations

import urllib.error

# (id, type, content) — mirrors docs/agent-demo.md step 2.
DEMO_CONTENT = [
    ("c_warm", "content", "warm specific note — concrete, no hype"),
    ("c_hype", "content", "AMAZING platform!!! 🚀🚀 unlock growth now"),
]
# (target_id, action)
DEMO_LINKS = [
    ("c_warm", "like"),
    ("c_hype", "dismiss"),
]


def _create(client, entity_id: str, type: str, content: str | None, created: list, existing: list) -> None:
    """Create an entity, treating a 400 'already exists' as success (idempotent)."""
    try:
        client.create_entity(id=entity_id, type=type, content=content)
        created.append(entity_id)
    except urllib.error.HTTPError as exc:  # duplicate create -> HTTP 400 from _guard
        if exc.code == 400:
            existing.append(entity_id)
        else:
            raise


def seed_demo(client, subject_id: str = "u_demo") -> dict:
    """Seed the canonical demo graph and return a summary.

    Creates ``subject_id`` (user) plus the demo content, links a like/dismiss, and reranks the
    two content items. On a healthy engine ``c_warm`` ranks above ``c_hype``.
    """
    created: list[str] = []
    existing: list[str] = []

    _create(client, subject_id, "user", None, created, existing)
    for cid, ctype, content in DEMO_CONTENT:
        _create(client, cid, ctype, content, created, existing)

    for target_id, action in DEMO_LINKS:
        client.link(subject_id, target_id, action=action)

    ranked = client.rerank(subject_id, [cid for cid, _, _ in DEMO_CONTENT])
    return {"subject_id": subject_id, "created": created, "existing": existing, "rerank": ranked}
