"""Application configuration via environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "Tech News Mystery"
    debug: bool = False
    secret_key: str
    api_v1_prefix: str = "/v1"

    # AWS / DynamoDB / S3
    # Note: AWS credentials are managed via IAM role attached to EC2 instance
    # No hardcoded credentials in application code
    aws_region: str = "us-west-2"
    dynamodb_endpoint_url: str | None = None  # None = use real AWS DynamoDB
    dynamodb_table_prefix: str = "tech-news-"  # Prefix for all DynamoDB table names
    s3_bucket: str = "tech-news-articles"  # S3 bucket for storing article images
    s3_images_prefix: str = "article-images/"  # Prefix for images in S3

    # Redis - Switch based on environment
    # Local dev: Docker Redis container at redis://redis:6379/0
    # Production: AWS ElastiCache endpoint (set REDIS_URL in .env or env vars)
    environment: str = "local"  # "local" or "production"
    redis_url: str = "redis://redis:6379/0"  # Docker Redis for local dev

    # LLM Providers - Support multiple providers (comma-separated for fallback chain)
    llm_provider: str = "bedrock,openai"  # Primary: Bedrock, Fallback: OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-mini"

    bedrock_region: str = "us-west-2"
    bedrock_model: str = "anthropic.claude-3-5-haiku-20241022"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"

    # Legacy Anthropic (for backward compatibility)
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5"

    # Celery - Uses Redis broker
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    celery_task_timeout: int = 300

    # Tavily
    tavily_api_key: str | None = None

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours (1 day)
    refresh_token_expire_days: int = 30


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
