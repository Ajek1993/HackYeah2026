import secrets
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from app.config import settings

SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{16,64}$"


@dataclass
class _Session:
    messages: list[dict[str, Any]] = field(default_factory=list)
    touched_at: float = 0.0


class SessionStore:
    """Conversation context kept only in process memory, expired after a TTL.

    Session ids are issued here (never chosen by the client), so nobody can read another
    conversation by guessing its id. Holds user questions and agent answers (address,
    household) — never persisted or logged. The number of sessions is capped; the least
    recently used ones are dropped first.
    """

    def __init__(
        self,
        ttl_seconds: int | None = None,
        max_messages: int | None = None,
        max_sessions: int | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds or settings.session_ttl_seconds
        self._max_messages = max_messages or settings.session_max_messages
        self._max_sessions = max_sessions or settings.session_max_count
        self._clock = clock
        self._sessions: OrderedDict[str, _Session] = OrderedDict()
        self._lock = Lock()

    def resolve(self, session_id: str | None) -> str:
        """Returns the id when the session is alive, otherwise issues a new one."""
        with self._lock:
            self._purge_expired()
            if session_id and session_id in self._sessions:
                return session_id
            new_id = secrets.token_urlsafe(24)
            self._sessions[new_id] = _Session(touched_at=self._clock())
            while len(self._sessions) > self._max_sessions:
                self._sessions.popitem(last=False)
            return new_id

    def history(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id)
            return list(session.messages) if session else []

    def append(self, session_id: str, *messages: dict[str, Any]) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                # Expired or evicted meanwhile: the answer is still returned, context is not kept
                return
            session.messages.extend(messages)
            del session.messages[: -self._max_messages]
            session.touched_at = self._clock()
            self._sessions.move_to_end(session_id)

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def __len__(self) -> int:
        return len(self._sessions)

    def _purge_expired(self) -> None:
        deadline = self._clock() - self._ttl
        for session_id in [s for s, v in self._sessions.items() if v.touched_at < deadline]:
            del self._sessions[session_id]
