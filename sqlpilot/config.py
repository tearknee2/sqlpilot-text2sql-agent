"""Lazy settings. Do NOT instantiate Settings() at module level (doc §2.12)."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM
    llm_base_url: str = ""
    llm_api_key: str = Field(default="", repr=False)
    llm_model: str = ""
    llm_temperature: float = 0.0
    llm_timeout_s: float = 15.0
    llm_max_retries: int = 2

    # MySQL (read-only at runtime)
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3307
    mysql_user: str = "sqlpilot_ro"
    mysql_password: str = Field(default="", repr=False)
    mysql_database: str = "sqlpilot_demo"

    # Agent budgets (doc §2.6)
    agent_max_steps: int = 16
    agent_max_retries: int = 2
    agent_max_sql_attempts: int = 3
    agent_wallclock_timeout_s: float = 30.0
    agent_token_budget: int = 8000
    max_llm_calls: int = 6
    sql_timeout_s: float = 3.0
    sql_max_rows: int = 200

    # Service
    rate_limit_per_min: int = 20
    demo_offline_mode: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Lazy accessor. Validation of required keys happens at call sites
    (LLMClient.chat / MySqlExecutor.connect), not at import time."""
    return Settings()