from pathlib import Path

import pytest

from tastebench import load_jsonl

DATA = Path(__file__).resolve().parents[1] / "data" / "design_sample.jsonl"


@pytest.fixture
def sample_examples():
    return load_jsonl(DATA)


@pytest.fixture
def sample_path():
    return DATA
