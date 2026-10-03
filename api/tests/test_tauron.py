from unittest.mock import MagicMock, patch

import pytest
import requests

from app.sources.tauron import (
    _build_center_wkt,
    _build_geom_wkt,
    _is_in_krakow,
    _item_hash,
    fetch_tauron_outages,
)

# ---------------------------------------------------------------------------
# Fixtures — Tauron API items
# ---------------------------------------------------------------------------


def _make_item(**overrides):
    base = {
        "OutageId": "11111111-1111-1111-1111-111111111111",
        "StartDate": "2026-10-03T06:00:00Z",
        "EndDate": "2026-10-03T14:00:00Z",
        "TypeId": 1,
        "Message": "Kraków ul. Testowa 1-10",
        "Modified": "2026-10-02T10:00:00Z",
        "IdsWWW": [100, 200],
        "AddressPointIds": [9000, 9001],
        "CoordinatesType": 2,
        "IsActive": True,
        "Coordinates": [{"lat": 50.06, "lng": 19.94}],
        "Center": {"lat": 50.06, "lng": 19.94},
        "Radius": 500.0,
    }
    base.update(overrides)
    return base


KRAKOW_CENTER_ITEM = _make_item()

OUTSIDE_KRAKOW_ITEM = _make_item(
    OutageId="22222222-2222-2222-2222-222222222222",
    Message="Radlin ul. Inna 5-15",
    Coordinates=[{"lat": 50.05, "lng": 18.45}],
    Center={"lat": 50.05, "lng": 18.45},
)

NO_COORDS_BUT_KRAKOW_MSG = _make_item(
    OutageId="33333333-3333-3333-3333-333333333333",
    Coordinates=[],
    Center=None,
    CoordinatesType=0,
    Message="Kraków, ul. Wielicka 20-30",
)

NOWA_HUTA_MSG = _make_item(
    OutageId="44444444-4444-4444-4444-444444444444",
    Coordinates=[],
    Center=None,
    CoordinatesType=0,
    Message="Nowa Huta, os. Zielone 1",
)

NO_COORDS_OUTSIDE = _make_item(
    OutageId="55555555-5555-5555-5555-555555555555",
    Coordinates=[],
    Center=None,
    CoordinatesType=0,
    Message="Katowice ul. Inna 1",
)

POLYGON_ITEM = _make_item(
    OutageId="66666666-6666-6666-6666-666666666666",
    Coordinates=[
        {"lat": 50.05, "lng": 19.93},
        {"lat": 50.06, "lng": 19.93},
        {"lat": 50.06, "lng": 19.95},
        {"lat": 50.05, "lng": 19.93},
    ],
    CoordinatesType=2,
)

MULTIPOINT_ITEM = _make_item(
    OutageId="77777777-7777-7777-7777-777777777777",
    Coordinates=[
        {"lat": 50.05, "lng": 19.93},
        {"lat": 50.06, "lng": 19.95},
    ],
    CoordinatesType=2,
)


# ---------------------------------------------------------------------------
# _item_hash
# ---------------------------------------------------------------------------


class TestItemHash:
    def test_deterministic(self):
        item = {"a": 1, "b": "x"}
        assert _item_hash(item) == _item_hash(item)

    def test_different_for_different_data(self):
        assert _item_hash({"a": 1}) != _item_hash({"a": 2})


# ---------------------------------------------------------------------------
# _is_in_krakow
# ---------------------------------------------------------------------------


class TestIsInKrakow:
    def test_center_inside_krakow(self):
        assert _is_in_krakow(KRAKOW_CENTER_ITEM) is True

    def test_center_outside_krakow(self):
        assert _is_in_krakow(OUTSIDE_KRAKOW_ITEM) is False

    def test_coordinates_inside_krakow(self):
        item = _make_item(Center=None, Coordinates=[{"lat": 50.06, "lng": 19.94}])
        assert _is_in_krakow(item) is True

    def test_no_coords_but_krakow_in_message(self):
        assert _is_in_krakow(NO_COORDS_BUT_KRAKOW_MSG) is True

    def test_no_coords_but_nowa_huta_in_message(self):
        assert _is_in_krakow(NOWA_HUTA_MSG) is True

    def test_no_coords_no_krakow_message(self):
        assert _is_in_krakow(NO_COORDS_OUTSIDE) is False

    def test_empty_item(self):
        assert _is_in_krakow({}) is False

    def test_message_case_insensitive(self):
        item = _make_item(
            Coordinates=[],
            Center=None,
            Message="KRAKÓW UL. WIELICKA",
        )
        assert _is_in_krakow(item) is True

    def test_krakow_without_polish_chars(self):
        item = _make_item(
            Coordinates=[],
            Center=None,
            Message="krakow ul. wielicka",
        )
        assert _is_in_krakow(item) is True

    def test_boundary_lat_min(self):
        item = _make_item(Center={"lat": 49.95, "lng": 19.90})
        assert _is_in_krakow(item) is True

    def test_boundary_lat_below_min(self):
        item = _make_item(
            Center={"lat": 49.94, "lng": 19.90},
            Coordinates=[],
            Message="",
        )
        assert _is_in_krakow(item) is False

    def test_boundary_lon_max(self):
        item = _make_item(Center={"lat": 50.05, "lng": 20.12})
        assert _is_in_krakow(item) is True

    def test_boundary_lon_above_max(self):
        item = _make_item(
            Center={"lat": 50.05, "lng": 20.13},
            Coordinates=[],
            Message="",
        )
        assert _is_in_krakow(item) is False

    def test_coordinates_with_missing_fields(self):
        item = _make_item(
            Center=None,
            Coordinates=[{"lat": None, "lng": 19.94}],
            Message="",
        )
        assert _is_in_krakow(item) is False

    def test_null_coordinates(self):
        item = _make_item(
            Center=None,
            Coordinates=None,
            Message="",
        )
        assert _is_in_krakow(item) is False


# ---------------------------------------------------------------------------
# _build_geom_wkt
# ---------------------------------------------------------------------------


class TestBuildGeomWkt:
    def test_single_point(self):
        wkt = _build_geom_wkt(_make_item(Coordinates=[{"lat": 50.06, "lng": 19.94}]))
        assert wkt == "SRID=4326;POINT(19.94 50.06)"

    def test_closed_polygon(self):
        wkt = _build_geom_wkt(POLYGON_ITEM)
        assert wkt is not None
        assert wkt.startswith("SRID=4326;POLYGON((")

    def test_multipoint(self):
        wkt = _build_geom_wkt(MULTIPOINT_ITEM)
        assert wkt is not None
        assert wkt.startswith("SRID=4326;MULTIPOINT(")

    def test_no_coordinates(self):
        assert _build_geom_wkt(_make_item(Coordinates=[])) is None

    def test_null_coordinates(self):
        assert _build_geom_wkt(_make_item(Coordinates=None)) is None

    def test_coordinates_with_missing_lat_lng(self):
        item = _make_item(Coordinates=[{"lat": None, "lng": None}])
        assert _build_geom_wkt(item) is None

    def test_three_open_points_are_multipoint(self):
        item = _make_item(
            Coordinates=[
                {"lat": 50.05, "lng": 19.93},
                {"lat": 50.06, "lng": 19.94},
                {"lat": 50.07, "lng": 19.95},
            ]
        )
        wkt = _build_geom_wkt(item)
        assert wkt.startswith("SRID=4326;MULTIPOINT(")


# ---------------------------------------------------------------------------
# _build_center_wkt
# ---------------------------------------------------------------------------


class TestBuildCenterWkt:
    def test_valid_center(self):
        wkt = _build_center_wkt(_make_item())
        assert wkt == "SRID=4326;POINT(19.94 50.06)"

    def test_null_center(self):
        assert _build_center_wkt(_make_item(Center=None)) is None

    def test_center_with_missing_lat(self):
        assert _build_center_wkt(_make_item(Center={"lat": None, "lng": 19.94})) is None

    def test_center_with_missing_lng(self):
        assert _build_center_wkt(_make_item(Center={"lat": 50.06, "lng": None})) is None


# ---------------------------------------------------------------------------
# fetch_tauron_outages task (mocked)
# ---------------------------------------------------------------------------


class TestFetchTauronOutagesTask:
    @pytest.fixture(autouse=True)
    def no_street_geocoding(self):
        # Street lookup has its own tests (test_outage_streets); keep Nominatim out of these
        with patch("app.sources.tauron.locate_streets", return_value={}) as locate:
            self.locate = locate
            yield

    def _mock_db(self, mock_conn):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {"ts": "2026-10-03T12:00:00+00:00"}
        mock_cur.rowcount = 0
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn_obj.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn_obj.__enter__ = MagicMock(return_value=mock_conn_obj)
        mock_conn_obj.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value = mock_conn_obj
        return mock_cur, mock_conn_obj

    @patch("app.sources.tauron.get_conn")
    @patch("app.sources.tauron.requests.get")
    def test_filters_to_krakow_only(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [KRAKOW_CENTER_ITEM, OUTSIDE_KRAKOW_ITEM]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_cur, _ = self._mock_db(mock_conn)

        result = fetch_tauron_outages.apply().get(timeout=10)

        assert result["total"] == 2
        assert result["krakow"] == 1

    @patch("app.sources.tauron.get_conn")
    @patch("app.sources.tauron.requests.get")
    def test_empty_response(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_cur, _ = self._mock_db(mock_conn)

        result = fetch_tauron_outages.apply().get(timeout=10)
        assert result["total"] == 0
        assert result["krakow"] == 0

    @patch("app.sources.tauron.requests.get")
    def test_http_error_retries(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("timeout")

        with pytest.raises(requests.ConnectionError):
            fetch_tauron_outages.apply().get(timeout=10)

    @patch("app.sources.tauron.get_conn")
    @patch("app.sources.tauron.requests.get")
    def test_deactivation_of_stale_entries(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [KRAKOW_CENTER_ITEM]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_cur, _ = self._mock_db(mock_conn)
        mock_cur.rowcount = 3

        result = fetch_tauron_outages.apply().get(timeout=10)
        assert result["deactivated"] == 3

    @patch("app.sources.tauron.get_conn")
    @patch("app.sources.tauron.requests.get")
    def test_conn_closed_after_success(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [KRAKOW_CENTER_ITEM]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _, mock_conn_obj = self._mock_db(mock_conn)

        fetch_tauron_outages.apply().get(timeout=10)
        mock_conn_obj.close.assert_called_once()

    @patch("app.sources.tauron.get_conn")
    @patch("app.sources.tauron.requests.get")
    def test_message_fallback_krakow(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [NO_COORDS_BUT_KRAKOW_MSG]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        self._mock_db(mock_conn)

        result = fetch_tauron_outages.apply().get(timeout=10)
        assert result["krakow"] == 1

    @patch("app.sources.tauron.get_conn")
    @patch("app.sources.tauron.requests.get")
    def test_request_uses_5_day_window(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        self._mock_db(mock_conn)

        fetch_tauron_outages.apply().get(timeout=10)

        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert "fromDate" in params
        assert "toDate" in params

    @patch("app.sources.tauron.get_conn")
    @patch("app.sources.tauron.requests.get")
    def test_district_outage_gets_the_geocoded_street(self, mock_get, mock_conn):
        item = _make_item(Message="Kraków ul. Litewska 23", CoordinatesType=3)
        exact = _make_item(OutageId="22222222-2222-2222-2222-222222222222")
        mock_resp = MagicMock()
        mock_resp.json.return_value = [item, exact]
        mock_get.return_value = mock_resp
        mock_cur, _ = self._mock_db(mock_conn)
        self.locate.return_value = {"Kraków ul. Litewska 23": (50.0712, 19.9205)}

        fetch_tauron_outages.apply().get(timeout=10)

        # Only the outage without exact coordinates is looked up
        assert list(self.locate.call_args.args[1]) == ["Kraków ul. Litewska 23"]
        inserted = [c.args[1] for c in mock_cur.execute.call_args_list if len(c.args) > 1]
        streets = [params["street_center"] for params in inserted if "street_center" in params]
        assert streets == ["SRID=4326;POINT(19.9205 50.0712)", None]
