import time
from collections import deque
from collections.abc import Callable
from threading import Lock


class RateLimiter:
    """Sliding-window limit per client key (IP), kept in process memory.

    Caps GLM spending and abuse of the public endpoint (audit A4 / L4). Behind a
    reverse proxy the client IP must come from trusted proxy headers.
    """

    def __init__(
        self,
        limit: int,
        window_seconds: float = 60.0,
        max_keys: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._max_keys = max_keys
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = self._clock()
        with self._lock:
            hits = self._hits.get(key)
            if hits is None:
                if len(self._hits) >= self._max_keys:
                    self._drop_idle(now)
                hits = self._hits[key] = deque()
            while hits and now - hits[0] >= self._window:
                hits.popleft()
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True

    def _drop_idle(self, now: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or now - v[-1] >= self._window]:
            del self._hits[key]
        while len(self._hits) >= self._max_keys:
            self._hits.pop(next(iter(self._hits)))
