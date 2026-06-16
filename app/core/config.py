from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FastAPI学习项目"
    app_version: str = "1.0.0"
    debug: bool = False
    auth_enabled: bool = True
    thread_pool_max_workers: int = 8
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "mysql+pymysql://root:123456@10.20.40.26:3306/fastapi_study?charset=utf8mb4"
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    openai_base_url: str | None = None

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"debug", "dev", "development", "true", "1", "yes", "on"}:
                return True
            if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False
        return value

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
