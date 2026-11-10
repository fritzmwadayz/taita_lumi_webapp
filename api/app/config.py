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
    database_url: str = "postgresql+asyncpg://localhost/Lumi"

    # ── JWT ────────────────────────────────────────────────────
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # ── Google OAuth ───────────────────────────────────────────
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""

    # ── Email (SMTP) ───────────────────────────────────────────
    # When SMTP_HOST is empty, emails are logged to stdout instead of sent
    # (useful for local development without an SMTP server).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@localhost"
    smtp_use_tls: bool = True

    # ── Email log file (dev-mode capture) ───────────────────────
    # If set (and SMTP_HOST is empty), every email sent in dev mode is also
    # appended to this file as a JSON line:
    #   {"to": "...", "subject": "...", "body": "...", "html": "...", "ts": ...}
    # Lets test scripts capture real reset tokens / verification codes without
    # SMTP — the same `send_email()` code path runs, just with a file sink.
    # Leave empty to disable (default — emails go to stdout only).
    email_log_file: str = ""

    # ── Frontend URL ────────────────────────────────────────────
    # Used to build absolute links in emails (e.g. password reset).
    frontend_url: str = "http://localhost:3000"

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
