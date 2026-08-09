"""Contract test: the JS SDK's example payload must validate against the Python Signal model.

This is the guard that keeps `@tastegraph/sdk` and the Python `Signal` wire format from
drifting. If the JS SDK changes its emitted shape, update fixtures/signal.json — and this
test enforces it stays loadable server-side.
"""

import json
from pathlib import Path

from tastebench.tastegraph.signals.schema import ACTION_WEIGHTS, Signal

FIXTURE = Path(__file__).resolve().parents[1] / "sdk-js" / "fixtures" / "signal.json"


def test_fixture_validates_against_signal_model():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    sig = Signal.model_validate(data)
    assert sig.user_id == data["user_id"]
    assert sig.asset_id == data["asset_id"]
    assert sig.action in ACTION_WEIGHTS
    # null weight -> the server supplies the action's default
    assert sig.effective_weight() == ACTION_WEIGHTS[sig.action]


def test_fixture_has_exactly_the_wire_fields():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert set(data.keys()) == {"user_id", "asset_id", "action", "weight", "timestamp", "session_id"}
