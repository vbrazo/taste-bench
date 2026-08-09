from pathlib import Path

from tastebench import Benchmark, Candidate, MockJudge, PreferenceExample, ExpertJudgment
from tastebench.judges.content import build_multimodal_content, has_image, to_message_content
from tastebench.judges.image_utils import is_remote_or_data_uri, load_as_data_uri
from tastebench.judges.llm import LLMJudge

DATA = Path(__file__).resolve().parents[1] / "data"


def _img_example():
    return PreferenceExample(
        id="e",
        task="pick one",
        criteria=["restraint"],
        candidates=[
            Candidate(id="A", type="image", uri=str(DATA / "images" / "a_minimal.png")),
            Candidate(id="B", type="text", content="a busy design with lots of elements"),
        ],
        judgments=[ExpertJudgment(expert_id="1", choice="A")],
    )


def test_has_image_detection():
    ex = _img_example()
    assert has_image(ex)


def test_to_message_content_types():
    ex = _img_example()
    img_part = to_message_content(ex.candidates[0])
    txt_part = to_message_content(ex.candidates[1])
    assert img_part["type"] == "image_url"
    assert img_part["image_url"]["url"].startswith("data:image/png;base64,")
    assert txt_part["type"] == "text"


def test_remote_uri_passthrough():
    assert is_remote_or_data_uri("https://x/y.png")
    assert is_remote_or_data_uri("data:image/png;base64,AAAA")
    assert not is_remote_or_data_uri("local/path.png")


def test_load_local_as_data_uri():
    uri = load_as_data_uri(str(DATA / "images" / "a_minimal.png"))
    assert uri.startswith("data:image/png;base64,")


def test_llm_judge_builds_multimodal_message():
    judge = LLMJudge(model="gpt-4o")  # not called; just building messages
    messages = judge.build_messages(_img_example())
    assert len(messages) == 1
    content = messages[0]["content"]
    assert isinstance(content, list)
    kinds = [p["type"] for p in content]
    assert "image_url" in kinds and "text" in kinds


def test_llm_judge_text_path_unchanged():
    ex = PreferenceExample(
        id="t",
        task="pick",
        candidates=[Candidate(id="A", content="a"), Candidate(id="B", content="b")],
        judgments=[ExpertJudgment(expert_id="1", choice="A")],
    )
    messages = LLMJudge(model="gpt-4o").build_messages(ex)
    assert isinstance(messages[0]["content"], str)


def test_mock_judge_on_image_dataset():
    bench = Benchmark.from_jsonl(DATA / "design_image_sample.jsonl")
    results = bench.evaluate(MockJudge())
    assert results.n_examples == 2
