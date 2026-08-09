"""TasteBench command-line interface (spec section 17).

    tastebench evaluate --dataset design_1k.jsonl --judge mock
    tastebench compare  --dataset design_1k.jsonl --judges mock gpt-4o
    tastebench report   --results results/
    tastebench disagreements --results results/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .benchmarks.benchmark import Benchmark
from .judges.base import Judge
from .judges.mock import MockJudge


def build_judge(spec: str) -> Judge:
    """Map a CLI judge spec to a Judge instance.

    ``mock`` (optionally ``mock:strategy``) builds a MockJudge; anything else is
    treated as a LiteLLM model string.
    """
    if spec == "mock" or spec.startswith("mock:"):
        strategy = spec.split(":", 1)[1] if ":" in spec else "longer"
        return MockJudge(strategy=strategy, name=f"mock:{strategy}")  # type: ignore[arg-type]
    from .judges.llm import LLMJudge

    return LLMJudge(model=spec)


def _cmd_evaluate(args: argparse.Namespace) -> int:
    bench = Benchmark.from_jsonl(args.dataset)
    judge = build_judge(args.judge)
    results = bench.evaluate(judge, max_workers=args.workers)
    results.report()
    if args.results:
        path = results.save(args.results)
        print(f"\nSaved results to {path}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    bench = Benchmark.from_jsonl(args.dataset)
    judges = [build_judge(s) for s in args.judges]
    all_results = bench.compare(judges, max_workers=args.workers)

    print(f"Comparison on {bench.name}  (human ceiling {all_results[0].human_ceiling * 100:.1f}%)")
    print("-" * 52)
    print(f"{'judge':<28}{'accuracy':>10}{'calib':>8}")
    for r in sorted(all_results, key=lambda x: x.accuracy, reverse=True):
        print(f"{r.judge_name:<28}{r.accuracy * 100:>9.1f}%{r.calibration.score:>8.2f}")
        if args.results:
            r.save(args.results)
    return 0


def _load_saved(directory: str) -> list[dict]:
    files = sorted(Path(directory).glob("*.json"))
    if not files:
        print(f"No result files found in {directory}", file=sys.stderr)
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def _cmd_report(args: argparse.Namespace) -> int:
    saved = _load_saved(args.results)
    if not saved:
        return 1
    for data in saved:
        print(f"\n=== {data['judge']} on {data['dataset']} ===")
        print(f"  accuracy:      {data['accuracy'] * 100:.1f}%")
        print(f"  human ceiling: {data['human_ceiling'] * 100:.1f}%")
        print(f"  calibration:   {data['calibration_score']:.2f}")
        for crit, s in data.get("criterion_scores", {}).items():
            print(f"    {crit:<18} {s['accuracy'] * 100:5.1f}%  ({s['correct']}/{s['total']})")
    return 0


def _cmd_disagreements(args: argparse.Namespace) -> int:
    saved = _load_saved(args.results)
    if not saved:
        return 1
    for data in saved:
        dis = data.get("disagreements", {})
        print(f"\n=== disagreements: {data['judge']} on {data['dataset']} ===")
        print(f"  model errors:         {dis.get('n_model_error', 0)}")
        print(f"  subjective ambiguity: {dis.get('n_ambiguous', 0)}")
        patterns = dis.get("top_patterns", [])
        if patterns:
            print("  top patterns:")
            for name, count in patterns:
                print(f"    - {str(name).replace('_', ' ')} ({count})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tastebench", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_eval = sub.add_parser("evaluate", help="Run one judge on a dataset.")
    p_eval.add_argument("--dataset", required=True)
    p_eval.add_argument("--judge", required=True, help="'mock', 'mock:<strategy>', or a LiteLLM model string.")
    p_eval.add_argument("--results", help="Directory to save results JSON.")
    p_eval.add_argument("--workers", type=int, default=None)
    p_eval.set_defaults(func=_cmd_evaluate)

    p_cmp = sub.add_parser("compare", help="Compare several judges on a dataset.")
    p_cmp.add_argument("--dataset", required=True)
    p_cmp.add_argument("--judges", required=True, nargs="+")
    p_cmp.add_argument("--results", help="Directory to save results JSON.")
    p_cmp.add_argument("--workers", type=int, default=None)
    p_cmp.set_defaults(func=_cmd_compare)

    p_rep = sub.add_parser("report", help="Re-render saved results.")
    p_rep.add_argument("--results", required=True)
    p_rep.set_defaults(func=_cmd_report)

    p_dis = sub.add_parser("disagreements", help="Show disagreement analysis from saved results.")
    p_dis.add_argument("--results", required=True)
    p_dis.set_defaults(func=_cmd_disagreements)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
