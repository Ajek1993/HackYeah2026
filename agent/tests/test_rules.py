from unittest.mock import MagicMock

import httpx
import pytest
from openai import APITimeoutError

from app.llm import GLMClient
from app.prompt import EMERGENCY_NO_GUIDE_MESSAGE, OUT_OF_AREA_MESSAGE
from app.session import SessionStore
from app.tools import ToolResult
from tests.test_chat import (
    FakeLLM,
    FakeTools,
    final_json,
    imgw_result,
    llm_message,
    post,
    tool_call,
)


def geocode_result(*, found=True, in_krakow=True) -> ToolResult:
    payload = {"query": "x", "found": found, "in_krakow": in_krakow}
    return ToolResult(content="{}", payload=payload)


def failing_llm() -> GLMClient:
    """Real GLMClient whose SDK call times out."""
    openai_mock = MagicMock()
    request = httpx.Request("POST", "https://example.test/chat/completions")
    openai_mock.chat.completions.create.side_effect = APITimeoutError(request=request)
    return GLMClient(openai_mock)


def test_geocode_outside_krakow_returns_fixed_message_without_another_round(make_client):
    llm = FakeLLM(llm_message(tool_calls=[tool_call("geocode", {"query": "Skawina"})]))
    tools = FakeTools({"geocode": geocode_result(in_krakow=False)})

    body = post(make_client(llm, tools), "Czy w Skawinie grozi zalanie?").json()

    assert body["answer"] == OUT_OF_AREA_MESSAGE
    assert body["out_of_area"] is True
    assert body["sections"] is None
    assert body["sources"] == []
    assert body["disclaimer"] is None
    assert len(llm.calls) == 1  # no extra model round after the geocode result


def test_geocode_in_krakow_continues_normally(make_client):
    llm = FakeLLM(
        llm_message(tool_calls=[tool_call("geocode", {"query": "Testowa 1, Kraków"})]),
        llm_message(final_json(answer="Spokojnie")),
    )
    tools = FakeTools({"geocode": geocode_result(in_krakow=True)})

    body = post(make_client(llm, tools), "Pytanie").json()

    assert body["answer"] == "Spokojnie"
    assert body["out_of_area"] is False


def test_place_in_krakow_wins_over_place_outside(make_client):
    llm = FakeLLM(
        llm_message(
            tool_calls=[
                tool_call("geocode", {"query": "Skawina"}, "call-1"),
                tool_call("geocode", {"query": "Testowa 1, Kraków"}, "call-2"),
            ]
        ),
        llm_message(final_json(answer="Porównanie")),
    )

    class TwoPlaces(FakeTools):
        def execute(self, name, arguments):
            self.calls.append((name, arguments))
            return geocode_result(in_krakow="Testowa" in arguments)

    body = post(make_client(llm, TwoPlaces()), "Pytanie").json()

    assert body["answer"] == "Porównanie"
    assert body["out_of_area"] is False


def test_unknown_place_is_not_treated_as_outside_krakow(make_client):
    llm = FakeLLM(
        llm_message(tool_calls=[tool_call("geocode", {"query": "Nieistniejąca"})]),
        llm_message(final_json(answer="Proszę doprecyzować adres")),
    )
    tools = FakeTools({"geocode": geocode_result(found=False, in_krakow=None)})

    body = post(make_client(llm, tools), "Pytanie").json()

    assert body["answer"] == "Proszę doprecyzować adres"
    assert body["out_of_area"] is False


def test_model_out_of_area_flag_forces_fixed_message(make_client):
    llm = FakeLLM(llm_message(final_json(answer="Inny tekst o Skawinie", out_of_area=True)))
    tools = FakeTools({"get_warnings": imgw_result()})

    body = post(make_client(llm, tools), "Pytanie").json()

    assert body["answer"] == OUT_OF_AREA_MESSAGE
    assert body["sections"] is None


def test_out_of_area_wins_over_off_topic(make_client):
    llm = FakeLLM(llm_message(final_json(out_of_area=True, off_topic=True)))

    body = post(make_client(llm), "Pytanie").json()

    assert (body["out_of_area"], body["off_topic"]) == (True, False)


def guide_result(data) -> ToolResult:
    return ToolResult(content="{}", payload={"source": "Poradnik", "data": data})


def emergency_turns():
    return FakeLLM(
        llm_message(tool_calls=[tool_call("get_guide", {"topic": "flood"})]),
        llm_message(final_json(answer="Dzwoń 112. Kroki z poradnika.", emergency=True)),
    )


def test_life_threat_with_guide_keeps_model_answer(make_client):
    tools = FakeTools({"get_guide": guide_result({"topic": "flood", "during": ["krok"]})})

    body = post(make_client(emergency_turns(), tools), "Woda wlewa się do piwnicy").json()

    assert body["emergency"] is True
    assert body["answer"] == "Dzwoń 112. Kroki z poradnika."
    assert body["disclaimer"] is not None


@pytest.mark.parametrize(
    "guide",
    [
        None,  # api unreachable -> error, no payload
        guide_result(None),  # no cached guide -> data: null
    ],
)
def test_life_threat_without_guide_returns_only_112_and_rcb(make_client, guide):
    tools = FakeTools({"get_guide": guide} if guide else {})

    body = post(make_client(emergency_turns(), tools), "Woda wlewa się do piwnicy").json()

    assert body["emergency"] is True
    assert body["answer"] == EMERGENCY_NO_GUIDE_MESSAGE
    assert body["sections"] is None


def test_life_threat_without_guide_call_returns_only_112_and_rcb(make_client):
    llm = FakeLLM(llm_message(final_json(answer="Dzwoń 112. Własne rady.", emergency=True)))

    body = post(make_client(llm), "Pożar w kuchni!").json()

    assert body["answer"] == EMERGENCY_NO_GUIDE_MESSAGE


def test_llm_timeout_returns_503_agent_unavailable(make_client):
    client = make_client(failing_llm())

    response = post(client, "Pytanie")

    assert response.status_code == 503
    assert response.json() == {
        "error": "agent_unavailable",
        "message": "Agent chwilowo niedostępny",
    }


def test_failed_question_is_not_stored_in_session(make_client):
    sessions = SessionStore(ttl_seconds=60, max_messages=20)
    post(make_client(failing_llm(), sessions=sessions), "Pytanie")

    assert sessions.history("s-1") == []
