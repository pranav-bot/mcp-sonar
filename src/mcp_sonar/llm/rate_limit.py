from __future__ import annotations

import asyncio
import time
from collections import deque


class MinuteRateLimiter:
    """Fixed-window style limiter: at most ``max_calls`` per 60 seconds."""

    def __init__(self, max_calls: int, window_seconds: float = 60.0) -> None:
        if max_calls < 1:
            raise ValueError("max_calls must be at least 1")
        self._max_calls = max_calls
        self._window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            while self._timestamps and now - self._timestamps[0] >= self._window:
                self._timestamps.popleft()
            if len(self._timestamps) >= self._max_calls:
                wait_for = self._window - (now - self._timestamps[0])
                if wait_for > 0:
                    await asyncio.sleep(wait_for)
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self._window:
                    self._timestamps.popleft()
            self._timestamps.append(time.monotonic())
