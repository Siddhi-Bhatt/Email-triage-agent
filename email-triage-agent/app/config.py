"""
Application configuration, loaded from environment variables / .env file.

Using pydantic-settings means misconfiguration (e.g. missing API key)
fails fast and loudly at startup with a clear error, instead of failing
deep inside a request handler.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"
    log_level: str = "INFO"
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    """Cached so we only parse the environment once per process."""
    return Settings()