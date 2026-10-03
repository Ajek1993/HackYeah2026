import os


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "")
        self.cors_origins = _csv(os.getenv("CORS_ORIGINS", "http://localhost:5173"))
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"


settings = Settings()
