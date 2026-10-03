import logging
from datetime import UTC, datetime, timedelta

import pytest

from app import mapping
from app.envelope import envelope, is_stale, iso
from app.logging_filters import StripQueryString
from app.repo import KRAKOW_CATCHMENTS
from app.sources import airly, boundary, gios

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


# --- envelope -------------------------------------------------------------


def test_envelope_marks_data_older_than_three_hours_as_stale():
    assert is_stale(NOW - timedelta(hours=3, minutes=1), NOW) is True
    assert is_stale(NOW - timedelta(hours=2, minutes=59), NOW) is False


def test_envelope_without_fetch_has_no_data():
    body = envelope("IMGW", None, None, [1, 2], now=NOW)

    assert body["data"] is None
    assert body["is_stale"] is False


def test_iso_uses_krakow_time():
    assert iso(datetime(2026, 10, 3, 15, 7, tzinfo=UTC)) == "2026-10-03T17:07:00+02:00"
    assert iso(datetime(2026, 1, 3, 15, 7, tzinfo=UTC)) == "2026-01-03T16:07:00+01:00"
    assert iso(None) is None


def test_static_envelope_is_never_stale():
    body = envelope("Poradnik", None, NOW - timedelta(days=300), {"a": 1}, now=NOW, static=True)

    assert body["is_stale"] is False
    assert body["data"] == {"a": 1}


# --- mapping --------------------------------------------------------------


@pytest.mark.parametrize(
    ("title", "kind"),
    [
        ("Susza hydrologiczna", "drought"),
        ("Wezbranie z przekroczeniem stanów ostrzegawczych", "flood"),
        ("Burze z gradem", "storm"),
        ("Silny wiatr", "wind"),
        ("Upał", "heat"),
        ("Przymrozki", "frost"),
        ("Gęsta mgła", "other"),
    ],
)
def test_warning_kind(title, kind):
    assert mapping.warning_kind(title) == kind


@pytest.mark.parametrize(
    ("severity", "level"), [(-1, 1), (None, 1), (1, 1), (2, 2), (3, 3), (5, 3)]
)
def test_warning_level(severity, level):
    assert mapping.warning_level(severity) == level


@pytest.mark.parametrize(
    ("count", "word"),
    [
        (1, "ostrzeżenie"),
        (2, "ostrzeżenia"),
        (4, "ostrzeżenia"),
        (5, "ostrzeżeń"),
        (12, "ostrzeżeń"),
        (22, "ostrzeżenia"),
    ],
)
def test_polish_plural(count, word):
    assert mapping.plural(count, "ostrzeżenie", "ostrzeżenia", "ostrzeżeń") == word


def test_shelter_type():
    assert mapping.shelter_type({"name": "Schron nr 4", "object_type": None}) == "shelter"
    assert (
        mapping.shelter_type({"name": "Miejsce ochronne", "object_type": "Obiekt"})
        == "hiding_place"
    )


def test_water_level_hides_placeholder_river():
    row = {"name": "Jezioro", "river": "-", "lat": 1, "lon": 2, "level_status": "alarmowy"}

    item = mapping.water_level(row)

    assert item["river"] is None
    assert item["status"] == "alarm"


def test_krakow_catchments_cover_the_city_section_of_the_vistula():
    joined = " ".join(KRAKOW_CATCHMENTS)
    assert "Wisła od ujścia Przemszy do ujścia Raby" in joined
    assert "%Rudawy%" in KRAKOW_CATCHMENTS


# --- access log privacy ---------------------------------------------------


def test_access_log_filter_drops_query_string():
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        0,
        '%s - "%s %s HTTP/%s" %d',
        ("1.2.3.4:5", "GET", "/geocode?q=Testowa+1%2C+Krak%C3%B3w", "1.1", 200),
        None,
    )

    StripQueryString().filter(record)

    assert record.getMessage() == '1.2.3.4:5 - "GET /geocode HTTP/1.1" 200'


def test_access_log_filter_ignores_other_records():
    record = logging.LogRecord("x", logging.INFO, "", 0, "plain %s", ("text",), None)

    assert StripQueryString().filter(record) is True
    assert record.getMessage() == "plain text"


# --- GIOŚ -----------------------------------------------------------------


def test_gios_station_parser_handles_misencoded_coordinate_keys():
    stations = [
        {
            "Identyfikator stacji": 400,
            "Nazwa stacji": "Kraków, Aleja Krasińskiego",
            "WGS84 Ď† N": "50.057678",
            "WGS84 \xce\xbb E": "19.926189",
            "Nazwa miasta": "Kraków",
        },
        {
            "Identyfikator stacji": 11,
            "Nazwa miasta": "Czerniawa",
            "WGS84 φ N": "50.9",
            "WGS84 λ E": "15.3",
        },
        {"Identyfikator stacji": 12, "Nazwa miasta": "Kraków", "WGS84 φ N": "", "WGS84 λ E": None},
    ]

    assert gios.krakow_stations(stations) == [
        {"id": "400", "name": "Kraków, Aleja Krasińskiego", "lat": 50.057678, "lon": 19.926189}
    ]


def test_gios_index_parser():
    payload = {
        "AqIndex": {
            "Wartość indeksu": 1,
            "Nazwa kategorii indeksu": "Dobry",
            # GIOŚ really truncates this key after "wskaźnika st"
            "Data danych źródłowych, z których policzono wartość indeksu dla wskaźnika st": (  # noqa: E501
                "2026-10-03 17:00:00"
            ),
        }
    }

    level, label, measured = gios.parse_index(payload)

    assert (level, label) == ("good", "Dobry")
    assert measured.isoformat() == "2026-10-03T17:00:00+02:00"


def test_gios_index_without_value():
    assert gios.parse_index({"AqIndex": {"Wartość indeksu": None}})[0] is None


def test_gios_latest_value_skips_empty_hours():
    payload = {
        "Lista danych pomiarowych": [{"Wartość": None}, {"Wartość": 15.8}, {"Wartość": 16.6}]
    }

    assert gios.latest_value(payload) == 15.8


# --- Airly ----------------------------------------------------------------


def test_airly_parser():
    installation = {
        "id": 123,
        "location": {"latitude": 50.06, "longitude": 19.94},
        "address": {"city": "Kraków", "street": "Testowa"},
    }
    payload = {
        "current": {
            "tillDateTime": "2026-10-03T15:00:00.000Z",
            "indexes": [{"name": "AIRLY_CAQI", "level": "MEDIUM", "description": "Umiarkowanie"}],
            "values": [{"name": "PM25", "value": 21.5}, {"name": "PM10", "value": 30.1}],
        }
    }

    reading = airly.parse_measurement(installation, payload)

    assert reading["name"] == "Kraków, Testowa"
    assert reading["level"] == "moderate"
    assert (reading["pm25"], reading["pm10"]) == (21.5, 30.1)
    assert reading["measured_at"].isoformat() == "2026-10-03T15:00:00+00:00"


def test_airly_is_skipped_without_api_key(monkeypatch):
    monkeypatch.setattr(airly.settings, "airly_api_key", "")

    assert airly.fetch_airly_air_quality.apply().get() == {
        "status": "skipped",
        "reason": "AIRLY_API_KEY not set",
    }


# --- boundary -------------------------------------------------------------


def test_boundary_extracts_administrative_polygon():
    polygon = {
        "type": "Polygon",
        "coordinates": [[[19.8, 50.0], [20.1, 50.0], [20.1, 50.1], [19.8, 50.0]]],
    }
    payload = {
        "features": [
            {"properties": {"category": "place"}, "geometry": {"type": "Point"}},
            {"properties": {"category": "boundary"}, "geometry": polygon},
        ]
    }

    assert boundary._extract_polygon(payload) == polygon
    assert boundary._extract_polygon({"features": []}) is None
