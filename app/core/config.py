from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "FastAPI学习项目"
    app_version: str = "1.0.0"
    debug: bool = False
    auth_enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "sqlite:///./app.db"
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
