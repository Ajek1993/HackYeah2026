"""Simulated crisis scenarios for the presentation (Demo tab).

Each scenario provides rows in the same shape as app.repo returns, so the
endpoints map them with app.mapping exactly like real readings. Timestamps are
relative to the activation time, so simulated data is never stale.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.mapping import SOURCES

Row = dict[str, Any]
# Air attack alarms come from the state warning system, not from IMGW
RCB = ("RCB", "https://www.gov.pl/web/rcb")

# Real IMGW gauges and thresholds, so the numbers look familiar on the map
BIELANY = {
    "station_id": "150190340",
    "name": "Kraków-Bielany",
    "river": "Wisła",
    "lat": 50.0408,
    "lon": 19.8425,
    "warning_level_cm": 370,
    "alarm_level_cm": 520,
}
LAGIEWNIKI = {
    "station_id": "150190350",
    "name": "Kraków-Łagiewniki",
    "river": "Wilga",
    "lat": 50.0187,
    "lon": 19.9351,
    "warning_level_cm": None,
    "alarm_level_cm": None,
}
CALM_AIR = {
    "provider": "gios",
    "station_id": "400",
    "station_name": "Kraków, Aleja Krasińskiego",
    "index_level": "good",
    "index_label": "Dobry",
    "pm25": 9.0,
    "pm10": 18.0,
}


@dataclass(frozen=True)
class ScenarioData:
    updated_at: datetime
    warnings: list[Row]
    water: list[Row]
    outages: list[Row]
    air: Row
    warnings_source: tuple[str, str] = SOURCES["imgw"]


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    build: Callable[[datetime], ScenarioData] = field(repr=False)


def _water(now: datetime, bielany_cm: int, status: str, wilga_cm: int) -> list[Row]:
    return [
        {**BIELANY, "water_level_cm": bielany_cm, "level_status": status, "measured_at": now},
        {**LAGIEWNIKI, "water_level_cm": wilga_cm, "level_status": None, "measured_at": now},
    ]


def _air(now: datetime) -> Row:
    return {**CALM_AIR, "measured_at": now, "last_seen_at": now}


def _warning(
    now: datetime, key: str, kind: str, severity: int, title: str, body: str, area: str, hours: int
) -> Row:
    return {
        "warning_key": f"demo:{key}",
        "kind": kind,
        "title": title,
        "severity": severity,
        "body": body,
        "area_descriptions": [area],
        "valid_from": now - timedelta(hours=1),
        "valid_to": now + timedelta(hours=hours),
        "geometry": None,
    }


def _outage(now: datetime, key: str, area: str, lat: float, lon: float, hours: int) -> Row:
    return {
        "id": f"demo:{key}",
        "outage_kind": "nieplanowane",
        "message": area,
        "start_at": now - timedelta(minutes=40),
        "end_at": now + timedelta(hours=hours),
        "lat": lat,
        "lon": lon,
        "location_precision": "street",
    }


def flood(now: datetime) -> ScenarioData:
    return ScenarioData(
        updated_at=now,
        warnings=[
            _warning(
                now,
                "flood-hydro",
                "flood",
                3,
                "Wezbranie z przekroczeniem stanów alarmowych",
                "Prognozowany dalszy wzrost stanu Wisły w Krakowie powyżej stanu alarmowego. "
                "Możliwe podtopienia terenów nadrzecznych, w szczególności Dębnik, "
                "Podgórza i Nowej Huty.",
                "małopolskie, zlewnia Wisły od ujścia Przemszy do ujścia Raby",
                36,
            ),
            _warning(
                now,
                "flood-rain",
                "storm",
                2,
                "Intensywne opady deszczu",
                "Prognozowana suma opadów do 90 mm w ciągu doby.",
                "małopolskie, Kraków",
                24,
            ),
        ],
        water=_water(now, bielany_cm=585, status="alarmowy", wilga_cm=310),
        outages=[
            _outage(
                now,
                "flood-1",
                "Kraków, Dębniki: ul. Konopnickiej, ul. Zielna",
                50.0480,
                19.9300,
                12,
            ),
        ],
        air=_air(now),
    )


def power_outage(now: datetime) -> ScenarioData:
    return ScenarioData(
        updated_at=now,
        warnings=[
            _warning(
                now,
                "power-wind",
                "wind",
                2,
                "Silny wiatr",
                "Porywy wiatru do 100 km/h. Możliwe uszkodzenia linii energetycznych.",
                "małopolskie, Kraków",
                12,
            ),
        ],
        water=_water(now, bielany_cm=160, status="normalny", wilga_cm=92),
        outages=[
            _outage(
                now,
                "power-1",
                "Kraków, Nowa Huta: os. Centrum A-E, os. Zgody",
                50.0717,
                20.0377,
                18,
            ),
            _outage(
                now,
                "power-2",
                "Kraków, Krowodrza: ul. Królewska, ul. Kazimierza Wielkiego",
                50.0745,
                19.9200,
                12,
            ),
            _outage(
                now,
                "power-3",
                "Kraków, Podgórze: ul. Kalwaryjska, ul. Wielicka 1-120",
                50.0420,
                19.9530,
                24,
            ),
        ],
        air=_air(now),
    )


def bomb_threat(now: datetime) -> ScenarioData:
    return ScenarioData(
        updated_at=now,
        warnings=[
            _warning(
                now,
                "bomb-alert",
                "bomb_threat",
                3,
                "Alarm o zagrożeniu atakiem z powietrza",
                "Ogłoszono alarm dla Krakowa. Niezwłocznie udaj się do najbliższego miejsca "
                "schronienia lub ukrycia i postępuj zgodnie z poleceniami służb.",
                "Kraków",
                2,
            ),
        ],
        water=_water(now, bielany_cm=160, status="normalny", wilga_cm=92),
        outages=[],
        air=_air(now),
        warnings_source=RCB,
    )


SCENARIOS: dict[str, Scenario] = {
    s.id: s
    for s in (
        Scenario("flood", "Powódź", flood),
        Scenario("power_outage", "Brak prądu", power_outage),
        Scenario("bomb_threat", "Atak bombowy", bomb_threat),
    )
}
