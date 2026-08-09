import pytest

from tastebench.tastegraph.api.ratelimit import RateLimiter


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def test_disabled_by_default():
    rl = RateLimiter()
    assert not rl.enabled
    for _ in range(100):
        assert rl.check("k") is None


def test_bucket_allows_burst_then_blocks():
    clock = FakeClock()
    rl = RateLimiter(rate_per_min=60, burst=3, clock=clock)  # 1 token/sec, burst 3
    assert rl.check("k") is None
    assert rl.check("k") is None
    assert rl.check("k") is None
    retry = rl.check("k")  # 4th within the same instant
    assert retry is not None and retry >= 1


def test_bucket_refills_over_time():
    clock = FakeClock()
    rl = RateLimiter(rate_per_min=60, burst=1, clock=clock)
    assert rl.check("k") is None
    assert rl.check("k") is not None  # empty
    clock.advance(1.0)  # +1 token
    assert rl.check("k") is None


def test_keys_are_independent():
    clock = FakeClock()
    rl = RateLimiter(rate_per_min=60, burst=1, clock=clock)
    assert rl.check("a") is None
    assert rl.check("b") is None  # different key, own bucket


def test_daily_quota():
    rl = RateLimiter(max_per_day=2)
    assert rl.check("k") is None
    assert rl.check("k") is None
    assert rl.check("k") is not None  # 3rd exceeds daily quota


def test_api_returns_429():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tastebench.tastegraph import TasteGraphEngine
    from tastebench.tastegraph.api.app import create_app

    rl = RateLimiter(rate_per_min=60, burst=2)
    client = TestClient(create_app(TasteGraphEngine(), limiter=rl))

    assert client.get("/health").status_code == 200  # health is exempt
    assert client.get("/metrics").status_code == 200
    assert client.get("/metrics").status_code == 200
    r = client.get("/metrics")
    assert r.status_code == 429
    assert "Retry-After" in r.headers
