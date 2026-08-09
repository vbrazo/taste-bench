"""Manual expert annotation (the sanctioned way to grow labeled data).

Presents two candidates and records an :class:`ExpertJudgment`, appending the resulting
:class:`PreferenceExample` to a JSONL file via the existing writer. Designed to be driven
interactively from the CLI or programmatically in tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from ..datasets.loader import iter_jsonl, write_jsonl
from ..datasets.schema import ExpertJudgment, PreferenceExample


def annotate_example(
    example: PreferenceExample,
    *,
    expert_id: str,
    choice: str,
    confidence: Optional[float] = None,
    rationale: Optional[str] = None,
    domain: Optional[str] = None,
) -> PreferenceExample:
    """Return a copy of ``example`` with the sentinel judgment replaced by a real one.

    If the example was already labeled, the new judgment is appended (multi-expert).
    """
    from .sources import is_unlabeled

    judgment = ExpertJudgment(
        expert_id=expert_id, domain=domain, choice=choice, confidence=confidence, rationale=rationale
    )
    judgments = [] if is_unlabeled(example) else list(example.judgments)
    judgments.append(judgment)
    return example.model_copy(update={"judgments": judgments})


def append_example(path: str, example: PreferenceExample) -> None:
    """Append one example to a JSONL file, creating it if absent."""
    existing = list(iter_jsonl(path)) if Path(path).exists() else []
    existing.append(example)
    write_jsonl(path, existing)


def run_wizard(
    stubs: list[PreferenceExample],
    out_path: str,
    *,
    expert_id: str,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
) -> int:
    """Interactively label each stub and append it to ``out_path``. Returns count saved.

    ``input_fn`` / ``print_fn`` are injectable for testing. Entering an empty choice
    skips the example.
    """
    saved = 0
    for ex in stubs:
        print_fn(f"\nTask: {ex.task}")
        for c in ex.candidates:
            print_fn(f"  [{c.id}] {c.render()[:200]}")
        choice = input_fn(f"Preferred candidate {[c.id for c in ex.candidates]} (blank to skip): ").strip()
        if not choice:
            continue
        rationale = input_fn("Rationale (optional): ").strip() or None
        labeled = annotate_example(ex, expert_id=expert_id, choice=choice, rationale=rationale)
        append_example(out_path, labeled)
        saved += 1
    print_fn(f"\nSaved {saved} annotations to {out_path}")
    return saved
