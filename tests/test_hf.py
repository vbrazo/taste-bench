import pytest

pytest.importorskip("datasets")

from tastebench.datasets.hf import from_hf_dataset, to_hf_dataset


def test_round_trip_preserves_data(sample_examples):
    ds = to_hf_dataset(sample_examples)
    assert len(ds) == len(sample_examples)
    back = from_hf_dataset(ds)
    assert [e.id for e in back] == [e.id for e in sample_examples]
    assert back[0].preference == sample_examples[0].preference
    assert len(back[0].judgments) == len(sample_examples[0].judgments)
