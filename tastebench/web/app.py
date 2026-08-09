"""Read-only web viewer for TasteBench (optional; requires ``tastebench[web]``).

Renders a leaderboard from a directory of saved ``Results`` JSON (the same schema
produced by ``Results.to_dict()`` / ``Results.save``), plus a dataset browser and a
disagreement viewer. No auth, no writes, no build step — server-rendered HTML only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def _require_fastapi():
    try:
        import fastapi  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "The web UI requires the 'web' extra: pip install 'tastebench[web]'"
        ) from exc


def _html(title: str, body: str) -> str:
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:2rem;max-width:60rem}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:.5rem;text-align:left}"
        "th{background:#f5f5f5}a{color:#06c}.bar{background:#06c;height:.8rem;display:inline-block}"
        "</style></head><body>"
        f"<h1>{title}</h1>{body}</body></html>"
    )


def _load_results(results_dir: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(results_dir.glob("*.json"))]


def create_app(results_dir: str = "results", dataset_path: Optional[str] = None):
    _require_fastapi()
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    from ..datasets.loader import load_jsonl

    app = FastAPI(title="TasteBench")
    rdir = Path(results_dir)

    @app.get("/", response_class=HTMLResponse)
    def leaderboard():
        rows = sorted(_load_results(rdir), key=lambda d: d.get("accuracy", 0), reverse=True)
        if not rows:
            return _html("TasteBench", f"<p>No results found in <code>{rdir}</code>.</p>")
        ceiling = rows[0].get("human_ceiling", 0)
        trs = "".join(
            f"<tr><td><a href='/disagreements/{d['judge'].replace('/', '_').replace(':', '_')}'>{d['judge']}</a></td>"
            f"<td>{d['accuracy']:.1%}</td><td>{d.get('calibration_score', 0):.2f}</td>"
            f"<td>{d.get('n_examples', 0)}</td></tr>"
            for d in rows
        )
        body = (
            f"<p>Human ceiling: <b>{ceiling:.1%}</b></p>"
            "<table><tr><th>Judge</th><th>Accuracy</th><th>Calibration</th><th>Examples</th></tr>"
            f"{trs}</table>"
        )
        if dataset_path:
            body += "<p><a href='/dataset'>Browse dataset →</a></p>"
        return _html("TasteBench Leaderboard", body)

    @app.get("/disagreements/{judge}", response_class=HTMLResponse)
    def disagreements(judge: str):
        for d in _load_results(rdir):
            safe = d["judge"].replace("/", "_").replace(":", "_")
            if safe == judge:
                dis = d.get("disagreements", {})
                patterns = "".join(
                    f"<li>{str(n).replace('_', ' ')} ({c})</li>" for n, c in dis.get("top_patterns", [])
                )
                body = (
                    f"<p>model errors: <b>{dis.get('n_model_error', 0)}</b> &nbsp; "
                    f"subjective ambiguity: <b>{dis.get('n_ambiguous', 0)}</b></p>"
                    f"<ul>{patterns}</ul><p><a href='/'>← back</a></p>"
                )
                return _html(f"Disagreements — {d['judge']}", body)
        return _html("Not found", "<p>No such judge.</p>")

    @app.get("/dataset", response_class=HTMLResponse)
    def dataset():
        if not dataset_path:
            return _html("Dataset", "<p>No dataset configured.</p>")
        examples = load_jsonl(dataset_path)
        trs = "".join(
            f"<tr><td>{ex.id}</td><td>{ex.task}</td><td>{ex.preference}</td>"
            f"<td>{ex.agreement:.0%}</td><td>{len(ex.judgments)}</td></tr>"
            for ex in examples
        )
        body = (
            "<table><tr><th>ID</th><th>Task</th><th>Consensus</th><th>Agreement</th><th>Experts</th></tr>"
            f"{trs}</table><p><a href='/'>← back</a></p>"
        )
        return _html("Dataset", body)

    return app
