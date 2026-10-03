import os


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    def __init__(self) -> None:
        self.glm_api_key = os.getenv("GLM_API_KEY", "")
        self.glm_model = os.getenv("GLM_MODEL", "glm-5.3")
        self.glm_base_url = os.getenv("GLM_BASE_URL", "https://api.z.ai/api/coding/paas/v4/")
        self.glm_max_tokens = int(os.getenv("GLM_MAX_TOKENS", "1200"))
        self.glm_temperature = float(os.getenv("GLM_TEMPERATURE", "0.2"))
        self.glm_thinking = os.getenv("GLM_THINKING", "disabled")
        self.glm_timeout = float(os.getenv("GLM_TIMEOUT", "30"))
        self.max_tool_rounds = int(os.getenv("AGENT_MAX_TOOL_ROUNDS", "3"))
        self.max_tool_calls_per_round = int(os.getenv("AGENT_MAX_TOOL_CALLS_PER_ROUND", "6"))
        self.request_deadline_s = float(os.getenv("AGENT_REQUEST_DEADLINE_S", "45"))
        self.session_ttl_seconds = int(os.getenv("SESSION_TTL_SECONDS", "1800"))
        self.session_max_messages = int(os.getenv("SESSION_MAX_MESSAGES", "20"))
        self.session_max_count = int(os.getenv("SESSION_MAX_COUNT", "5000"))
        self.chat_rate_limit_per_minute = int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "10"))
        # "production" hides /docs and /openapi.json
        self.app_env = os.getenv("APP_ENV", "development")
        self.api_url = os.getenv("API_URL", "http://api:8000")
        self.api_internal_token = os.getenv("API_INTERNAL_TOKEN", "")
        self.cors_origins = _csv(os.getenv("CORS_ORIGINS", "http://localhost:5173"))


settings = Settings()
