"""Runtime configuration for the Agent Core service."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "local"
    debug: bool = False

    agent_core_api_key: str | None = None
    bedrock_region: str = "us-west-2"
    agent_model: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"

    qdrant_mode: str = "cloud"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "articles"

    tool_timeout: int = 30
    max_search_results: int = 8


@lru_cache
def get_settings() -> Settings:
    """Return cached service settings."""

    return Settings()


settings = get_settings()
