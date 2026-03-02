from __future__ import annotations

import time
from collections import deque


class InMemoryRateLimiter:
    def __init__(self, limit_per_minute: int):
        self.limit_per_minute = limit_per_minute
        self._buckets: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        bucket = self._buckets.setdefault(key, deque())
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= self.limit_per_minute:
            return False
        bucket.append(now)
        return True

