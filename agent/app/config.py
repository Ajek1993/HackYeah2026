import os


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    def __init__(self) -> None:
        self.glm_api_key = os.getenv("GLM_API_KEY", "")
        self.glm_model = os.getenv("GLM_MODEL", "glm-5.3")
        self.glm_base_url = os.getenv("GLM_BASE_URL", "https://api.z.ai/api/paas/v4/")
        self.api_url = os.getenv("API_URL", "http://api:8000")
        self.cors_origins = _csv(os.getenv("CORS_ORIGINS", "http://localhost:5173"))


settings = Settings()
