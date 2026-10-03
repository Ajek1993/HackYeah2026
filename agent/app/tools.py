import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from app.config import settings
from app.prompt import NO_DATA_MESSAGE

GUIDE_TOPICS = ["flood", "power_outage", "bomb_threat", "fire", "drought", "air_quality", "general"]

_LAT = {"type": "number", "description": "Latitude (WGS84), from geocode or the device location"}
_LON = {"type": "number", "description": "Longitude (WGS84), from geocode or the device location"}


def _function(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    _function(
        "geocode",
        "Resolve a street, address or district to coordinates. Returns `found` and `in_krakow`. "
        "Always call it before answering about a specific place.",
        {"query": {"type": "string", "description": "Place name, e.g. 'Kobierzyńska 1, Kraków'"}},
        ["query"],
    ),
    _function(
        "reverse_geocode",
        "Resolve coordinates (e.g. the user's device location) to a street and district. "
        "Returns `found` and `in_krakow`. Use it when the question names no place.",
        {"lat": _LAT, "lon": _LON},
        ["lat", "lon"],
    ),
    _function(
        "get_warnings",
        "Active IMGW meteorological and hydrological warnings for a point in Kraków "
        "(or the whole city when no coordinates are given).",
        {"lat": _LAT, "lon": _LON},
        [],
    ),
    _function(
        "get_water_levels",
        "Current river water levels at gauging stations in Kraków with warning and alarm levels.",
        {},
        [],
    ),
    _function(
        "get_air_quality",
        "Freshest air quality reading (GIOŚ or Airly) near a point in Kraków.",
        {"lat": _LAT, "lon": _LON},
        [],
    ),
    _function(
        "get_power_outages",
        "Planned and unplanned power outages (Tauron) near a point in Kraków.",
        {"lat": _LAT, "lon": _LON},
        [],
    ),
    _function(
        "find_nearest_shelter",
        "Nearest shelters and hiding places to a point, sorted by distance in metres.",
        {
            "lat": _LAT,
            "lon": _LON,
            "limit": {"type": "integer", "description": "How many shelters, default 3"},
        },
        ["lat", "lon"],
    ),
    _function(
        "get_guide",
        "Official safety guide steps (before / during / after) and emergency numbers for a topic.",
        {"topic": {"type": "string", "enum": GUIDE_TOPICS}},
        ["topic"],
    ),
]


@dataclass(frozen=True)
class Source:
    name: str
    url: str | None
    updated_at: str | None
    is_stale: bool
    is_simulated: bool


@dataclass
class ToolResult:
    content: str  # JSON passed back to the model as the tool message
    sources: list[Source] = field(default_factory=list)
    payload: dict[str, Any] | None = None  # parsed api response, for rules in the chat endpoint


def _error(message: str) -> ToolResult:
    return ToolResult(content=json.dumps({"error": message}, ensure_ascii=False))


def _age_hours(updated_at: str | None, now: datetime) -> int | None:
    if not updated_at:
        return None
    try:
        updated = datetime.fromisoformat(updated_at)
    except ValueError:
        return None
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=UTC)
    return max(0, int((now - updated).total_seconds() // 3600))


def _is_envelope(payload: Any) -> bool:
    return isinstance(payload, dict) and "source" in payload and "data" in payload


class ToolExecutor:
    """Runs tool calls requested by the model against the `api` service.

    Failures never raise: the model gets an error it must report as "Brak danych".
    """

    def __init__(self, client: httpx.Client | None = None, now: datetime | None = None) -> None:
        self._client = client or httpx.Client(base_url=settings.api_url, timeout=10.0)
        self._now = now

    def execute(self, name: str, arguments: str | dict[str, Any] | None) -> ToolResult:
        handler = self._handlers().get(name)
        if handler is None:
            return _error(f"Unknown tool: {name}")

        try:
            args = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
        except json.JSONDecodeError:
            return _error("Invalid tool arguments")
        if not isinstance(args, dict):
            return _error("Invalid tool arguments")

        try:
            return handler(args)
        except (KeyError, TypeError, ValueError):
            return _error("Invalid tool arguments")

    def _handlers(self) -> dict:
        return {
            "geocode": lambda a: self._get("/geocode", {"q": a["query"]}),
            "reverse_geocode": lambda a: self._get(
                "/reverse", {"lat": float(a["lat"]), "lon": float(a["lon"])}
            ),
            "get_warnings": lambda a: self._get("/warnings", _point(a)),
            "get_water_levels": lambda a: self._get("/water-levels"),
            "get_air_quality": lambda a: self._get("/air-quality", _point(a)),
            "get_power_outages": lambda a: self._get("/power-outages", _point(a)),
            "find_nearest_shelter": lambda a: self._get(
                "/shelters/nearest",
                {"lat": float(a["lat"]), "lon": float(a["lon"]), "limit": int(a.get("limit", 3))},
            ),
            "get_guide": self._guide,
        }

    def _guide(self, args: dict[str, Any]) -> ToolResult:
        topic = args["topic"]
        if topic not in GUIDE_TOPICS:
            return _error(f"Unknown guide topic, use one of: {', '.join(GUIDE_TOPICS)}")
        return self._get(f"/guide/{topic}")

    def _get(self, path: str, params: dict[str, Any] | None = None) -> ToolResult:
        try:
            response = self._client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return _error(NO_DATA_MESSAGE)

        if not _is_envelope(payload):
            return ToolResult(content=json.dumps(payload, ensure_ascii=False), payload=payload)

        now = self._now or datetime.now(UTC)
        enriched = dict(payload)
        if enriched["data"] is None:
            enriched["note"] = NO_DATA_MESSAGE
        if enriched.get("is_stale"):
            enriched["age_hours"] = _age_hours(enriched.get("updated_at"), now)

        source = Source(
            name=payload["source"],
            url=payload.get("source_url"),
            updated_at=payload.get("updated_at"),
            is_stale=bool(payload.get("is_stale")),
            is_simulated=bool(payload.get("is_simulated")),
        )
        return ToolResult(
            content=json.dumps(enriched, ensure_ascii=False),
            sources=[source],
            payload=payload,
        )


def _point(args: dict[str, Any]) -> dict[str, float] | None:
    if args.get("lat") is None or args.get("lon") is None:
        return None
    return {"lat": float(args["lat"]), "lon": float(args["lon"])}
