from datetime import UTC, datetime

from app.prompt import (
    DISCLAIMER,
    NO_DATA_MESSAGE,
    OUT_OF_AREA_MESSAGE,
    build_system_prompt,
)

FIXED_NOW = datetime(2026, 10, 4, 8, 30, tzinfo=UTC)


def test_prompt_forbids_inventing_data_and_uses_no_data_message():
    prompt = build_system_prompt(FIXED_NOW)

    assert "Use ONLY facts returned by your tools" in prompt
    assert f'"{NO_DATA_MESSAGE}"' in prompt


def test_prompt_requires_advice_only_from_safety_guide():
    prompt = build_system_prompt(FIXED_NOW)

    assert "All advice and steps must come from the safety guide" in prompt
    assert "do not give advice from your own knowledge" in prompt
    assert "add no steps of your own" in prompt


def test_prompt_requires_source_and_stale_marking():
    prompt = build_system_prompt(FIXED_NOW)

    assert "source and update time" in prompt
    assert "dane sprzed X godz." in prompt
    assert "older than 3 hours" in prompt


def test_prompt_requires_before_during_after_sections():
    prompt = build_system_prompt(FIXED_NOW)

    for key in ('"situation"', '"before"', '"during"', '"after"'):
        assert key in prompt


def test_prompt_limits_scope_to_krakow_with_fixed_message():
    prompt = build_system_prompt(FIXED_NOW)

    assert f'"{OUT_OF_AREA_MESSAGE}"' in prompt
    assert "in_krakow: false" in prompt


def test_prompt_limits_off_topic_to_two_sentences():
    prompt = build_system_prompt(FIXED_NOW)

    assert "at most 2 sentences" in prompt
    assert '"off_topic"' in prompt


def test_prompt_handles_emergency_and_services_disclaimer():
    prompt = build_system_prompt(FIXED_NOW)

    assert "Dzwoń 112" in prompt
    assert '"emergency"' in prompt
    assert DISCLAIMER in prompt
    assert "never replaces official services" in prompt


def test_prompt_requires_polish_answers():
    assert "Always answer in Polish" in build_system_prompt(FIXED_NOW)


def test_prompt_contains_current_time_in_krakow():
    # 08:30 UTC is 10:30 in Kraków (CEST)
    assert "2026-10-04 10:30" in build_system_prompt(FIXED_NOW)
