import time
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from app.config import settings


@dataclass
class _Session:
    messages: list[dict[str, Any]] = field(default_factory=list)
    touched_at: float = 0.0


class SessionStore:
    """Conversation context kept only in process memory, expired after a TTL.

    Holds user questions and agent answers (address, household) — never persisted or logged.
    """

    def __init__(
        self,
        ttl_seconds: int | None = None,
        max_messages: int | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds or settings.session_ttl_seconds
        self._max_messages = max_messages or settings.session_max_messages
        self._clock = clock
        self._sessions: dict[str, _Session] = {}
        self._lock = Lock()

    def history(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            self._purge_expired()
            session = self._sessions.get(session_id)
            return list(session.messages) if session else []

    def append(self, session_id: str, *messages: dict[str, Any]) -> None:
        with self._lock:
            self._purge_expired()
            session = self._sessions.setdefault(session_id, _Session())
            session.messages.extend(messages)
            del session.messages[: -self._max_messages]
            session.touched_at = self._clock()

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def _purge_expired(self) -> None:
        deadline = self._clock() - self._ttl
        for session_id in [s for s, v in self._sessions.items() if v.touched_at < deadline]:
            del self._sessions[session_id]
