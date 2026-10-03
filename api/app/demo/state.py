"""The active demo scenario, kept in the memory of the single `api` process.

Activation switches the data endpoints for every client, so the scenario
expires on its own after `DEMO_TTL_MINUTES` (audit X5).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends

from app.config import settings
from app.demo.scenarios import SCENARIOS, Scenario, ScenarioData


@dataclass(frozen=True)
class ActiveScenario:
    scenario: Scenario
    data: ScenarioData
    expires_at: datetime

    @property
    def id(self) -> str:
        return self.scenario.id


class DemoState:
    def __init__(self, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._clock = clock
        self._active: ActiveScenario | None = None

    def activate(self, scenario_id: str, ttl: timedelta) -> ActiveScenario:
        now = self._clock()
        scenario = SCENARIOS[scenario_id]
        self._active = ActiveScenario(scenario, scenario.build(now), now + ttl)
        return self._active

    def deactivate(self) -> None:
        self._active = None

    def current(self) -> ActiveScenario | None:
        if self._active is not None and self._clock() >= self._active.expires_at:
            self._active = None
        return self._active


demo_state = DemoState()


def get_demo_state() -> DemoState:
    return demo_state


def get_active_scenario(
    state: Annotated[DemoState, Depends(get_demo_state)],
) -> ActiveScenario | None:
    # A scenario left in memory never leaks out once the demo flag is off
    return state.current() if settings.demo_mode else None


ScenarioDep = Annotated[ActiveScenario | None, Depends(get_active_scenario)]
