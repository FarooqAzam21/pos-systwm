from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 60
    frontend_origins: str = "https://pos-systwm.vercel.app,http://localhost:5173"
    algorithm: str = "HS256"
    redis_url: str | None = None
    redis_socket_timeout_seconds: float = 0.4
    redis_connect_timeout_seconds: float = 0.4
    redis_max_connections: int = 20
    dashboard_cache_ttl_seconds: int = 30
    reports_cache_ttl_seconds: int = 60
    catalog_cache_ttl_seconds: int = 60
    settings_cache_ttl_seconds: int = 600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
