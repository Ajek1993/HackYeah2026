import json
from unittest.mock import MagicMock, patch, call

import pytest
import requests

from app.sources.imgw import (
    _flatten_area_codes,
    _flatten_area_descriptions,
    _flatten_voivodeships,
    _hydro_warning_key,
    _json_hash,
    _upsert_warnings,
    fetch_imgw_hydro,
    fetch_imgw_warnings,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

HYDRO_STATION = {
    "id_stacji": "149200090",
    "stacja": "Dobczyce",
    "rzeka": "Raba",
    "wojewodztwo": "małopolskie",
    "lon": "20.0861",
    "lat": "49.8836",
    "stan_wody": "227",
    "stan_ostrzegawczy": "600",
    "stan_alarmowy": "690",
    "przeplyw": "4.14",
    "przeplyw_data": "2026-10-03 10:50:00",
    "temperatura_wody": None,
    "temperatura_wody_data_pomiaru": None,
    "stan_wody_data_pomiaru": "2026-10-03 12:50:00",
}

HYDRO_STATION_NO_COORDS = {
    "id_stacji": "999",
    "stacja": "Brak",
    "rzeka": "-",
    "wojewodztwo": "test",
    "lon": "abc",
    "lat": "xyz",
    "stan_wody": "100",
}

HYDRO_STATION_NULL_VALUES = {
    "id_stacji": "888",
    "stacja": "Null station",
    "rzeka": "-",
    "wojewodztwo": "test",
    "lon": "20.0",
    "lat": "50.0",
    "stan_wody": None,
    "stan_ostrzegawczy": None,
    "stan_alarmowy": None,
    "przeplyw": None,
    "przeplyw_data": None,
    "temperatura_wody": None,
    "stan_wody_data_pomiaru": None,
}

HYDRO_STATION_EMPTY_STRINGS = {
    "id_stacji": "777",
    "stacja": "Empty strings",
    "rzeka": "-",
    "wojewodztwo": "test",
    "lon": "20.0",
    "lat": "50.0",
    "stan_wody": "",
    "stan_ostrzegawczy": "",
    "stan_alarmowy": "",
    "przeplyw": "",
    "przeplyw_data": "",
    "temperatura_wody": "",
    "stan_wody_data_pomiaru": "",
}

HYDRO_WARNING = {
    "opublikowano": "2026-04-17 08:45:56",
    "stopień": "-1",
    "data_od": "2026-04-17 08:46:51",
    "data_do": "9999-12-31 23:59:59",
    "prawdopodobienstwo": "90",
    "numer": "21",
    "biuro": "Biuro Prognoz Hydrologicznych we Wrocławiu",
    "zdarzenie": "Susza hydrologiczna",
    "przebieg": "Niskie przepływy wody",
    "komentarz": "Ostrzeżenie wydawane...",
    "obszary": [
        {
            "wojewodztwo": "łódzkie",
            "opis": "łódzkie, Warta górna, susza",
            "kod_zlewni": ["Z_P_LD_1816", "R_P_LD_18_A"],
        },
        {
            "wojewodztwo": "śląskie",
            "opis": "śląskie, Warta górna, susza",
            "kod_zlewni": ["Z_P_SL_18_A"],
        },
    ],
}

METEO_WARNING = {
    "id": "Po20261003084735706",
    "nazwa_zdarzenia": "Gęsta mgła",
    "stopien": "1",
    "prawdopodobienstwo": "80",
    "obowiazuje_od": "2026-10-03 22:00:00",
    "obowiazuje_do": "2026-10-04 10:00:00",
    "opublikowano": "2026-10-03 10:47:00",
    "tresc": "Prognozuje się gęste mgły",
    "komentarz": "Brak.",
    "biuro": "Centralne Biuro Prognoz Meteorologicznych",
    "teryt": ["1261", "1206"],
}


# ---------------------------------------------------------------------------
# _json_hash
# ---------------------------------------------------------------------------

class TestJsonHash:
    def test_deterministic(self):
        assert _json_hash({"a": 1}) == _json_hash({"a": 1})

    def test_different_data(self):
        assert _json_hash({"a": 1}) != _json_hash({"a": 2})

    def test_order_independent(self):
        assert _json_hash({"b": 2, "a": 1}) == _json_hash({"a": 1, "b": 2})


# ---------------------------------------------------------------------------
# _hydro_warning_key
# ---------------------------------------------------------------------------

class TestHydroWarningKey:
    def test_format(self):
        key = _hydro_warning_key(HYDRO_WARNING)
        assert key.startswith("hydro:2026:")
        assert key.endswith(":21")
        parts = key.split(":")
        assert len(parts) == 4
        assert len(parts[2]) == 8  # md5[:8]

    def test_different_biuro_different_key(self):
        w1 = {**HYDRO_WARNING, "biuro": "Biuro A"}
        w2 = {**HYDRO_WARNING, "biuro": "Biuro B"}
        assert _hydro_warning_key(w1) != _hydro_warning_key(w2)

    def test_same_number_same_biuro_same_key(self):
        assert _hydro_warning_key(HYDRO_WARNING) == _hydro_warning_key(HYDRO_WARNING)

    def test_missing_fields(self):
        key = _hydro_warning_key({})
        assert key.startswith("hydro:0000:")
        assert key.endswith(":0")


# ---------------------------------------------------------------------------
# _flatten helpers
# ---------------------------------------------------------------------------

class TestFlattenAreaCodes:
    def test_flattens_all_codes(self):
        codes = _flatten_area_codes(HYDRO_WARNING)
        assert codes == ["Z_P_LD_1816", "R_P_LD_18_A", "Z_P_SL_18_A"]

    def test_empty_areas(self):
        assert _flatten_area_codes({}) == []
        assert _flatten_area_codes({"obszary": []}) == []

    def test_areas_without_kod_zlewni(self):
        item = {"obszary": [{"wojewodztwo": "test"}]}
        assert _flatten_area_codes(item) == []


class TestFlattenVoivodeships:
    def test_extracts_voivodeships(self):
        result = _flatten_voivodeships(HYDRO_WARNING)
        assert result == ["łódzkie", "śląskie"]

    def test_empty_areas(self):
        assert _flatten_voivodeships({}) == []

    def test_skips_empty_voivodeship(self):
        item = {"obszary": [{"wojewodztwo": ""}, {"wojewodztwo": "test"}]}
        assert _flatten_voivodeships(item) == ["test"]


class TestFlattenAreaDescriptions:
    def test_extracts_descriptions(self):
        result = _flatten_area_descriptions(HYDRO_WARNING)
        assert len(result) == 2
        assert "łódzkie" in result[0]

    def test_empty_areas(self):
        assert _flatten_area_descriptions({}) == []

    def test_skips_empty_description(self):
        item = {"obszary": [{"opis": ""}, {"opis": "test desc"}]}
        assert _flatten_area_descriptions(item) == ["test desc"]


# ---------------------------------------------------------------------------
# fetch_imgw_hydro task
# ---------------------------------------------------------------------------

class TestFetchImgwHydro:
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

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_successful_fetch(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [HYDRO_STATION]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_cur, _ = self._mock_db(mock_conn)

        result = fetch_imgw_hydro.apply().get(timeout=10)
        assert result["status"] == "ok"
        assert result["upserted"] == 1

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_skips_station_with_bad_coords(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [HYDRO_STATION, HYDRO_STATION_NO_COORDS]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_cur, _ = self._mock_db(mock_conn)

        result = fetch_imgw_hydro.apply().get(timeout=10)
        assert result["upserted"] == 1

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_handles_null_measurement_values(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [HYDRO_STATION_NULL_VALUES]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_cur, _ = self._mock_db(mock_conn)

        result = fetch_imgw_hydro.apply().get(timeout=10)
        assert result["status"] == "ok"
        assert result["upserted"] == 1

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_handles_empty_string_values(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [HYDRO_STATION_EMPTY_STRINGS]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_cur, _ = self._mock_db(mock_conn)

        result = fetch_imgw_hydro.apply().get(timeout=10)
        assert result["status"] == "ok"
        assert result["upserted"] == 1

    @patch("app.sources.imgw.requests.get")
    def test_non_list_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": "error"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_imgw_hydro.apply().get(timeout=10)
        assert result["status"] == "unexpected_format"

    @patch("app.sources.imgw.requests.get")
    def test_http_error_retries(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("timeout")

        with pytest.raises(Exception):
            fetch_imgw_hydro.apply().get(timeout=10)

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_deactivation_count(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [HYDRO_STATION]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_cur, _ = self._mock_db(mock_conn)
        mock_cur.rowcount = 7

        result = fetch_imgw_hydro.apply().get(timeout=10)
        assert result["deactivated"] == 7

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_conn_closed_after_success(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [HYDRO_STATION]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _, mock_conn_obj = self._mock_db(mock_conn)

        fetch_imgw_hydro.apply().get(timeout=10)
        mock_conn_obj.close.assert_called_once()

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_empty_station_list(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_cur, _ = self._mock_db(mock_conn)

        result = fetch_imgw_hydro.apply().get(timeout=10)
        assert result["status"] == "ok"
        assert result["upserted"] == 0


# ---------------------------------------------------------------------------
# fetch_imgw_warnings task
# ---------------------------------------------------------------------------

class TestFetchImgwWarnings:
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

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_successful_hydro_and_meteo(self, mock_get, mock_conn):
        hydro_resp = MagicMock()
        hydro_resp.status_code = 200
        hydro_resp.json.return_value = [HYDRO_WARNING]
        hydro_resp.raise_for_status = MagicMock()

        meteo_resp = MagicMock()
        meteo_resp.status_code = 200
        meteo_resp.json.return_value = [METEO_WARNING]
        meteo_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [hydro_resp, meteo_resp]

        mock_cur, _ = self._mock_db(mock_conn)

        result = fetch_imgw_warnings.apply().get(timeout=10)
        assert result["hydro"]["status"] == "ok"
        assert result["hydro"]["upserted"] == 1
        assert result["meteo"]["status"] == "ok"
        assert result["meteo"]["upserted"] == 1

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_404_means_no_warnings(self, mock_get, mock_conn):
        hydro_resp = MagicMock()
        hydro_resp.status_code = 404
        hydro_resp.raise_for_status = MagicMock()

        meteo_resp = MagicMock()
        meteo_resp.status_code = 200
        meteo_resp.json.return_value = [METEO_WARNING]
        meteo_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [hydro_resp, meteo_resp]

        self._mock_db(mock_conn)

        result = fetch_imgw_warnings.apply().get(timeout=10)
        assert result["hydro"]["status"] == "no_warnings"

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_message_response_means_no_warnings(self, mock_get, mock_conn):
        hydro_resp = MagicMock()
        hydro_resp.status_code = 200
        hydro_resp.json.return_value = {"message": "Brak ostrzeżeń hydrologicznych"}
        hydro_resp.raise_for_status = MagicMock()

        meteo_resp = MagicMock()
        meteo_resp.status_code = 200
        meteo_resp.json.return_value = [METEO_WARNING]
        meteo_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [hydro_resp, meteo_resp]

        self._mock_db(mock_conn)

        result = fetch_imgw_warnings.apply().get(timeout=10)
        assert result["hydro"]["status"] == "no_warnings"
        assert result["hydro"]["count"] == 0

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_http_error_on_one_source_continues(self, mock_get, mock_conn):
        mock_get.side_effect = [
            requests.ConnectionError("hydro down"),
            MagicMock(
                status_code=200,
                json=MagicMock(return_value=[METEO_WARNING]),
                raise_for_status=MagicMock(),
            ),
        ]

        self._mock_db(mock_conn)

        result = fetch_imgw_warnings.apply().get(timeout=10)
        assert result["hydro"]["status"] == "error"
        assert result["meteo"]["status"] == "ok"

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_unexpected_format_handled(self, mock_get, mock_conn):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = "not a list or dict with message"
        resp.raise_for_status = MagicMock()

        mock_get.return_value = resp
        self._mock_db(mock_conn)

        result = fetch_imgw_warnings.apply().get(timeout=10)
        assert result["hydro"]["status"] == "unexpected_format"
        assert result["meteo"]["status"] == "unexpected_format"

    @patch("app.sources.imgw.get_conn")
    @patch("app.sources.imgw.requests.get")
    def test_empty_warnings_list(self, mock_get, mock_conn):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = []
        resp.raise_for_status = MagicMock()

        mock_get.return_value = resp
        mock_cur, _ = self._mock_db(mock_conn)

        result = fetch_imgw_warnings.apply().get(timeout=10)
        assert result["hydro"]["upserted"] == 0
        assert result["meteo"]["upserted"] == 0


# ---------------------------------------------------------------------------
# _upsert_warnings — unit tests for field mapping
# ---------------------------------------------------------------------------

class TestUpsertWarningsMapping:
    def test_hydro_warning_fields(self):
        mock_cur = MagicMock()
        run_ts = "2026-10-03T12:00:00+00:00"

        _upsert_warnings(mock_cur, "hydro", [HYDRO_WARNING], run_ts)

        assert mock_cur.execute.call_count == 1
        call_args = mock_cur.execute.call_args
        params = call_args[0][1]
        assert params["source"] == "hydro"
        assert params["title"] == "Susza hydrologiczna"
        assert params["severity"] == -1
        assert params["prob"] == 90
        assert params["valid_to"] is None  # 9999-12-31 converted to None
        assert params["issuer"] == "Biuro Prognoz Hydrologicznych we Wrocławiu"
        assert params["warning_number"] == "21"
        assert params["body"] == "Niskie przepływy wody"
        assert len(params["area_codes"]) == 3
        assert len(params["voivodeships"]) == 2

    def test_meteo_warning_fields(self):
        mock_cur = MagicMock()
        run_ts = "2026-10-03T12:00:00+00:00"

        _upsert_warnings(mock_cur, "meteo", [METEO_WARNING], run_ts)

        call_args = mock_cur.execute.call_args
        params = call_args[0][1]
        assert params["key"] == "meteo:Po20261003084735706"
        assert params["source"] == "meteo"
        assert params["title"] == "Gęsta mgła"
        assert params["severity"] == 1
        assert params["prob"] == 80
        assert params["valid_from"] == "2026-10-03 22:00:00"
        assert params["valid_to"] == "2026-10-04 10:00:00"
        assert params["area_codes"] == ["1261", "1206"]
        assert params["voivodeships"] is None
        assert params["warning_number"] is None

    def test_invalid_severity_becomes_none(self):
        mock_cur = MagicMock()
        warning = {**METEO_WARNING, "stopien": "abc"}
        _upsert_warnings(mock_cur, "meteo", [warning], "ts")
        params = mock_cur.execute.call_args[0][1]
        assert params["severity"] is None

    def test_missing_probability(self):
        mock_cur = MagicMock()
        warning = {**METEO_WARNING}
        del warning["prawdopodobienstwo"]
        _upsert_warnings(mock_cur, "meteo", [warning], "ts")
        params = mock_cur.execute.call_args[0][1]
        assert params["prob"] is None

    def test_invalid_probability_becomes_none(self):
        mock_cur = MagicMock()
        warning = {**METEO_WARNING, "prawdopodobienstwo": "high"}
        _upsert_warnings(mock_cur, "meteo", [warning], "ts")
        params = mock_cur.execute.call_args[0][1]
        assert params["prob"] is None

    def test_hydro_9999_date_converted_to_none(self):
        mock_cur = MagicMock()
        _upsert_warnings(mock_cur, "hydro", [HYDRO_WARNING], "ts")
        params = mock_cur.execute.call_args[0][1]
        assert params["valid_to"] is None

    def test_meteo_normal_date_preserved(self):
        mock_cur = MagicMock()
        _upsert_warnings(mock_cur, "meteo", [METEO_WARNING], "ts")
        params = mock_cur.execute.call_args[0][1]
        assert params["valid_to"] == "2026-10-04 10:00:00"

    def test_returns_count(self):
        mock_cur = MagicMock()
        count = _upsert_warnings(mock_cur, "meteo", [METEO_WARNING, METEO_WARNING], "ts")
        assert count == 2

    def test_empty_list_returns_zero(self):
        mock_cur = MagicMock()
        count = _upsert_warnings(mock_cur, "meteo", [], "ts")
        assert count == 0

    def test_hydro_stopien_with_accent(self):
        mock_cur = MagicMock()
        warning = {**HYDRO_WARNING, "stopień": "2", "stopien": None}
        _upsert_warnings(mock_cur, "hydro", [warning], "ts")
        params = mock_cur.execute.call_args[0][1]
        assert params["severity"] == 2

    def test_hydro_stopien_without_accent_fallback(self):
        mock_cur = MagicMock()
        warning = dict(HYDRO_WARNING)
        if "stopień" in warning:
            del warning["stopień"]
        warning["stopien"] = "3"
        _upsert_warnings(mock_cur, "hydro", [warning], "ts")
        params = mock_cur.execute.call_args[0][1]
        assert params["severity"] == 3


# ---------------------------------------------------------------------------
# Celery beat schedule config
# ---------------------------------------------------------------------------

class TestCeleryConfig:
    def test_beat_schedule_exists(self):
        from app.celery_app import app as celery_app
        schedule = celery_app.conf.beat_schedule
        assert "fetch-shelters-every-2h" in schedule
        assert "fetch-tauron-every-30min" in schedule
        assert "fetch-imgw-hydro-every-45min" in schedule
        assert "fetch-imgw-warnings-every-45min" in schedule

    def test_shelters_interval_is_2h(self):
        from app.celery_app import app as celery_app
        assert celery_app.conf.beat_schedule["fetch-shelters-every-2h"]["schedule"] == 7200.0

    def test_tauron_interval_is_30min(self):
        from app.celery_app import app as celery_app
        assert celery_app.conf.beat_schedule["fetch-tauron-every-30min"]["schedule"] == 1800.0

    def test_imgw_hydro_interval_is_45min(self):
        from app.celery_app import app as celery_app
        assert celery_app.conf.beat_schedule["fetch-imgw-hydro-every-45min"]["schedule"] == 2700.0

    def test_imgw_warnings_interval_is_45min(self):
        from app.celery_app import app as celery_app
        assert celery_app.conf.beat_schedule["fetch-imgw-warnings-every-45min"]["schedule"] == 2700.0
