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
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── PostgreSQL ───────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "astrology"
    POSTGRES_PASSWORD: str = "astrology_dev"
    POSTGRES_DB: str = "astrology_agent"
    POSTGRES_MIN_CONNECTIONS: int = 2
    POSTGRES_MAX_CONNECTIONS: int = 20

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

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

    # ── Rate Limiting ────────────────────────────────────────────
    RATE_LIMIT_SSE_CONNECTS: int = 60
    RATE_LIMIT_CHART_CALCS: int = 20
    RATE_LIMIT_WINDOW_SECONDS: int = 3600  # 1 hour

    # ── LLM / OpenCode Go API ────────────────────────────────────
    OPENCODE_API_KEY: str = ""


settings = Settings()
