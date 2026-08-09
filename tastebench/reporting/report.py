"""Human-readable report rendering (spec section 18)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid a circular import at runtime
    from ..benchmarks.benchmark import Results


def _bar(label: str, value: float, width: int = 20) -> str:
    filled = int(round(value * width))
    return f"  {label:<16} {value * 100:5.1f}%  {'█' * filled}{'░' * (width - filled)}"


def format_report(results: "Results") -> str:
    lines: list[str] = []
    lines.append("TasteBench Results")
    lines.append("=" * 40)
    lines.append(f"Dataset:       {results.dataset_name}")
    lines.append(f"Judge:         {results.judge_name}")
    lines.append(f"Examples:      {results.n_examples}")
    lines.append("")
    lines.append(f"Accuracy:      {results.accuracy * 100:5.1f}%")
    lines.append(f"Human ceiling: {results.human_ceiling * 100:5.1f}%")
    lines.append(f"Calibration:   {results.calibration.score:.2f}  (ECE {results.calibration.ece:.3f})")

    scores = results.criterion_scores
    if scores:
        ranked = sorted(scores.values(), key=lambda s: s.accuracy, reverse=True)
        lines.append("")
        lines.append("By criterion:")
        for s in ranked:
            lines.append(_bar(s.criterion, s.accuracy) + f"  ({s.correct}/{s.total})")

        if len(ranked) >= 2:
            lines.append("")
            lines.append(f"Strongest: {ranked[0].criterion} ({ranked[0].accuracy * 100:.0f}%)")
            lines.append(f"Weakest:   {ranked[-1].criterion} ({ranked[-1].accuracy * 100:.0f}%)")

    d = results.disagreement
    lines.append("")
    lines.append("Disagreements:")
    lines.append(f"  model errors:        {d.n_model_error}")
    lines.append(f"  subjective ambiguity:{d.n_ambiguous:>4}")
    if d.top_patterns:
        lines.append("  top error patterns:")
        for name, count in d.top_patterns[:5]:
            lines.append(f"    - {name.replace('_', ' ')} ({count})")

    return "\n".join(lines)


def format_disagreements(results: "Results", limit: int = 20) -> str:
    """Detailed per-example disagreement listing (spec section 12)."""
    d = results.disagreement
    lines: list[str] = []
    lines.append(f"Disagreement analysis — {results.judge_name} on {results.dataset_name}")
    lines.append("=" * 50)
    lines.append(f"model errors: {d.n_model_error}   subjective ambiguity: {d.n_ambiguous}")
    if d.top_patterns:
        lines.append("")
        lines.append("Top disagreement patterns (on model errors):")
        for i, (name, count) in enumerate(d.top_patterns, start=1):
            lines.append(f"  {i}. {name.replace('_', ' ')} ({count})")

    lines.append("")
    lines.append("Examples:")
    for dg in d.disagreements[:limit]:
        kind = "AMBIGUOUS" if dg.is_ambiguous else "MODEL ERROR"
        lines.append("")
        lines.append(f"[{kind}] {dg.example_id} — human agreement {dg.human_agreement * 100:.0f}%")
        lines.append(f"  task:      {dg.task}")
        lines.append(f"  model:     {dg.model_choice}   consensus: {dg.consensus_choice}")
        if dg.model_rationale:
            lines.append(f"  rationale: {dg.model_rationale[:160]}")
        if dg.tags:
            lines.append(f"  tags:      {', '.join(dg.tags)}")

    if len(d.disagreements) > limit:
        lines.append("")
        lines.append(f"... and {len(d.disagreements) - limit} more.")
    return "\n".join(lines)
