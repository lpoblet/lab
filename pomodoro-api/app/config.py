from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import make_url


def normalize_database_url(url: str) -> str:
    parsed = make_url(url)
    driver = parsed.drivername
    if driver in {"postgres", "postgresql", "postgresql+psycopg2"}:
        parsed = parsed.set(drivername="postgresql+psycopg")
    elif driver == "postgres+psycopg":
        parsed = parsed.set(drivername="postgresql+psycopg")
    return parsed.render_as_string(hide_password=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    port: int = 8000
    db_connect_timeout: int = 3
    db_pool_timeout: int = 5

    @field_validator("database_url", mode="after")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
