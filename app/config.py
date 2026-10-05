from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # JWT
    jwt_secret_key: str = "supersecret-change-in-production-32chars!!"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.2"

    # Groq
    groq_api_key: Optional[str] = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_default_model: str = "openai/gpt-oss-20b"

    # Token quotas
    daily_token_quota: int = 50_000   # tokens per user per day
    monthly_token_quota: int = 500_000

    # SQLite
    database_url: str = "sqlite+aiosqlite:///./usage.db"

    # App
    app_name: str = "NexAI"
    app_version: str = "1.0.0"
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
