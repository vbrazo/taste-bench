"""Per-API-key rate limiting + daily quota (Item 2).

Dependency-free token bucket keyed by tenant/API-key, plus a rolling daily quota. In-process
only (per-process buckets; a shared store like Redis is out of scope). Unset limits == disabled,
so dev mode and existing tests are unlimited.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class _Bucket:
    tokens: float
    last: float


class RateLimiter:
    """Token bucket: ``rate_per_min`` tokens/min, up to ``burst`` in reserve.

    ``check(key)`` returns None if allowed, or the integer seconds to wait (Retry-After).
    A ``clock`` is injectable for testing.
    """

    def __init__(
        self,
        rate_per_min: float = 0.0,
        burst: Optional[int] = None,
        max_per_day: int = 0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.rate_per_sec = rate_per_min / 60.0 if rate_per_min else 0.0
        self.burst = burst if burst is not None else max(1, int(rate_per_min))
        self.max_per_day = max_per_day
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}
        self._daily: dict[str, list] = {}  # key -> [day_index, count]

    @property
    def enabled(self) -> bool:
        return self.rate_per_sec > 0 or self.max_per_day > 0

    def check(self, key: str) -> Optional[int]:
        if not self.enabled:
            return None
        now = self._clock()

        # daily quota (wall-clock day)
        if self.max_per_day > 0:
            day = int(time.time() // 86400)
            slot = self._daily.get(key)
            if slot is None or slot[0] != day:
                slot = [day, 0]
                self._daily[key] = slot
            if slot[1] >= self.max_per_day:
                return 86400 - int(time.time() % 86400)
            slot[1] += 1

        # token bucket
        if self.rate_per_sec > 0:
            b = self._buckets.get(key)
            if b is None:
                b = _Bucket(tokens=self.burst, last=now)
                self._buckets[key] = b
            b.tokens = min(self.burst, b.tokens + (now - b.last) * self.rate_per_sec)
            b.last = now
            if b.tokens < 1.0:
                need = (1.0 - b.tokens) / self.rate_per_sec
                return max(1, int(need + 0.999))
            b.tokens -= 1.0
        return None
