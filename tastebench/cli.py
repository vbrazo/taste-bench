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
    results = bench.evaluate(judge, max_workers=args.workers, semantic=args.semantic)
    results.report()
    clusters = results.disagreement.semantic_clusters
    if clusters:
        print("\nSemantic disagreement clusters:")
        for c in clusters:
            print(f"  - [{c.size}] {c.label}: {c.representative[:80]}")
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


def _cmd_export(args: argparse.Namespace) -> int:
    from .datasets.hf import push_to_hub, to_hf_dataset
    from .datasets.loader import load_jsonl

    examples = load_jsonl(args.dataset)
    if args.hf_repo:
        push_to_hub(examples, args.hf_repo)
        print(f"Pushed {len(examples)} examples to {args.hf_repo}")
    else:
        ds = to_hf_dataset(examples)
        ds.save_to_disk(args.out)
        print(f"Saved HF dataset ({len(examples)} examples) to {args.out}")
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    from .datasets.hf import load_from_hub
    from .datasets.loader import write_jsonl

    examples = load_from_hub(args.hf_repo, split=args.split)
    n = write_jsonl(args.out, examples)
    print(f"Wrote {n} examples to {args.out}")
    return 0


def _cmd_train(args: argparse.Namespace) -> int:
    from .datasets.loader import load_jsonl

    examples = load_jsonl(args.dataset)
    if args.kind == "classifier":
        from .training.classifier import TrainableJudge

        model = TrainableJudge(base_model=args.base_model).fit(examples, epochs=args.epochs)
    else:
        from .training.reward import RewardModel

        model = RewardModel(base_model=args.base_model, lora=args.lora).fit(examples, epochs=args.epochs)
    model.save(args.out)
    print(f"Trained {args.kind} on {len(examples)} examples -> {args.out}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:  # pragma: no cover - runs a server
    import uvicorn

    from .web.app import create_app

    app = create_app(results_dir=args.results, dataset_path=args.dataset)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def _cmd_annotate(args: argparse.Namespace) -> int:  # pragma: no cover - interactive
    from .collection.annotate import run_wizard
    from .collection.sources import CSVSource

    stubs = CSVSource(args.csv).examples()
    run_wizard(stubs, args.out, expert_id=args.expert)
    return 0


def _build_tastegraph_engine(assets_path: str, signals_path: Optional[str], analyzer_spec: str, backend: str = "memory"):
    """Build and populate a TasteGraphEngine from sample files."""
    from .tastegraph import TasteGraphEngine, load_assets
    from .tastegraph.graph.backends import make_backend
    from .tastegraph.signals.capture import load_signals

    if analyzer_spec == "mock":
        analyzer = None
    else:
        from .tastegraph.assets.analyzer import VLMAssetAnalyzer

        analyzer = VLMAssetAnalyzer(model=analyzer_spec)
    engine = TasteGraphEngine(analyzer=analyzer, backend=make_backend(backend))
    engine.ingest(load_assets(assets_path))
    if signals_path:
        for sig in load_signals(signals_path):
            engine.track(sig)
    return engine


def _cmd_tg_ingest(args: argparse.Namespace) -> int:
    engine = _build_tastegraph_engine(args.assets, None, args.analyzer, getattr(args, "backend", "memory"))
    print(f"Ingested {len(engine.index)} assets into the taste graph.")
    for fp in list(engine.store)[:5]:
        print(f"  {fp.asset_id}: style={fp.aesthetic.style} mood={fp.emotional.mood} score={fp.advanced.score}")
    return 0


def _cmd_tg_rerank(args: argparse.Namespace) -> int:
    engine = _build_tastegraph_engine(args.assets, args.signals, args.analyzer)
    candidates = args.candidates.split(",")
    ranked = engine.rerank(args.user, candidates, cold_start_seed=args.seed)
    print(f"Reranked for {args.user}:")
    for aid, score in ranked:
        print(f"  {score:+.4f}  {aid}")
    return 0


def _cmd_tg_agent_context(args: argparse.Namespace) -> int:
    import json

    engine = _build_tastegraph_engine(args.assets, args.signals, args.analyzer)
    print(json.dumps(engine.agent_context(args.user), indent=2))
    return 0


def _cmd_tg_train(args: argparse.Namespace) -> int:
    from .training.from_signals import signals_to_examples

    engine = _build_tastegraph_engine(args.assets, args.signals, args.analyzer)
    examples = signals_to_examples(engine)
    if not examples:
        print("No training pairs could be derived from the signals.")
        return 1
    if args.kind == "reward":
        from .training.reward import RewardModel

        model = RewardModel(base_model=args.base_model).fit(examples, epochs=args.epochs)
    else:
        from .training.classifier import TrainableJudge

        model = TrainableJudge(base_model=args.base_model).fit(examples, epochs=args.epochs)
    model.save(args.out)
    print(f"Trained {args.kind} on {len(examples)} taste pairs -> {args.out}")
    return 0


def _cmd_tg_ask(args: argparse.Namespace) -> int:
    import json

    from .tastegraph.api.ask import ask

    engine = _build_tastegraph_engine(args.assets, args.signals, args.analyzer)
    print(json.dumps(ask(engine, args.user, args.question), indent=2))
    return 0


def _cmd_tg_export_web(args: argparse.Namespace) -> int:
    from .tastegraph.export_web import export_bundle

    analyzer = None
    if args.analyzer != "mock":
        from .tastegraph.assets.analyzer import VLMAssetAnalyzer

        analyzer = VLMAssetAnalyzer(model=args.analyzer)
    n = export_bundle(args.assets, args.out, analyzer=analyzer)
    print(f"Exported {n} assets with vectors -> {args.out}")
    return 0


def _cmd_tg_serve(args: argparse.Namespace) -> int:  # pragma: no cover - runs a server
    import uvicorn

    from .tastegraph.api.app import create_app

    from .tastegraph.api.ratelimit import RateLimiter

    limiter = RateLimiter(rate_per_min=args.rate_per_min or 0, max_per_day=args.quota_per_day or 0)
    engine = _build_tastegraph_engine(args.assets, args.signals, args.analyzer, getattr(args, "backend", "memory"))
    if args.api_keys:
        from .tastegraph.api.tenancy import ApiKeyRegistry, TenantStore

        store = TenantStore(ApiKeyRegistry.from_file(args.api_keys), engine_factory=lambda _t: engine)
        app = create_app(tenant_store=store, limiter=limiter)
    else:
        app = create_app(engine, limiter=limiter)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def _cmd_tg_seed_demo(args: argparse.Namespace) -> int:
    from .tastegraph.client import TasteGraphClient
    from .tastegraph.demo_seed import seed_demo

    client = TasteGraphClient(args.base_url, args.api_key)
    result = seed_demo(client, args.subject_id)
    subject = result["subject_id"]

    if result["created"]:
        print(f"Created: {', '.join(result['created'])}")
    if result["existing"]:
        print(f"Already present: {', '.join(result['existing'])}")
    order = " > ".join(r["id"] for r in result["rerank"].get("results", []))
    print(f"Seeded demo taste graph for '{subject}' at {client.base_url}.")
    print(f"Rerank order: {order}")
    print()
    print("Next steps:")
    print(f"  curl -s {client.base_url}/agent-context/{subject}")
    print(f"  curl -sX POST {client.base_url}/v1/rerank -H 'Content-Type: application/json' \\")
    print(f"    -d '{{\"user_id\":\"{subject}\",\"candidates\":[\"c_warm\",\"c_hype\"]}}'")
    print(f"  curl -sX POST {client.base_url}/v1/judge -H 'Content-Type: application/json' \\")
    print(f"    -d '{{\"subject_id\":\"{subject}\",\"candidates\":[\"c_warm\",\"c_hype\"]}}'")
    print("  Wire an agent with the skill: skills/tastegraph/SKILL.md")
    return 0


def _cmd_tg_mcp(args: argparse.Namespace) -> int:  # pragma: no cover - runs an stdio server
    from .tastegraph.mcp_server import main as mcp_main

    return mcp_main(args.base_url, args.api_key)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tastebench", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_eval = sub.add_parser("evaluate", help="Run one judge on a dataset.")
    p_eval.add_argument("--dataset", required=True)
    p_eval.add_argument("--judge", required=True, help="'mock', 'mock:<strategy>', or a LiteLLM model string.")
    p_eval.add_argument("--results", help="Directory to save results JSON.")
    p_eval.add_argument("--workers", type=int, default=None)
    p_eval.add_argument(
        "--semantic", action="store_true", help="Cluster disagreement rationales (needs the 'embeddings' extra)."
    )
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

    p_exp = sub.add_parser("export", help="Export a dataset to Hugging Face (needs 'hf' extra).")
    p_exp.add_argument("--dataset", required=True)
    p_exp.add_argument("--hf-repo", dest="hf_repo", help="Push to this hub repo id.")
    p_exp.add_argument("--out", help="Or save an HF dataset to this local dir.")
    p_exp.set_defaults(func=_cmd_export)

    p_imp = sub.add_parser("import", help="Import a dataset from Hugging Face (needs 'hf' extra).")
    p_imp.add_argument("--hf-repo", dest="hf_repo", required=True)
    p_imp.add_argument("--split", default="train")
    p_imp.add_argument("--out", required=True, help="Destination JSONL path.")
    p_imp.set_defaults(func=_cmd_import)

    p_tr = sub.add_parser("train", help="Train a judge or reward model (needs 'train' extra).")
    p_tr.add_argument("--dataset", required=True)
    p_tr.add_argument("--kind", choices=["classifier", "reward"], default="classifier")
    p_tr.add_argument("--out", required=True, help="Output model directory.")
    p_tr.add_argument("--base-model", dest="base_model", default="distilbert-base-uncased")
    p_tr.add_argument("--epochs", type=int, default=3)
    p_tr.add_argument("--lora", action="store_true")
    p_tr.set_defaults(func=_cmd_train)

    p_srv = sub.add_parser("serve", help="Serve the read-only web UI (needs 'web' extra).")
    p_srv.add_argument("--results", default="results")
    p_srv.add_argument("--dataset", default=None)
    p_srv.add_argument("--host", default="127.0.0.1")
    p_srv.add_argument("--port", type=int, default=8000)
    p_srv.set_defaults(func=_cmd_serve)

    p_ann = sub.add_parser("annotate", help="Manually label candidate pairs from a CSV into JSONL.")
    p_ann.add_argument("--csv", required=True, help="CSV of id,task,uri_a,uri_b[,type].")
    p_ann.add_argument("--out", required=True, help="Destination JSONL path.")
    p_ann.add_argument("--expert", required=True, help="Expert id for the annotations.")
    p_ann.set_defaults(func=_cmd_annotate)

    # ---- TasteGraph command group -----------------------------------------
    p_tg = sub.add_parser("tastegraph", help="TasteGraph taste-infrastructure commands.")
    tg_sub = p_tg.add_subparsers(dest="tg_command", required=True)

    def _tg_common(p):
        p.add_argument("--assets", required=True, help="Assets JSONL to ingest.")
        p.add_argument("--analyzer", default="mock", help="'mock' or a LiteLLM model string.")
        p.add_argument("--backend", default="memory", choices=["memory", "qdrant"], help="Vector backend.")

    tg_ing = tg_sub.add_parser("ingest", help="Fingerprint assets into the taste graph.")
    _tg_common(tg_ing)
    tg_ing.set_defaults(func=_cmd_tg_ingest)

    tg_rr = tg_sub.add_parser("rerank", help="Rerank candidate assets by a user's taste.")
    _tg_common(tg_rr)
    tg_rr.add_argument("--signals", help="Signals JSONL.")
    tg_rr.add_argument("--user", required=True)
    tg_rr.add_argument("--candidates", required=True, help="Comma-separated asset ids.")
    tg_rr.add_argument("--seed", help="Cold-start seed asset id.")
    tg_rr.set_defaults(func=_cmd_tg_rerank)

    tg_ac = tg_sub.add_parser("agent-context", help="Print the structured taste read for a user.")
    _tg_common(tg_ac)
    tg_ac.add_argument("--signals", help="Signals JSONL.")
    tg_ac.add_argument("--user", required=True)
    tg_ac.set_defaults(func=_cmd_tg_agent_context)

    tg_srv = tg_sub.add_parser("serve", help="Serve the TasteGraph API (needs 'web' extra).")
    _tg_common(tg_srv)
    tg_srv.add_argument("--signals", help="Signals JSONL.")
    tg_srv.add_argument("--api-keys", dest="api_keys", help="JSON file mapping api-key -> tenant id.")
    tg_srv.add_argument("--host", default="127.0.0.1")
    tg_srv.add_argument("--port", type=int, default=8000)
    tg_srv.add_argument("--rate-per-min", dest="rate_per_min", type=float, default=0, help="Per-key request rate (0 = unlimited).")
    tg_srv.add_argument("--quota-per-day", dest="quota_per_day", type=int, default=0, help="Per-key daily quota (0 = unlimited).")
    tg_srv.set_defaults(func=_cmd_tg_serve)

    tg_ask = tg_sub.add_parser("ask", help="Taste-personalized Q&A for a user (local, in-process).")
    _tg_common(tg_ask)
    tg_ask.add_argument("--signals", required=True, help="Signals JSONL.")
    tg_ask.add_argument("--user", required=True)
    tg_ask.add_argument("--question", required=True)
    tg_ask.set_defaults(func=_cmd_tg_ask)

    tg_ew = tg_sub.add_parser("export-web", help="Export a static asset+vector bundle for the web UI.")
    _tg_common(tg_ew)
    tg_ew.add_argument("--out", required=True, help="Destination JSON path.")
    tg_ew.set_defaults(func=_cmd_tg_export_web)

    tg_tr = tg_sub.add_parser("train", help="Train a taste model from signals (needs 'train' extra).")
    _tg_common(tg_tr)
    tg_tr.add_argument("--signals", required=True, help="Signals JSONL.")
    tg_tr.add_argument("--kind", choices=["reward", "classifier"], default="reward")
    tg_tr.add_argument("--out", required=True, help="Output model directory.")
    tg_tr.add_argument("--base-model", dest="base_model", default="distilbert-base-uncased")
    tg_tr.add_argument("--epochs", type=int, default=3)
    tg_tr.set_defaults(func=_cmd_tg_train)

    tg_seed = tg_sub.add_parser(
        "seed-demo", help="Seed the 10-minute demo taste graph on a running server (idempotent)."
    )
    tg_seed.add_argument("--base-url", dest="base_url", default="http://127.0.0.1:8000", help="TasteGraph server base URL.")
    tg_seed.add_argument("--api-key", dest="api_key", default=None, help="Optional X-API-Key for tenant auth.")
    tg_seed.add_argument("--subject-id", dest="subject_id", default="u_demo", help="Subject id to personalize for.")
    tg_seed.set_defaults(func=_cmd_tg_seed_demo)

    tg_mcp = tg_sub.add_parser("mcp", help="Run an MCP server (stdio) over a running TasteGraph (needs 'mcp' extra).")
    tg_mcp.add_argument("--base-url", dest="base_url", default=None, help="Server base URL (default env TASTEGRAPH_BASE_URL or http://127.0.0.1:8000).")
    tg_mcp.add_argument("--api-key", dest="api_key", default=None, help="Optional X-API-Key (default env TASTEGRAPH_API_KEY).")
    tg_mcp.set_defaults(func=_cmd_tg_mcp)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
