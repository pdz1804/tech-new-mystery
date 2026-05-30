"""Runtime configuration for the Agent Core service."""

from functools import lru_cache
import json
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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
    app_secret_arn: str | None = None
    require_true_streaming: bool = True

    # AWS / Bedrock
    aws_region: str = "us-west-2"
    bedrock_region: str = "us-west-2"
    agent_model: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

    # AWS AgentCore Memory — set by Terraform via aws_bedrockagentcore_memory.main.id
    memory_id: str | None = None

    # AWS AgentCore Browser — set by Terraform via aws_bedrockagentcore_browser.main.browser_id
    browser_id: str | None = None

    # AWS AgentCore Code Interpreter — set by Terraform
    code_interpreter_id: str | None = None

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

    def model_post_init(self, __context) -> None:
        if not self.app_secret_arn:
            return

        try:
            import boto3

            client = boto3.client("secretsmanager", region_name=self.aws_region)
            response = client.get_secret_value(SecretId=self.app_secret_arn)
            secret = json.loads(response.get("SecretString") or "{}")
        except Exception as exc:
            logger.warning("Could not load AgentCore app secret: %s", exc)
            return

        for field_name, secret_key in {
            "openai_api_key": "OPENAI_API_KEY",
            "qdrant_url": "QDRANT_URL",
            "qdrant_api_key": "QDRANT_API_KEY",
        }.items():
            if getattr(self, field_name) in (None, "") and secret.get(secret_key):
                setattr(self, field_name, secret[secret_key])


@lru_cache
def get_settings() -> Settings:
    """Return cached service settings."""
    return Settings()


settings = get_settings()
