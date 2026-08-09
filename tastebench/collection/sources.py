"""Ingest user-provided artifacts into unlabeled examples for annotation.

TasteBench does **not** crawl third-party sites (spec §5: "no automated scraping of
design datasets"; §24: expert-first data). Sources here consume data the user already
has the right to use — a CSV of artifact URIs, a list of local files — and emit
schema-valid :class:`PreferenceExample` *stubs* (candidates only, no judgments) ready for
:mod:`tastebench.collection.annotate`.

Respecting each source's Terms of Service and copyright is the caller's responsibility.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Optional, Protocol

from ..datasets.schema import Candidate, ExpertJudgment, PreferenceExample


class Source(Protocol):
    def examples(self) -> list[PreferenceExample]: ...


def _stub(id: str, task: str, a: Candidate, b: Candidate, criteria: Optional[list[str]]) -> PreferenceExample:
    # An unlabeled stub still needs >=1 judgment to satisfy the schema; use a sentinel
    # "unlabeled" judgment that the annotator replaces. It is filtered by is_unlabeled().
    return PreferenceExample(
        id=id,
        task=task,
        criteria=criteria or [],
        candidates=[a, b],
        judgments=[ExpertJudgment(expert_id="__unlabeled__", choice=a.id)],
    )


def is_unlabeled(example: PreferenceExample) -> bool:
    return all(j.expert_id == "__unlabeled__" for j in example.judgments)


class CSVSource:
    """Reads rows of ``id, task, uri_a, uri_b[, type]`` into unlabeled pair stubs.

    ``type`` (``text`` or ``image``, default ``image``) sets both candidates' type.
    Text-typed rows treat the ``uri_*`` columns as inline content.
    """

    def __init__(self, path: str, criteria: Optional[list[str]] = None):
        self.path = Path(path)
        self.criteria = criteria

    def examples(self) -> list[PreferenceExample]:
        out: list[PreferenceExample] = []
        with open(self.path, newline="", encoding="utf-8") as fh:
            for i, row in enumerate(csv.DictReader(fh)):
                ctype = (row.get("type") or "image").strip()
                ex_id = row.get("id") or f"row_{i:05d}"
                task = row.get("task", "").strip()
                if ctype == "text":
                    a = Candidate(id="A", type="text", content=row["uri_a"])
                    b = Candidate(id="B", type="text", content=row["uri_b"])
                else:
                    a = Candidate(id="A", type="image", uri=row["uri_a"])
                    b = Candidate(id="B", type="image", uri=row["uri_b"])
                out.append(_stub(ex_id, task, a, b, self.criteria))
        return out
