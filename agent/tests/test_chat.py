import json
import logging
import re
import time
from types import SimpleNamespace

import pytest

from app.prompt import DISCLAIMER
from app.session import SESSION_ID_PATTERN, SessionStore
from app.tools import Source, ToolResult

ADDRESS = "Testowa 1, Kraków"  # fictional address only (SPEC: Never)
UPDATED_AT = "2026-10-04T10:30:00+02:00"


def tool_call(name: str, arguments: dict, call_id: str = "call-1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


def llm_message(content: str | None = None, tool_calls=None):
    return SimpleNamespace(role="assistant", content=content, tool_calls=tool_calls)


def final_json(**fields) -> str:
    body = {
        "answer": "Odpowiedź",
        "sections": None,
        "emergency": False,
        "out_of_area": False,
        "off_topic": False,
    }
    body.update(fields)
    return json.dumps(body, ensure_ascii=False)


class FakeLLM:
    """Returns scripted messages and records what it was sent."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def complete(self, messages, tools=None):
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools})
        return self.responses.pop(0)


class FakeTools:
    def __init__(self, results: dict[str, ToolResult] | None = None):
        self.results = results or {}
        self.calls: list[tuple[str, str]] = []
        self.locations: list = []

    async def execute(self, name, arguments, location=None):
        self.calls.append((name, arguments))
        self.locations.append(location)
        return self.results.get(name, ToolResult(content='{"error": "Brak danych"}'))


def imgw_result(*, is_stale=False, is_simulated=False) -> ToolResult:
    source = Source("IMGW", "https://danepubliczne.imgw.pl/", UPDATED_AT, is_stale, is_simulated)
    return ToolResult(content='{"data": []}', sources=[source])


def post(client, message, session_id=None):
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    return client.post("/chat", json=payload)


def test_answer_without_tools_has_contract_shape(make_client):
    client = make_client(FakeLLM(llm_message(final_json(answer="Cześć"))))

    response = post(client, "Pytanie")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "session_id",
        "answer",
        "sections",
        "sources",
        "emergency",
        "out_of_area",
        "off_topic",
        "is_simulated",
        "disclaimer",
    }
    assert re.fullmatch(SESSION_ID_PATTERN, body["session_id"])
    assert body["answer"] == "Cześć"
    assert body["disclaimer"] == DISCLAIMER


def test_tool_loop_executes_calls_and_returns_sources(make_client):
    sections = {"situation": "Brak ostrzeżeń", "before": ["a"], "during": ["b"], "after": ["c"]}
    llm = FakeLLM(
        llm_message(tool_calls=[tool_call("get_warnings", {"lat": 50.0, "lon": 19.9})]),
        llm_message(final_json(answer="Spokojnie", sections=sections)),
    )
    tools = FakeTools({"get_warnings": imgw_result(is_stale=True)})
    client = make_client(llm, tools)

    body = post(client, "Czy grozi zalanie?").json()

    assert tools.calls == [("get_warnings", json.dumps({"lat": 50.0, "lon": 19.9}))]
    second_call = llm.calls[1]["messages"]
    assert second_call[-2]["tool_calls"][0]["function"]["name"] == "get_warnings"
    assert second_call[-1] == {"role": "tool", "tool_call_id": "call-1", "content": '{"data": []}'}
    assert body["sections"] == sections
    assert body["sources"] == [
        {
            "name": "IMGW",
            "url": "https://danepubliczne.imgw.pl/",
            "updated_at": UPDATED_AT,
            "is_stale": True,
        }
    ]
    assert body["is_simulated"] is False


def test_repeated_source_is_listed_once(make_client):
    llm = FakeLLM(
        llm_message(
            tool_calls=[
                tool_call("get_warnings", {}, "call-1"),
                tool_call("get_water_levels", {}, "call-2"),
            ]
        ),
        llm_message(final_json()),
    )
    tools = FakeTools({"get_warnings": imgw_result(), "get_water_levels": imgw_result()})

    body = post(make_client(llm, tools), "Pytanie").json()

    assert len(body["sources"]) == 1


def test_simulated_source_marks_response(make_client):
    llm = FakeLLM(
        llm_message(tool_calls=[tool_call("get_warnings", {})]),
        llm_message(final_json()),
    )
    tools = FakeTools({"get_warnings": imgw_result(is_simulated=True)})

    assert post(make_client(llm, tools), "Pytanie").json()["is_simulated"] is True


def test_second_question_in_session_sees_address_from_first(make_client):
    llm = FakeLLM(llm_message(final_json(answer="Jasne")), llm_message(final_json()))
    client = make_client(llm)

    session_id = post(client, f"Mieszkam przy ulicy {ADDRESS}").json()["session_id"]
    second_body = post(client, "A czy grozi mi zalanie?", session_id).json()

    assert second_body["session_id"] == session_id
    second = llm.calls[1]["messages"]
    assert second[0]["role"] == "system"
    assert second[1] == {"role": "user", "content": f"Mieszkam przy ulicy {ADDRESS}"}
    assert second[2] == {"role": "assistant", "content": "Jasne"}
    assert second[3] == {"role": "user", "content": "A czy grozi mi zalanie?"}


def test_question_without_session_starts_a_new_one(make_client):
    llm = FakeLLM(llm_message(final_json()), llm_message(final_json()))
    client = make_client(llm)

    first = post(client, ADDRESS).json()["session_id"]
    second = post(client, "Pytanie").json()["session_id"]

    assert first != second
    assert len(llm.calls[1]["messages"]) == 2  # system + new question only


def test_unknown_session_id_gets_a_fresh_server_issued_id(make_client):
    # A client cannot pick an id (e.g. guess another user's) and read that context
    llm = FakeLLM(llm_message(final_json()))
    client = make_client(llm)

    made_up = "x" * 32
    body = post(client, "Pytanie", made_up).json()

    assert body["session_id"] != made_up
    assert len(llm.calls[0]["messages"]) == 2


@pytest.mark.parametrize("session_id", ["short", "x" * 65, "bad id with spaces!"])
def test_malformed_session_id_is_rejected(make_client, session_id):
    client = make_client(FakeLLM())

    response = client.post("/chat", json={"session_id": session_id, "message": "Pytanie"})

    assert response.status_code == 422


def test_delete_clears_session(make_client):
    llm = FakeLLM(llm_message(final_json()), llm_message(final_json()))
    client = make_client(llm)

    session_id = post(client, ADDRESS).json()["session_id"]
    assert client.delete(f"/chat/{session_id}").status_code == 204
    body = post(client, "Pytanie", session_id).json()

    assert body["session_id"] != session_id
    assert len(llm.calls[1]["messages"]) == 2


def test_delete_rejects_malformed_session_id(make_client):
    assert make_client(FakeLLM()).delete("/chat/bad id").status_code == 422


def test_tool_budget_exhausted_forces_final_answer_without_tools(make_client):
    loop = [llm_message(tool_calls=[tool_call("get_warnings", {})]) for _ in range(2)]
    llm = FakeLLM(*loop, llm_message(final_json(answer="Koniec")))

    body = post(make_client(llm, max_tool_rounds=2), "Pytanie").json()

    assert body["answer"] == "Koniec"
    assert llm.calls[-1]["tools"] is None


def test_off_topic_and_out_of_area_have_no_disclaimer(make_client):
    llm = FakeLLM(
        llm_message(final_json(off_topic=True)),
        llm_message(final_json(out_of_area=True)),
    )
    client = make_client(llm)

    assert post(client, "Przepis na pierogi").json()["disclaimer"] is None
    assert post(client, "Skawina").json()["disclaimer"] is None


def test_emergency_flag_is_passed_through(make_client):
    llm = FakeLLM(llm_message(final_json(answer="Dzwoń 112", emergency=True)))

    assert post(make_client(llm), "Woda wlewa się do piwnicy").json()["emergency"] is True


def test_json_in_code_fence_is_parsed(make_client):
    content = "```json\n" + final_json(answer="Z bloku kodu") + "\n```"
    llm = FakeLLM(llm_message(content))

    assert post(make_client(llm), "Pytanie").json()["answer"] == "Z bloku kodu"


def test_plain_text_answer_falls_back_to_answer_field(make_client):
    llm = FakeLLM(llm_message("Zwykły tekst bez JSON"))

    body = post(make_client(llm), "Pytanie").json()

    assert body["answer"] == "Zwykły tekst bez JSON"
    assert body["sections"] is None


def test_invalid_sections_are_dropped(make_client):
    llm = FakeLLM(llm_message(final_json(sections={"before": "not a list"})))

    assert post(make_client(llm), "Pytanie").json()["sections"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"message": ""},
        {"session_id": "", "message": "Pytanie"},
        {"message": "x" * 2001},
        {"message": "Pytanie", "unexpected": True},
    ],
)
def test_invalid_request_is_rejected(make_client, payload):
    client = make_client(FakeLLM())

    assert client.post("/chat", json=payload).status_code == 422


def test_chat_content_is_not_logged(make_client, caplog):
    llm = FakeLLM(llm_message(final_json(answer="Odpowiedź")))

    with caplog.at_level(logging.DEBUG):
        post(make_client(llm), f"Mieszkam przy ulicy {ADDRESS}")

    assert ADDRESS not in caplog.text


def test_tool_calls_per_round_are_capped(make_client):
    calls = [tool_call("get_warnings", {}, f"call-{i}") for i in range(8)]
    llm = FakeLLM(llm_message(tool_calls=calls), llm_message(final_json()))
    tools = FakeTools()

    post(make_client(llm, tools, max_tool_calls=6), "Pytanie")

    assert len(tools.calls) == 6
    tool_messages = [m for m in llm.calls[1]["messages"] if m["role"] == "tool"]
    assert len(tool_messages) == 8  # every call gets an answer, the extra ones an error
    assert "Too many tool calls" in tool_messages[-1]["content"]


def test_deadline_forces_final_answer(make_client):
    now = [0.0]

    def clock():
        now[0] += 30.0  # every check moves time by 30 s
        return now[0]

    llm = FakeLLM(
        llm_message(tool_calls=[tool_call("get_warnings", {})]),
        llm_message(final_json(answer="Na czas")),
    )

    body = post(make_client(llm, deadline_s=45, clock=clock), "Pytanie").json()

    assert body["answer"] == "Na czas"
    assert llm.calls[-1]["tools"] is None
    assert len(llm.calls) == 2


def test_chat_is_rate_limited_per_client(make_client):
    from app.ratelimit import RateLimiter

    llm = FakeLLM(*[llm_message(final_json()) for _ in range(3)])
    client = make_client(llm, limiter=RateLimiter(2))

    codes = [post(client, "Pytanie").status_code for _ in range(3)]

    assert codes == [200, 200, 429]
    assert "Za dużo pytań" in post(client, "Pytanie").json()["detail"]


def test_session_store_expires_after_ttl():
    now = [0.0]
    sessions = SessionStore(ttl_seconds=10, max_messages=20, clock=lambda: now[0])
    session_id = sessions.resolve(None)
    sessions.append(session_id, {"role": "user", "content": "a"})

    now[0] = 11.0

    assert sessions.resolve(session_id) != session_id
    assert sessions.history(session_id) == []


def test_session_store_keeps_only_recent_messages():
    sessions = SessionStore(ttl_seconds=10, max_messages=3, clock=lambda: 0.0)
    session_id = sessions.resolve(None)

    for i in range(5):
        sessions.append(session_id, {"role": "user", "content": str(i)})

    assert [m["content"] for m in sessions.history(session_id)] == ["2", "3", "4"]


def test_session_store_caps_number_of_sessions():
    sessions = SessionStore(ttl_seconds=60, max_messages=5, max_sessions=3, clock=time.monotonic)

    ids = [sessions.resolve(None) for _ in range(5)]

    assert len(sessions) == 3
    assert sessions.resolve(ids[0]) != ids[0]  # oldest one was dropped
    assert sessions.resolve(ids[-1]) == ids[-1]


def test_session_ids_are_random_and_url_safe():
    sessions = SessionStore(ttl_seconds=60, max_messages=5)

    ids = {sessions.resolve(None) for _ in range(50)}

    assert len(ids) == 50
    assert all(re.fullmatch(SESSION_ID_PATTERN, i) for i in ids)
