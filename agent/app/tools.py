import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import settings
from app.prompt import LOCATION_DECIMALS, NO_DATA_MESSAGE

GUIDE_TOPICS = ["flood", "power_outage", "bomb_threat", "fire", "drought", "air_quality", "general"]

# Free text from external feeds (outage messages, warning bodies) is cut before it
# reaches the model: shorter prompts, less room for injected instructions (LLM01).
MAX_TEXT_LENGTH = 500

# Data tools serve Poland only (the api validates the same bounds)
PL_LAT = (49.0, 55.0)
PL_LON = (14.0, 24.2)


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GeocodeArgs(_Args):
    query: str = Field(min_length=2, max_length=200)


class PointArgs(_Args):
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, allow_inf_nan=False)


class OptionalPolandPointArgs(_Args):
    lat: float | None = Field(default=None, ge=PL_LAT[0], le=PL_LAT[1], allow_inf_nan=False)
    lon: float | None = Field(default=None, ge=PL_LON[0], le=PL_LON[1], allow_inf_nan=False)


class ShelterArgs(_Args):
    lat: float = Field(ge=PL_LAT[0], le=PL_LAT[1], allow_inf_nan=False)
    lon: float = Field(ge=PL_LON[0], le=PL_LON[1], allow_inf_nan=False)
    limit: int = Field(default=3, ge=1, le=10)


class GuideArgs(_Args):
    topic: Literal[
        "flood", "power_outage", "bomb_threat", "fire", "drought", "air_quality", "general"
    ]


class NoArgs(_Args):
    pass


def _number(description: str, bounds: tuple[float, float]) -> dict:
    return {
        "type": "number",
        "description": description,
        "minimum": bounds[0],
        "maximum": bounds[1],
    }


_LAT = _number("Latitude (WGS84), from geocode or the device location", PL_LAT)
_LON = _number("Longitude (WGS84), from geocode or the device location", PL_LON)


def _function(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    _function(
        "geocode",
        "Resolve a street, address or district to coordinates. Returns `found` and `in_krakow`. "
        "Always call it before answering about a specific place.",
        {
            "query": {
                "type": "string",
                "minLength": 2,
                "maxLength": 200,
                "description": "Place name, e.g. 'Kobierzyńska 1, Kraków'",
            }
        },
        ["query"],
    ),
    _function(
        "reverse_geocode",
        "Resolve coordinates (e.g. the user's device location) to a street and district. "
        "Returns `found` and `in_krakow`. Use it when the question names no place.",
        {
            "lat": _number("Latitude (WGS84)", (-90, 90)),
            "lon": _number("Longitude (WGS84)", (-180, 180)),
        },
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
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": "How many shelters, default 3",
            },
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

ARG_MODELS: dict[str, type[_Args]] = {
    "geocode": GeocodeArgs,
    "reverse_geocode": PointArgs,
    "get_warnings": OptionalPolandPointArgs,
    "get_water_levels": NoArgs,
    "get_air_quality": OptionalPolandPointArgs,
    "get_power_outages": OptionalPolandPointArgs,
    "find_nearest_shelter": ShelterArgs,
    "get_guide": GuideArgs,
}


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


def truncate_texts(value: Any, limit: int = MAX_TEXT_LENGTH) -> Any:
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit].rstrip() + "…"
    if isinstance(value, list):
        return [truncate_texts(v, limit) for v in value]
    if isinstance(value, dict):
        return {k: truncate_texts(v, limit) for k, v in value.items()}
    return value


def _restore_exact_point(
    args: dict[str, Any], location: tuple[float, float] | None
) -> dict[str, Any]:
    """The model only sees the device location rounded to ~100 m (LLM02); when it passes
    those rounded coordinates to a tool, the exact ones are used instead."""
    if not location or args.get("lat") is None or args.get("lon") is None:
        return args
    lat, lon = location
    try:
        matches = round(float(args["lat"]), LOCATION_DECIMALS) == round(
            lat, LOCATION_DECIMALS
        ) and round(float(args["lon"]), LOCATION_DECIMALS) == round(lon, LOCATION_DECIMALS)
    except (TypeError, ValueError):
        return args
    return {**args, "lat": lat, "lon": lon} if matches else args


class ToolExecutor:
    """Runs tool calls requested by the model against the `api` service.

    Arguments are validated before any request; failures never raise: the model gets an
    error it must report as "Brak danych".
    """

    def __init__(
        self, client: httpx.AsyncClient | None = None, now: datetime | None = None
    ) -> None:
        headers = (
            {"X-Internal-Token": settings.api_internal_token} if settings.api_internal_token else {}
        )
        self._client = client or httpx.AsyncClient(
            base_url=settings.api_url, timeout=httpx.Timeout(10.0, connect=3.0), headers=headers
        )
        self._now = now

    async def execute(
        self,
        name: str,
        arguments: str | dict[str, Any] | None,
        location: tuple[float, float] | None = None,
    ) -> ToolResult:
        model = ARG_MODELS.get(name)
        if model is None:
            return _error(f"Unknown tool: {name}")

        try:
            raw = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
        except json.JSONDecodeError:
            return _error("Invalid tool arguments")
        if not isinstance(raw, dict):
            return _error("Invalid tool arguments")

        try:
            args = model.model_validate(_restore_exact_point(raw, location))
        except ValidationError:
            return _error("Invalid tool arguments")
        return await self._dispatch(name, args)

    async def _dispatch(self, name: str, args: Any) -> ToolResult:
        if name == "geocode":
            return await self._get("/geocode", {"q": args.query})
        if name == "reverse_geocode":
            return await self._get("/reverse", {"lat": args.lat, "lon": args.lon})
        if name == "get_water_levels":
            return await self._get("/water-levels")
        if name == "find_nearest_shelter":
            params = {"lat": args.lat, "lon": args.lon, "limit": args.limit}
            return await self._get("/shelters/nearest", params)
        if name == "get_guide":
            return await self._get(f"/guide/{args.topic}")
        path = {
            "get_warnings": "/warnings",
            "get_air_quality": "/air-quality",
            "get_power_outages": "/power-outages",
        }[name]
        point = (
            {"lat": args.lat, "lon": args.lon}
            if args.lat is not None and args.lon is not None
            else None
        )
        return await self._get(path, point)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> ToolResult:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return _error(NO_DATA_MESSAGE)

        if not _is_envelope(payload):
            content = truncate_texts(payload)
            return ToolResult(content=json.dumps(content, ensure_ascii=False), payload=payload)

        now = self._now or datetime.now(UTC)
        enriched = truncate_texts(dict(payload))
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
