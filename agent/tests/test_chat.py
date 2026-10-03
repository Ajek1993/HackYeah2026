import json
import logging
from types import SimpleNamespace

import pytest

from app.prompt import DISCLAIMER
from app.session import SessionStore
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

    def complete(self, messages, tools=None):
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools})
        return self.responses.pop(0)


class FakeTools:
    def __init__(self, results: dict[str, ToolResult] | None = None):
        self.results = results or {}
        self.calls: list[tuple[str, str]] = []

    def execute(self, name, arguments):
        self.calls.append((name, arguments))
        return self.results.get(name, ToolResult(content='{"error": "Brak danych"}'))


def imgw_result(*, is_stale=False, is_simulated=False) -> ToolResult:
    source = Source("IMGW", "https://danepubliczne.imgw.pl/", UPDATED_AT, is_stale, is_simulated)
    return ToolResult(content='{"data": []}', sources=[source])


def post(client, message, session_id="s-1"):
    return client.post("/chat", json={"session_id": session_id, "message": message})


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
    assert body["session_id"] == "s-1"
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

    post(client, f"Mieszkam przy ulicy {ADDRESS}")
    post(client, "A czy grozi mi zalanie?")

    second = llm.calls[1]["messages"]
    assert second[0]["role"] == "system"
    assert second[1] == {"role": "user", "content": f"Mieszkam przy ulicy {ADDRESS}"}
    assert second[2] == {"role": "assistant", "content": "Jasne"}
    assert second[3] == {"role": "user", "content": "A czy grozi mi zalanie?"}


def test_sessions_are_isolated(make_client):
    llm = FakeLLM(llm_message(final_json()), llm_message(final_json()))
    client = make_client(llm)

    post(client, ADDRESS, session_id="a")
    post(client, "Pytanie", session_id="b")

    assert len(llm.calls[1]["messages"]) == 2  # system + new question only


def test_delete_clears_session(make_client):
    llm = FakeLLM(llm_message(final_json()), llm_message(final_json()))
    client = make_client(llm)

    post(client, ADDRESS)
    assert client.delete("/chat/s-1").status_code == 204
    post(client, "Pytanie")

    assert len(llm.calls[1]["messages"]) == 2


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
        {"session_id": "s-1", "message": ""},
        {"session_id": "", "message": "Pytanie"},
        {"session_id": "s-1", "message": "x" * 2001},
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


def test_session_store_expires_after_ttl():
    now = [0.0]
    sessions = SessionStore(ttl_seconds=10, max_messages=20, clock=lambda: now[0])
    sessions.append("s", {"role": "user", "content": "a"})

    now[0] = 11.0

    assert sessions.history("s") == []


def test_session_store_keeps_only_recent_messages():
    sessions = SessionStore(ttl_seconds=10, max_messages=3, clock=lambda: 0.0)

    for i in range(5):
        sessions.append("s", {"role": "user", "content": str(i)})

    assert [m["content"] for m in sessions.history("s")] == ["2", "3", "4"]
