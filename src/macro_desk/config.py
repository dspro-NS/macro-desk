from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-based runtime configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MACRO_DESK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_path: Path = Field(default=Path("data/macro_desk.sqlite"))
    rbi_rss_url: str = Field(default="https://rbi.org.in/pressreleases_rss.xml")
    rbi_notification_rss_url: str = Field(default="https://rbi.org.in/notifications_rss.xml")
    rbi_speeches_rss_url: str = Field(default="https://rbi.org.in/speeches_rss.xml")
    http_timeout_seconds: float = Field(default=20.0, ge=1.0, le=120.0)
    user_agent: str = Field(
        default=(
            "MacroDesk/0.1 (+https://github.com/dspro-NS/macro-desk; "
            "personal research ingestion)"
        )
    )


def load_settings() -> Settings:
    return Settings()
