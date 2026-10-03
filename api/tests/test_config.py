import os
from unittest.mock import patch

from app.config import Settings


class TestSettings:
    def test_default_values(self):
        with patch.dict(os.environ, {}, clear=True):
            s = Settings()
            assert s.database_url == ""
            assert s.demo_mode is False
            assert s.demo_admin_token == ""
            assert s.demo_ttl_minutes == 30
            assert s.cors_origins == ["http://localhost:5173"]
            assert "dane.gov.pl" in s.shelters_csv_url
            assert "tauron" in s.tauron_api_url
            assert "imgw" in s.imgw_hydro_url
            assert "warningshydro" in s.imgw_warnings_hydro_url
            assert "warningsmeteo" in s.imgw_warnings_meteo_url
            assert s.krakow_teryt == "1261"
            assert s.celery_broker_url == "redis://redis:6379/0"
            assert s.celery_result_backend == "redis://redis:6379/1"

    def test_demo_mode_true(self):
        with patch.dict(os.environ, {"DEMO_MODE": "true"}, clear=False):
            s = Settings()
            assert s.demo_mode is True

    def test_demo_mode_case_insensitive(self):
        with patch.dict(os.environ, {"DEMO_MODE": "True"}, clear=False):
            s = Settings()
            assert s.demo_mode is True

    def test_database_url_from_env(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://a:b@c/d"}, clear=False):
            s = Settings()
            assert s.database_url == "postgresql://a:b@c/d"

    def test_cors_origins_csv(self):
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://a.com, http://b.com"}, clear=False):
            s = Settings()
            assert s.cors_origins == ["http://a.com", "http://b.com"]

    def test_cors_origins_empty_items_stripped(self):
        with patch.dict(
            os.environ, {"CORS_ORIGINS": "http://a.com,,, http://b.com, "}, clear=False
        ):
            s = Settings()
            assert s.cors_origins == ["http://a.com", "http://b.com"]

    def test_custom_urls(self):
        with patch.dict(
            os.environ,
            {
                "SHELTERS_CSV_URL": "http://custom/shelters",
                "TAURON_API_URL": "http://custom/tauron",
                "IMGW_HYDRO_URL": "http://custom/hydro",
                "KRAKOW_TERYT": "9999",
            },
            clear=False,
        ):
            s = Settings()
            assert s.shelters_csv_url == "http://custom/shelters"
            assert s.tauron_api_url == "http://custom/tauron"
            assert s.imgw_hydro_url == "http://custom/hydro"
            assert s.krakow_teryt == "9999"
