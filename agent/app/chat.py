import json
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.llm import GLMClient
from app.prompt import (
    DISCLAIMER,
    EMERGENCY_NO_GUIDE_MESSAGE,
    OUT_OF_AREA_MESSAGE,
    build_location_note,
    build_system_prompt,
)
from app.session import SESSION_ID_PATTERN, SessionStore
from app.tools import TOOL_DEFINITIONS, Source, ToolExecutor, ToolResult

TOO_MANY_CALLS = ToolResult(content=json.dumps({"error": "Too many tool calls in one turn"}))


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, allow_inf_nan=False)
    accuracy_m: float | None = Field(default=None, ge=0, le=100_000, allow_inf_nan=False)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Omitted on the first question; afterwards the id issued by the agent
    session_id: str | None = Field(default=None, pattern=SESSION_ID_PATTERN)
    message: str = Field(min_length=1, max_length=2000)
    location: Location | None = None


class Sections(BaseModel):
    situation: str = ""
    before: list[str] = []
    during: list[str] = []
    after: list[str] = []


class SourceOut(BaseModel):
    name: str
    url: str | None
    updated_at: str | None
    is_stale: bool


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sections: Sections | None
    sources: list[SourceOut]
    emergency: bool
    out_of_area: bool
    off_topic: bool
    is_simulated: bool
    disclaimer: str | None


def _assistant_message(message: Any) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": message.content or "",
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments},
            }
            for call in message.tool_calls
        ],
    }


RESPONSE_KEYS = {"answer", "sections", "emergency", "out_of_area", "off_topic"}


def _parse_final(content: str | None) -> dict[str, Any]:
    """Extract the JSON object the prompt asks for; fall back to plain text.

    The model sometimes writes the answer as prose and appends a JSON object
    without `answer` — then the prose becomes the answer and the JSON keeps
    supplying sections and flags, so raw JSON never reaches the user.
    """
    text = (content or "").strip()
    decoder = json.JSONDecoder()
    index = text.find("{")
    while index != -1:
        try:
            parsed, _ = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict) and RESPONSE_KEYS & parsed.keys():
            if isinstance(parsed.get("answer"), str):
                return parsed
            prose = text[:index].strip().removesuffix("```json").removesuffix("```").strip()
            sections = parsed.get("sections")
            situation = sections.get("situation") if isinstance(sections, dict) else None
            return {**parsed, "answer": prose or (situation if isinstance(situation, str) else "")}
        index = text.find("{", index + 1)
    return {"answer": text}


def _parse_sections(raw: Any) -> Sections | None:
    if not isinstance(raw, dict):
        return None
    try:
        return Sections.model_validate(raw)
    except ValueError:
        return None


class ChatService:
    def __init__(
        self,
        llm: GLMClient,
        tools: ToolExecutor,
        sessions: SessionStore,
        max_tool_rounds: int | None = None,
        max_tool_calls: int | None = None,
        deadline_s: float | None = None,
        clock=time.monotonic,
    ) -> None:
        self._llm = llm
        self._tools = tools
        self._sessions = sessions
        self._max_tool_rounds = max_tool_rounds or settings.max_tool_rounds
        self._max_tool_calls = max_tool_calls or settings.max_tool_calls_per_round
        self._deadline_s = deadline_s or settings.request_deadline_s
        self._clock = clock

    async def reply(self, request: ChatRequest) -> ChatResponse:
        started = self._clock()
        session_id = self._sessions.resolve(request.session_id)
        user_message = {"role": "user", "content": request.message}
        messages = [
            {"role": "system", "content": build_system_prompt()},
            *self._sessions.history(session_id),
        ]
        location = None
        if request.location:
            # Sent with every request, never stored in the session: device location is sensitive.
            loc = request.location
            location = (loc.lat, loc.lon)
            messages.append(
                {"role": "system", "content": build_location_note(loc.lat, loc.lon, loc.accuracy_m)}
            )
        messages.append(user_message)
        sources: dict[tuple[str, str | None], Source] = {}
        geocoded: list[dict[str, Any]] = []
        guide_loaded = False

        final = None
        for _ in range(self._max_tool_rounds):
            if self._clock() - started > self._deadline_s:
                break  # time budget spent: answer from what has been gathered
            message = await self._llm.complete(messages, tools=TOOL_DEFINITIONS)
            if not message.tool_calls:
                final = message
                break
            messages.append(_assistant_message(message))
            for index, call in enumerate(message.tool_calls):
                if index >= self._max_tool_calls:
                    result = TOO_MANY_CALLS
                else:
                    result = await self._tools.execute(
                        call.function.name, call.function.arguments, location
                    )
                for source in result.sources:
                    sources[(source.name, source.updated_at)] = source
                if call.function.name in ("geocode", "reverse_geocode") and result.payload:
                    geocoded.append(result.payload)
                if call.function.name == "get_guide" and result.payload:
                    guide_loaded = guide_loaded or result.payload.get("data") is not None
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": result.content}
                )
            if _outside_krakow(geocoded):
                # Fixed message, no further model round (US-01, saves tokens).
                return self._respond(session_id, user_message, {"out_of_area": True}, {}, False)
        if final is None:
            # Tool or time budget exhausted: force an answer from what has been gathered.
            final = await self._llm.complete(messages)

        parsed = _parse_final(final.content)
        return self._respond(session_id, user_message, parsed, sources, guide_loaded)

    def _respond(
        self,
        session_id: str,
        user_message: dict[str, Any],
        parsed: dict[str, Any],
        sources: dict[tuple[str, str | None], Source],
        guide_loaded: bool,
    ) -> ChatResponse:
        out_of_area = bool(parsed.get("out_of_area"))
        off_topic = bool(parsed.get("off_topic")) and not out_of_area
        emergency = bool(parsed.get("emergency"))
        if out_of_area:
            answer, sections, sources = OUT_OF_AREA_MESSAGE, None, {}
        elif emergency and not guide_loaded:
            # Without the safety guide the model must not improvise life-saving steps.
            answer, sections = EMERGENCY_NO_GUIDE_MESSAGE, None
        else:
            answer, sections = parsed["answer"], _parse_sections(parsed.get("sections"))

        self._sessions.append(session_id, user_message, {"role": "assistant", "content": answer})

        return ChatResponse(
            session_id=session_id,
            answer=answer,
            sections=sections,
            sources=[
                SourceOut(name=s.name, url=s.url, updated_at=s.updated_at, is_stale=s.is_stale)
                for s in sources.values()
            ],
            emergency=emergency,
            out_of_area=out_of_area,
            off_topic=off_topic,
            is_simulated=any(s.is_simulated for s in sources.values()),
            disclaimer=None if off_topic or out_of_area else DISCLAIMER,
        )


def _outside_krakow(geocoded: list[dict[str, Any]]) -> bool:
    """True when the user asked only about places that were found outside Kraków."""
    found = [g for g in geocoded if g.get("found")]
    return bool(found) and not any(g.get("in_krakow") for g in found)
