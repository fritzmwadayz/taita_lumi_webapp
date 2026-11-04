"""Application settings — read from environment / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. Override via .env file or env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # ── Database ───────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://localhost/taitalumi"

    # ── JWT ────────────────────────────────────────────────────
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # ── Google OAuth ───────────────────────────────────────────
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""

    # ── CORS ───────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173"

    # ── App ────────────────────────────────────────────────────
    app_env: str = "development"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
