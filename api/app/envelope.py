from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

STALE_AFTER = timedelta(hours=3)
WARSAW = ZoneInfo("Europe/Warsaw")


def iso(value: datetime | None) -> str | None:
    """ISO 8601 in Kraków time (`+02:00` / `+01:00`), as in the API contract."""
    return value.astimezone(WARSAW).isoformat() if value else None


def is_stale(updated_at: datetime | None, now: datetime | None = None) -> bool:
    if updated_at is None:
        return False
    return (now or datetime.now(UTC)) - updated_at > STALE_AFTER


def envelope(
    source: str,
    source_url: str | None,
    updated_at: datetime | None,
    data: Any,
    now: datetime | None = None,
    static: bool = False,
) -> dict[str, Any]:
    """Common wrapper for every data reading (docs_ai/api-contract.md).

    `updated_at` is when KryzIO last fetched the source; `data` is None when the
    source has never been fetched ("Brak danych"). `static` marks reference
    material (the safety guide) that never goes stale.
    """
    return {
        "source": source,
        "source_url": source_url,
        "updated_at": iso(updated_at),
        "is_stale": False if static else is_stale(updated_at, now),
        "is_simulated": False,
        "data": data if updated_at is not None or static else None,
    }
