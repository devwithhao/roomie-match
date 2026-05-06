from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    jwt_secret: str
    jwt_expire_minutes: int = 60
    # Neu true: loi 500 tu register se kem thong bao loi DB (chi localhost/debug)
    app_debug: bool = Field(default=False, validation_alias="APP_DEBUG")


settings = Settings()
