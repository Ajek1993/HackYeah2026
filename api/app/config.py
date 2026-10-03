import os


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "")
        self.cors_origins = _csv(os.getenv("CORS_ORIGINS", "http://localhost:5173"))
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        self.celery_broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
        self.celery_result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
        self.shelters_csv_url = os.getenv(
            "SHELTERS_CSV_URL",
            "https://api.dane.gov.pl/resources/1393918,punkty-schronienia-dane-csv/file",
        )
        self.tauron_api_url = os.getenv(
            "TAURON_API_URL",
            "https://www.tauron-dystrybucja.pl/waapi/outages/items",
        )
        self.imgw_hydro_url = os.getenv(
            "IMGW_HYDRO_URL",
            "https://danepubliczne.imgw.pl/api/data/hydro",
        )
        self.imgw_warnings_hydro_url = os.getenv(
            "IMGW_WARNINGS_HYDRO_URL",
            "https://danepubliczne.imgw.pl/api/data/warningshydro",
        )
        self.imgw_warnings_meteo_url = os.getenv(
            "IMGW_WARNINGS_METEO_URL",
            "https://danepubliczne.imgw.pl/api/data/warningsmeteo",
        )
        self.krakow_teryt = os.getenv("KRAKOW_TERYT", "1261")
        self.nominatim_url = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
        self.nominatim_user_agent = os.getenv(
            "NOMINATIM_USER_AGENT",
            "KryzIO/1.0 (HackYeah2026; https://github.com/Ajek1993/HackYeah2026)",
        )
        self.gios_api_url = os.getenv("GIOS_API_URL", "https://api.gios.gov.pl/pjp-api/v1/rest")
        self.airly_api_url = os.getenv("AIRLY_API_URL", "https://airapi.airly.eu/v2")
        self.airly_api_key = os.getenv("AIRLY_API_KEY", "")
        # Protects the public geocoder endpoints and the Nominatim quota (audit A4)
        self.geocode_rate_limit_per_minute = int(os.getenv("GEOCODE_RATE_LIMIT_PER_MINUTE", "30"))
        # Shared with the agent, whose calls (one container IP for all users) skip that limit
        self.internal_token = os.getenv("API_INTERNAL_TOKEN", "")
        # "production" hides /docs and /openapi.json
        self.app_env = os.getenv("APP_ENV", "development")


settings = Settings()
