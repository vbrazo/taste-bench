from tastebench.cli import build_judge, main
from tastebench.judges.mock import MockJudge


def test_build_judge_mock():
    j = build_judge("mock")
    assert isinstance(j, MockJudge)
    assert j.strategy == "longer"
    assert build_judge("mock:first").strategy == "first"


def test_evaluate_command(sample_path, tmp_path, capsys):
    rc = main(["evaluate", "--dataset", str(sample_path), "--judge", "mock", "--results", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "TasteBench Results" in out
    assert list(tmp_path.glob("*.json"))


def test_compare_command(sample_path, capsys):
    rc = main(["compare", "--dataset", str(sample_path), "--judges", "mock", "mock:first"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Comparison" in out


def test_report_and_disagreements(sample_path, tmp_path, capsys):
    main(["evaluate", "--dataset", str(sample_path), "--judge", "mock", "--results", str(tmp_path)])
    capsys.readouterr()  # clear
    assert main(["report", "--results", str(tmp_path)]) == 0
    assert "accuracy" in capsys.readouterr().out
    assert main(["disagreements", "--results", str(tmp_path)]) == 0
    assert "disagreements" in capsys.readouterr().out
