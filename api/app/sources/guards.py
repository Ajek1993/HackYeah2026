"""Protects cached data against truncated or tampered feeds (audit A2)."""

import logging

logger = logging.getLogger(__name__)

# A feed shrinking below this share of the currently active rows is treated as broken
MIN_FEED_RATIO = 0.5


def safe_to_deactivate(cur, table: str, fetched: int, where: str = "", params=()) -> bool:
    """False when the new feed is suspiciously small compared with what is active now.

    Rows missing from such a feed stay active until a feed of normal size arrives, so
    an outage of the source never wipes shelters or stations from the map.
    """
    cur.execute(f"SELECT count(*) AS n FROM {table} WHERE is_active {where}", params)
    active = cur.fetchone()["n"]
    if active and fetched < active * MIN_FEED_RATIO:
        logger.warning(
            "%s: feed has %d rows but %d are active; skipping deactivation", table, fetched, active
        )
        return False
    return True
