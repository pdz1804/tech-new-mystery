"""Application configuration via environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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
    s3_bucket: str = "tech-news-articles-381492273521"  # S3 bucket (prod) - override with S3_BUCKET env var for local dev
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
    bedrock_model: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"

    # Legacy Anthropic (for backward compatibility)
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5"

    # Celery - Uses Redis broker
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    celery_task_timeout: int = 300
    celery_worker_concurrency: int = 1
    celery_worker_max_tasks_per_child: int = 10

    # Tavily
    tavily_api_key: str | None = None

    # NewsAPI
    newsapi_key: str | None = None

    # Qdrant Vector Database
    qdrant_mode: str = "cloud"  # "docker" or "cloud"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "articles"

    # OpenAI Embeddings (for vector search)
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_batch_size: int = 100
    openai_embedding_retry_max_attempts: int = 3

    # Clustering Configuration
    clustering_min_cluster_size: int = 5
    clustering_min_samples: int = 3
    clustering_batch_size: int = 100
    clustering_task_timeout: int = 600
    clustering_ttl_days: int = 7

    # Clustering Evaluation Configuration
    clustering_evaluation_enabled: bool = True
    clustering_k_min: int = 5
    clustering_k_max: int = 10
    clustering_evaluation_timeout: int = 300
    clustering_quality_threshold: float = 0.6
    clustering_silhouette_weight: float = 0.5
    clustering_davies_bouldin_weight: float = 0.3
    clustering_calinski_harabasz_weight: float = 0.2

    # DynamoDB Table Names
    dynamodb_article_clusters_table: str = "tech-news-article_clusters"
    dynamodb_cluster_metadata_table: str = "tech-news-cluster_metadata"
    dynamodb_clustering_evaluation_table: str = "tech-news-clustering_evaluation"
    clustering_evaluation_ttl_days: int = 30

    # Agent Core Memory
    agent_memory_type: str = "SHORT_TERM"
    agent_memory_retention_days: int = 90  # 90-day TTL matching DynamoDB

    # Agent Core — production uses boto3 invoke_agent_runtime via runtime ARN.
    # Local dev falls back to HTTP POST if only base_url is set.
    agent_core_runtime_arn: str | None = None   # Set in ECS via Terraform output
    agent_core_base_url: str | None = "http://localhost:8080"  # Local dev fallback
    agent_core_api_key: str | None = None
    agent_core_timeout: int = 60
    agent_core_require_true_streaming: bool = True

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
