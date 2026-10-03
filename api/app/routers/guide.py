import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.envelope import envelope

router = APIRouter()

GUIDE_DIR = Path(__file__).resolve().parents[2] / "data" / "guide"
TOPICS = ("flood", "power_outage", "bomb_threat", "fire", "drought", "air_quality", "general")
SOURCE = "Poradnik bezpieczeństwa (MON, MSWiA, RCB)"
SOURCE_URL = "https://www.gov.pl/web/poradnikbezpieczenstwa"
PUBLISHED = datetime(2025, 12, 1, tzinfo=UTC)


@lru_cache
def load_topic(topic: str) -> dict | None:
    path = GUIDE_DIR / f"{topic}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/guide/{topic}")
async def guide(topic: str) -> dict:
    # Allowlist: the path parameter never reaches the filesystem unchecked
    if topic not in TOPICS:
        raise HTTPException(404, "unknown_topic")
    data = load_topic(topic)
    url = (data or {}).get("source_url", SOURCE_URL)
    # The guide is reference material: it never goes stale; a topic it does not cover -> null
    return envelope(SOURCE, url, PUBLISHED, data, static=True)
