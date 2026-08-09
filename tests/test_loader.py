from tastebench import load_jsonl, write_jsonl
from tastebench.datasets.validation import dataset_summary, validate_dataset


def test_sample_loads(sample_examples):
    assert len(sample_examples) == 10
    validate_dataset(sample_examples)


def test_round_trip(tmp_path, sample_examples):
    out = tmp_path / "rt.jsonl"
    n = write_jsonl(out, sample_examples)
    assert n == len(sample_examples)
    reloaded = load_jsonl(out)
    assert [e.id for e in reloaded] == [e.id for e in sample_examples]
    assert reloaded[0].preference == sample_examples[0].preference


def test_summary(sample_examples):
    summ = dataset_summary(sample_examples)
    assert summ["examples"] == 10
    assert summ["with_multiple_experts"] == 10
    assert summ["avg_experts_per_example"] == 3.0
