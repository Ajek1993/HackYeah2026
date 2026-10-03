from unittest.mock import MagicMock, patch

import pytest
import requests

from app.sources.shelters import _parse_csv, _row_hash, fetch_shelters

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CSV_HEADER = (
    "Identyfikator publiczny,Nazwa,Rodzaj obiektu,Opis ogolny,"
    "Gmina,Powiat,Wojewodztwo,Szerokosc geograficzna,Dlugosc geograficzna,"
    "Adres,Dostepnosc\r\n"
)

VALID_CSV = (
    CSV_HEADER + "OZO-AAA,Schron testowy,Obiekt ochrony ludności,,Kraków,Kraków,"
    'małopolskie,50.06,19.94,"ul. Testowa 1, Kraków",Na żądanie\r\n'
    "OZO-BBB,Miejsce ochronne,Obiekt ochrony ludności,,Wrocław,Wrocław,"
    'dolnośląskie,51.10,16.95,"ul. Inna 2, Wrocław",Określone godziny\r\n'
)

CSV_WITH_BOM = VALID_CSV.encode("utf-8-sig")

CSV_MISSING_COORDS = (
    CSV_HEADER + "OZO-CCC,Bez koordynatów,Obiekt,,Kraków,Kraków,małopolskie,,"
    ',"ul. X 1",Na żądanie\r\n'
).encode("utf-8-sig")

CSV_BAD_COORDS = (
    CSV_HEADER + "OZO-DDD,Złe współrzędne,Obiekt,,Kraków,Kraków,małopolskie,abc,xyz,"
    '"ul. Y 2",Na żądanie\r\n'
).encode("utf-8-sig")

EMPTY_CSV = CSV_HEADER.encode("utf-8-sig")

CSV_MISSING_COLUMNS = ("Identyfikator publiczny,Nazwa\r\n" "OZO-EEE,Test\r\n").encode("utf-8-sig")

CSV_EMPTY_OPTIONAL_FIELDS = (CSV_HEADER + "OZO-FFF, Schron , , , , , ,50.06,19.94, , \r\n").encode(
    "utf-8-sig"
)


# ---------------------------------------------------------------------------
# _row_hash
# ---------------------------------------------------------------------------


class TestRowHash:
    def test_deterministic(self):
        row = {"a": "1", "b": "2"}
        assert _row_hash(row) == _row_hash(row)

    def test_different_for_different_data(self):
        assert _row_hash({"a": "1"}) != _row_hash({"a": "2"})

    def test_order_independent(self):
        assert _row_hash({"b": "2", "a": "1"}) == _row_hash({"a": "1", "b": "2"})

    def test_handles_missing_keys(self):
        result = _row_hash({"x": "val"})
        assert isinstance(result, str) and len(result) == 32


# ---------------------------------------------------------------------------
# _parse_csv
# ---------------------------------------------------------------------------


class TestParseCsv:
    def test_parses_valid_csv(self):
        rows = _parse_csv(CSV_WITH_BOM)
        assert len(rows) == 2
        assert rows[0]["shelter_id"] == "OZO-AAA"
        assert rows[0]["name"] == "Schron testowy"
        assert rows[0]["lat"] == 50.06
        assert rows[0]["lon"] == 19.94
        assert rows[0]["gmina"] == "Kraków"
        assert rows[0]["powiat"] == "Kraków"
        assert rows[0]["wojewodztwo"] == "małopolskie"
        assert rows[0]["availability"] == "Na żądanie"
        assert rows[0]["address"] == "ul. Testowa 1, Kraków"
        assert rows[0]["object_type"] == "Obiekt ochrony ludności"

    def test_second_row_fields(self):
        rows = _parse_csv(CSV_WITH_BOM)
        assert rows[1]["shelter_id"] == "OZO-BBB"
        assert rows[1]["lat"] == 51.10
        assert rows[1]["availability"] == "Określone godziny"

    def test_row_hash_is_present(self):
        rows = _parse_csv(CSV_WITH_BOM)
        for r in rows:
            assert "row_hash" in r
            assert len(r["row_hash"]) == 32

    def test_skips_rows_with_missing_coords(self):
        rows = _parse_csv(CSV_MISSING_COORDS)
        assert len(rows) == 0

    def test_skips_rows_with_invalid_coords(self):
        rows = _parse_csv(CSV_BAD_COORDS)
        assert len(rows) == 0

    def test_empty_csv_returns_empty_list(self):
        rows = _parse_csv(EMPTY_CSV)
        assert rows == []

    def test_csv_missing_coordinate_columns(self):
        rows = _parse_csv(CSV_MISSING_COLUMNS)
        assert rows == []

    def test_strips_whitespace_and_converts_empty_to_none(self):
        rows = _parse_csv(CSV_EMPTY_OPTIONAL_FIELDS)
        assert len(rows) == 1
        r = rows[0]
        assert r["name"] == "Schron"
        assert r["object_type"] is None
        assert r["description"] is None
        assert r["gmina"] is None
        assert r["powiat"] is None
        assert r["wojewodztwo"] is None
        assert r["address"] is None
        assert r["availability"] is None

    def test_handles_utf8_bom(self):
        rows = _parse_csv(CSV_WITH_BOM)
        assert rows[0]["shelter_id"] == "OZO-AAA"

    def test_handles_utf8_without_bom(self):
        content = VALID_CSV.lstrip("﻿").encode("utf-8")
        rows = _parse_csv(content)
        assert len(rows) == 2


# ---------------------------------------------------------------------------
# fetch_shelters task (mocked HTTP + DB)
# ---------------------------------------------------------------------------


class TestFetchSheltersTask:
    @patch("app.sources.shelters.get_conn")
    @patch("app.sources.shelters.requests.get")
    def test_successful_fetch_upserts_rows(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.content = CSV_WITH_BOM
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {"ts": "2026-10-03T12:00:00+00:00", "n": 0}
        mock_cur.rowcount = 0
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn_obj.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn_obj.__enter__ = MagicMock(return_value=mock_conn_obj)
        mock_conn_obj.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value = mock_conn_obj

        result = fetch_shelters.apply().get(timeout=10)

        assert result["status"] == "ok"
        assert result["upserted"] == 2
        assert result["deactivated"] == 0
        # SELECT now() + 2 upserts + active count + deactivate
        assert mock_cur.execute.call_count == 5

    @patch("app.sources.shelters.get_conn")
    @patch("app.sources.shelters.requests.get")
    def test_empty_csv_skips_db_update(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.content = EMPTY_CSV
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_shelters.apply().get(timeout=10)

        assert result["status"] == "empty"
        assert result["count"] == 0
        mock_conn.assert_not_called()

    @patch("app.sources.shelters.requests.get")
    def test_http_error_retries(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(requests.ConnectionError):
            fetch_shelters.apply().get(timeout=10)

        assert mock_get.call_count >= 1

    @patch("app.sources.shelters.requests.get")
    def test_http_500_retries(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.HTTPError):
            fetch_shelters.apply().get(timeout=10)

    @patch("app.sources.shelters.get_conn")
    @patch("app.sources.shelters.requests.get")
    def test_deactivation_count_propagated(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.content = CSV_WITH_BOM
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {"ts": "2026-10-03T12:00:00+00:00", "n": 0}
        mock_cur.rowcount = 5
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn_obj.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn_obj.__enter__ = MagicMock(return_value=mock_conn_obj)
        mock_conn_obj.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value = mock_conn_obj

        result = fetch_shelters.apply().get(timeout=10)
        assert result["deactivated"] == 5

    @patch("app.sources.shelters.get_conn")
    @patch("app.sources.shelters.requests.get")
    def test_conn_closed_after_success(self, mock_get, mock_conn):
        mock_resp = MagicMock()
        mock_resp.content = CSV_WITH_BOM
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {"ts": "2026-10-03T12:00:00+00:00", "n": 0}
        mock_cur.rowcount = 0
        mock_conn_obj = MagicMock()
        mock_conn_obj.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn_obj.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn_obj.__enter__ = MagicMock(return_value=mock_conn_obj)
        mock_conn_obj.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value = mock_conn_obj

        fetch_shelters.apply().get(timeout=10)
        mock_conn_obj.close.assert_called_once()
