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

    # Agent Core
    agent_core_api_key: str | None = None

    # AWS / Bedrock
    aws_region: str = "us-west-2"
    bedrock_region: str = "us-west-2"
    agent_model: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

    # AWS AgentCore Memory (optional — graceful fallback when not configured)
    # memory_id is the AWS Bedrock AgentCore Memory resource ID created via console/Terraform
    memory_id: str | None = None
    memory_execution_role_arn: str | None = None
    memory_event_expiry_days: int = 90

    # OpenAI Embeddings
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"

    # Qdrant Vector DB
    qdrant_mode: str = "cloud"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "articles"

    # Tool timeouts
    tool_timeout: int = 30
    browser_timeout: int = 60
    code_interpreter_timeout: int = 60
    max_search_results: int = 8

    # Browser / Code Interpreter (AWS managed — requires AWS credentials)
    browser_identifier: str = "aws.browser.v1"
    code_interpreter_identifier: str = "aws.codeinterpreter.v1"


@lru_cache
def get_settings() -> Settings:
    """Return cached service settings."""
    return Settings()


settings = get_settings()
