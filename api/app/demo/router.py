import hmac
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import settings
from app.demo.scenarios import SCENARIOS
from app.demo.state import ActiveScenario, DemoState, get_demo_state
from app.envelope import iso


def require_demo_mode() -> None:
    # Outside the presentation build the demo does not exist at all
    if not settings.demo_mode:
        raise HTTPException(404, "Not Found")


def require_demo_token(request: Request) -> None:
    # Switching scenarios affects every client, so it needs the admin token (audit X5)
    token = request.headers.get("X-Demo-Token", "")
    if not settings.demo_admin_token or not hmac.compare_digest(token, settings.demo_admin_token):
        raise HTTPException(403, "Brak uprawnień do sterowania trybem demo.")


router = APIRouter(prefix="/demo", dependencies=[Depends(require_demo_mode)])

StateDep = Annotated[DemoState, Depends(get_demo_state)]


@router.get("/scenarios")
def scenarios() -> list[dict]:
    return [{"id": s.id, "title": s.title} for s in SCENARIOS.values()]


def _status(current: ActiveScenario | None) -> dict:
    if current is None:
        return {"active": None, "expires_at": None}
    return {"active": current.id, "expires_at": iso(current.expires_at)}


@router.get("/active")
def active_scenario(state: StateDep) -> dict:
    return _status(state.current())


@router.post("/activate/{scenario_id}", dependencies=[Depends(require_demo_token)])
def activate(scenario_id: str, state: StateDep) -> dict:
    if scenario_id not in SCENARIOS:
        raise HTTPException(404, "Nieznany scenariusz.")
    return _status(state.activate(scenario_id, timedelta(minutes=settings.demo_ttl_minutes)))


@router.post("/deactivate", dependencies=[Depends(require_demo_token)])
def deactivate(state: StateDep) -> dict:
    state.deactivate()
    return _status(None)
