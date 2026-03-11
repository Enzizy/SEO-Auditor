from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="SEO_AUDITOR_",
    )

    app_env: str = "development"
    debug: bool = False
    app_name: str = "Joyno SEO Auditor Tool"
    secret_key: str = "change-me"
    base_url: str = "http://localhost:8000"
    default_user_email: str = "demo@seoauditor.local"
    database_url: str = "sqlite:///./seo_auditor.db"
    redis_url: str = "redis://localhost:6379/0"
    rq_queue_name: str = "seo-audits"
    execution_backend: str = "inline"
    reports_dir: str = "reports"
    storage_backend: str = "local"
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_endpoint_url: str | None = None
    log_level: str = "INFO"
    request_timeout_seconds: int = 15
    crawler_default_max_pages: int = 25
    crawler_default_max_depth: int = 2
    crawler_user_agent: str = "JoynoSEOAuditorToolBot/1.0"
    pagespeed_api_key: str | None = None
    pagespeed_strategy: str = "mobile"
    allow_auto_create_tables: bool = False
    session_cookie_name: str = "seo_auditor_session"
    safe_large_image_bytes: int = Field(default=250_000)
    large_asset_bytes: int = Field(default=350_000)

    @property
    def reports_path(self) -> Path:
        path = BASE_DIR / self.reports_dir
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
