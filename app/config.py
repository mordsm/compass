from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COMPASS_", env_file=".env", extra="ignore")

    actions_api_key: str = Field(default="dev-only-change-me")
    database_path: Path = Field(default=Path("data/compass.db"))
    public_base_url: str = Field(default="http://localhost:8000")
    user_id: str = Field(default="moshe")
    rules_engine_path: Path = Field(default=Path("../rules_engine"))
    rules_engine_base_url: str = Field(default="http://127.0.0.1:8003")
    self_manage_base_url: str = Field(default="http://127.0.0.1:8001")
    assessment_base_url: str = Field(default="http://127.0.0.1:8002")
    mail_manager_base_url: str = Field(default="http://127.0.0.1:8004")
    economic_spending_base_url: str = Field(default="http://127.0.0.1:8005")
    task_commander_base_url: str = Field(default="http://127.0.0.1:8006")
    administrative_base_url: str = Field(default="http://127.0.0.1:8007")


@lru_cache
def get_settings() -> Settings:
    return Settings()
