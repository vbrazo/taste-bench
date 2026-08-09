"""Thin Python client for the TasteGraph /v1 API (Part 4).

The open-source consumer surface, mirroring the create → content → link → query loop. Uses
the stdlib (urllib) so it has no extra dependency; pass an API key for tenant auth.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Optional


class TasteGraphClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("X-API-Key", self.api_key)
        with urllib.request.urlopen(req) as resp:  # noqa: S310 - user-supplied base_url
            return json.loads(resp.read().decode("utf-8"))

    # ---- entities ----------------------------------------------------------

    def create_entity(self, id: str, type: str = "content", content: Optional[str] = None, metadata: Optional[dict] = None) -> dict:
        return self._request("POST", "/v1/entity", {"id": id, "type": type, "content": content, "metadata": metadata or {}})

    def register_type(self, name: str, kind: str) -> dict:
        return self._request("POST", "/v1/entity/type", {"name": name, "kind": kind})

    def get_entity(self, id: str) -> dict:
        return self._request("GET", f"/v1/entity/{id}")

    def delete_entity(self, id: str) -> dict:
        return self._request("DELETE", f"/v1/entity/{id}")

    def link(self, user_id: str, target_id: str, action: str = "like", weight: Optional[float] = None) -> dict:
        return self._request("POST", f"/v1/entity/{user_id}/link", {"target_id": target_id, "action": action, "weight": weight})

    # ---- queries -----------------------------------------------------------

    def search(self, user_id: Optional[str] = None, seed_id: Optional[str] = None, k: int = 10) -> dict:
        return self._request("POST", "/v1/search", {"user_id": user_id, "seed_id": seed_id, "k": k})

    def rerank(self, user_id: str, candidates: list[str]) -> dict:
        return self._request("POST", "/v1/rerank", {"user_id": user_id, "candidates": candidates})

    def ask(self, user_id: str, question: str, k: int = 5) -> dict:
        return self._request("POST", "/v1/ask", {"user_id": user_id, "question": question, "k": k})

    def explain(self, user_id: str) -> dict:
        return self._request("POST", "/v1/explain", {"user_id": user_id, "candidates": []})

    def clusters(self) -> dict:
        return self._request("GET", "/v1/clusters")
