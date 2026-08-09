from tastebench import load_jsonl
from tastebench.collection.annotate import annotate_example, append_example, run_wizard
from tastebench.collection.sources import CSVSource, is_unlabeled
from tastebench.datasets.validation import validate_dataset


def _write_csv(path):
    path.write_text(
        "id,task,uri_a,uri_b,type\n"
        "r1,Pick the cleaner design,Design A text,Design B text,text\n"
        "r2,Pick the hero,a.png,b.png,image\n",
        encoding="utf-8",
    )


def test_csv_source_produces_valid_stubs(tmp_path):
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path)
    stubs = CSVSource(str(csv_path), criteria=["restraint"]).examples()
    assert len(stubs) == 2
    validate_dataset(stubs)
    assert all(is_unlabeled(s) for s in stubs)
    assert stubs[0].candidates[0].type == "text"
    assert stubs[1].candidates[0].type == "image"


def test_annotate_replaces_sentinel(tmp_path):
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path)
    stub = CSVSource(str(csv_path)).examples()[0]
    labeled = annotate_example(stub, expert_id="designer_1", choice="B", rationale="cleaner")
    assert not is_unlabeled(labeled)
    assert labeled.preference == "B"
    assert len(labeled.judgments) == 1


def test_append_and_wizard(tmp_path):
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path)
    stubs = CSVSource(str(csv_path)).examples()
    out = tmp_path / "out.jsonl"

    answers = iter(["A", "looks better", "", ""])  # label first, skip second
    saved = run_wizard(
        stubs,
        str(out),
        expert_id="designer_1",
        input_fn=lambda _prompt: next(answers),
        print_fn=lambda _msg: None,
    )
    assert saved == 1
    reloaded = load_jsonl(out)
    assert len(reloaded) == 1
    assert reloaded[0].preference == "A"
