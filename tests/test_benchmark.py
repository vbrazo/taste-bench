from tastebench import Benchmark, HumanJudge, MockJudge
from tastebench.evaluation.disagreement import analyze_disagreements


def test_full_pipeline_mock(sample_path):
    bench = Benchmark.from_jsonl(sample_path)
    results = bench.evaluate(MockJudge(strategy="longer"))
    assert results.n_examples == 10
    assert 0.0 <= results.accuracy <= 1.0
    assert 0.0 <= results.human_ceiling <= 1.0
    # sample is designed so experts strongly agree -> high ceiling
    assert results.human_ceiling > 0.8
    assert results.criterion_scores  # populated
    text = results.report()
    assert "TasteBench Results" in text


def test_mock_first_strategy_is_deterministic(sample_path):
    bench = Benchmark.from_jsonl(sample_path)
    r1 = bench.evaluate(MockJudge(strategy="first"))
    r2 = bench.evaluate(MockJudge(strategy="first"))
    assert [p.choice for p in r1.predictions] == [p.choice for p in r2.predictions]


def test_compare(sample_path):
    bench = Benchmark.from_jsonl(sample_path)
    res = bench.compare([MockJudge(strategy="longer"), MockJudge(strategy="first", name="mock_first")])
    assert len(res) == 2
    assert {r.judge_name for r in res} == {"mock", "mock_first"}


def test_save_and_load(tmp_path, sample_path):
    bench = Benchmark.from_jsonl(sample_path)
    results = bench.evaluate(MockJudge())
    path = results.save(tmp_path)
    assert path.exists()


def test_human_judge_ceiling_reference(sample_path):
    # A held-out human judge should score near the human ceiling on examples it labeled.
    bench = Benchmark.from_jsonl(sample_path)
    judge = HumanJudge("designer_1")
    labeled = [ex for ex in bench.examples if judge.predicts(ex)]
    assert labeled  # designer_1 appears in the sample
    preds = [judge.predict(ex) for ex in labeled]
    # every prediction is a valid candidate id
    for ex, p in zip(labeled, preds):
        assert p.choice in {c.id for c in ex.candidates}


def test_disagreement_separates_error_from_ambiguity(sample_path):
    bench = Benchmark.from_jsonl(sample_path)
    results = bench.evaluate(MockJudge(strategy="first"))
    rep = analyze_disagreements(bench.examples, results.predictions)
    assert rep.n_model_error + rep.n_ambiguous == len(rep.disagreements)
