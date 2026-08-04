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
    assessment_path: Path = Field(default=Path("../personal_Assessment"))
    mail_manager_base_url: str = Field(default="http://127.0.0.1:8004")
    economic_spending_base_url: str = Field(default="http://127.0.0.1:8005")
    economic_spending_path: Path = Field(default=Path("../economic_spending"))
    task_commander_base_url: str = Field(default="http://127.0.0.1:8006")
    administrative_base_url: str = Field(default="http://127.0.0.1:8007")
    autostart_local_agents: bool = Field(default=True)
    autostart_wait_seconds: float = Field(default=12.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
