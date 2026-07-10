"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All config values read from environment, with sensible defaults for local dev."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "Astrology Agent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── Server ───────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173", "http://localhost:5174", "http://localhost:3000",
    ]

    # ── SQLite ──────────────────────────────────────────────────
    SQLITE_PATH: str = "data/astrology.db"

    # ── Redis ────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ── Auth / JWT ───────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ANONYMOUS_EXPIRY_HOURS: int = 24
    JWT_AUTHENTICATED_EXPIRY_HOURS: int = 168  # 7 days

    # ── Dev Auth ─────────────────────────────────────────────────
    AUTH_DEV_MODE_ENABLED: bool = True
    AUTH_DEV_USER_ID: str = "00000000-0000-4000-8000-000000000001"
    AUTH_DEV_DISPLAY_NAME: str = "Dev User"

    # ── Google Auth ──────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # ── Rate Limiting ────────────────────────────────────────────
    RATE_LIMIT_SSE_CONNECTS: int = 60
    RATE_LIMIT_CHART_CALCS: int = 20
    RATE_LIMIT_WINDOW_SECONDS: int = 3600  # 1 hour

    # ── LLM / OpenCode Go API ────────────────────────────────────
    OPENCODE_API_KEY: str = ""
    # Base URL without trailing path segment (client appends /chat/completions)
    OPENCODE_API_BASE: str = "https://opencode.ai/zen/go/v1"
    OPENCODE_MODEL: str = "deepseek-v4-flash"
    # live = real OpenCode API; mock = deterministic scripted replies (offline only)
    LLM_MODE: str = "live"


settings = Settings()
