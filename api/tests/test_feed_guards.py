from unittest.mock import MagicMock, patch

import requests

from app.sources import tauron
from app.sources.guards import safe_to_deactivate
from app.sources.imgw import fetch_imgw_warnings


def cursor_with_active(count: int) -> MagicMock:
    cur = MagicMock()
    cur.fetchone.return_value = {"n": count}
    return cur


def test_normal_feed_may_deactivate_missing_rows():
    assert safe_to_deactivate(cursor_with_active(100), "shelters", 95) is True


def test_truncated_feed_keeps_rows_active():
    assert safe_to_deactivate(cursor_with_active(3000), "shelters", 400) is False


def test_first_load_may_deactivate():
    assert safe_to_deactivate(cursor_with_active(0), "hydro_stations", 10) is True


@patch("app.sources.imgw.get_conn")
@patch("app.sources.imgw.requests.get")
def test_explicit_no_warnings_deactivates_old_ones(mock_get, mock_conn):
    response = MagicMock(status_code=200)
    response.json.return_value = {"message": "Brak ostrzeżeń"}
    mock_get.return_value = response
    cur = MagicMock()
    cur.rowcount = 4
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    mock_conn.return_value = conn

    result = fetch_imgw_warnings.apply().get(timeout=10)

    assert result["hydro"] == {"status": "no_warnings", "count": 0, "deactivated": 4}
    sql = cur.execute.call_args_list[0].args[0]
    assert "is_active = false" in sql


@patch("app.sources.imgw.get_conn")
@patch("app.sources.imgw.requests.get")
def test_source_error_does_not_touch_warnings(mock_get, mock_conn):
    mock_get.side_effect = requests.ConnectionError("down")

    result = fetch_imgw_warnings.apply().get(timeout=10)

    assert result["hydro"]["status"] == "error"
    mock_conn.assert_not_called()


def test_tauron_coordinates_are_validated_before_wkt():
    item = {
        "Coordinates": [
            {"lat": 50.06, "lng": 19.94},
            {"lat": "50.07", "lng": "19.95"},
            {"lat": "1 2), POLYGON((0 0", "lng": 19.9},
            {"lat": 0.0, "lng": 0.0},
            "not a dict",
        ],
        "Center": {"lat": "50.06); DROP", "lng": 19.94},
    }

    assert tauron._build_geom_wkt(item) == "SRID=4326;MULTIPOINT(19.94 50.06, 19.95 50.07)"
    assert tauron._build_center_wkt(item) is None


def test_tauron_center_outside_poland_is_dropped():
    assert tauron._build_center_wkt({"Center": {"lat": 48.0, "lng": 2.35}}) is None
    assert tauron._build_center_wkt({"Center": {"lat": 50.06, "lng": 19.94}}) == (
        "SRID=4326;POINT(19.94 50.06)"
    )
