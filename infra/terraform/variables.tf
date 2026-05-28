variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Short name used in AWS resource names."
  type        = string
  default     = "tech-news-mystery"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "prod"
}

variable "dynamodb_table_prefix" {
  description = "Prefix expected by backend/app/config.py."
  type        = string
  default     = "tech-news-"
}

variable "create_dynamodb_tables" {
  description = "Create DynamoDB tables. Set false after importing existing tables, or when tables are managed outside this stack."
  type        = bool
  default     = true
}

variable "create_s3_bucket" {
  description = "Create the article-images S3 bucket. Set false to use an existing bucket."
  type        = bool
  default     = true
}

variable "existing_s3_bucket_name" {
  description = "Existing S3 bucket name when create_s3_bucket is false."
  type        = string
  default     = ""
}

variable "s3_bucket_name" {
  description = "S3 bucket name to create or import. Defaults to the existing app bucket from backend/app/config.py."
  type        = string
  default     = "tech-news-articles-381492273521"
}

variable "create_vpc" {
  description = "Create a VPC. Set false to deploy into an existing VPC/subnets."
  type        = bool
  default     = true
}

variable "existing_vpc_id" {
  description = "Existing VPC ID when create_vpc is false."
  type        = string
  default     = ""
}

variable "existing_public_subnet_ids" {
  description = "Existing public subnet IDs for ALB/ECS when create_vpc is false."
  type        = list(string)
  default     = []
}

variable "existing_private_subnet_ids" {
  description = "Existing private subnet IDs for ElastiCache when create_vpc is false. Falls back to public subnets if empty."
  type        = list(string)
  default     = []
}

variable "vpc_cidr" {
  description = "CIDR for the managed VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs. Keep two AZs for ALB/ECS."
  type        = list(string)
  default     = ["10.40.0.0/24", "10.40.1.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDRs for Redis."
  type        = list(string)
  default     = ["10.40.10.0/24", "10.40.11.0/24"]
}

variable "backend_image_tag" {
  description = "Backend image tag deployed by ECS."
  type        = string
  default     = "latest"
}

variable "frontend_image_tag" {
  description = "Frontend image tag deployed by ECS."
  type        = string
  default     = "latest"
}

variable "api_desired_count" {
  description = "Desired FastAPI task count."
  type        = number
  default     = 1
}

variable "frontend_desired_count" {
  description = "Desired Next.js task count."
  type        = number
  default     = 1
}

variable "worker_desired_count" {
  description = "Desired Celery worker task count."
  type        = number
  default     = 1
}

variable "beat_desired_count" {
  description = "Desired Celery beat scheduler task count. Usually exactly 1."
  type        = number
  default     = 1
}

variable "agent_core_image_tag" {
  description = "Agent Core runtime image tag deployed by ECS."
  type        = string
  default     = "latest"
}

variable "agent_core_desired_count" {
  description = "Desired Agent Core task count."
  type        = number
  default     = 2
}

variable "agent_core_min_count" {
  description = "Minimum Agent Core task count for auto-scaling."
  type        = number
  default     = 2
}

variable "agent_core_max_count" {
  description = "Maximum Agent Core task count for auto-scaling."
  type        = number
  default     = 10
}

variable "agent_core_cpu" {
  description = "Fargate CPU units for Agent Core tasks."
  type        = number
  default     = 2048
}

variable "agent_core_memory" {
  description = "Fargate memory in MiB for Agent Core tasks."
  type        = number
  default     = 4096
}

variable "agent_core_model" {
  description = "Claude model for Agent Core runtime."
  type        = string
  default     = "claude-haiku-4-5-20251001"
}

variable "agent_core_memory_type" {
  description = "Memory system type for Agent Core (short_term, long_term, or hybrid)."
  type        = string
  default     = "hybrid"
}

variable "agent_core_tool_timeout" {
  description = "Tool execution timeout in seconds for Agent Core."
  type        = number
  default     = 30
}

variable "task_cpu" {
  description = "Default Fargate CPU units. Upgraded to 1024 (from 512) for worker stability."
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "Default Fargate memory in MiB. Upgraded to 2048 (from 1024) for worker OOM fix."
  type        = number
  default     = 2048
}

variable "redis_node_type" {
  description = "ElastiCache Redis node size."
  type        = string
  default     = "cache.t4g.micro"
}

variable "allowed_http_cidr_blocks" {
  description = "CIDR ranges allowed to reach the public ALB."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "certificate_arn" {
  description = "Optional ACM certificate ARN. When set, the ALB also exposes HTTPS."
  type        = string
  default     = ""
}

variable "secrets_manager_arn" {
  description = "Existing Secrets Manager JSON secret ARN. Leave empty to create an empty app secret."
  type        = string
  default     = ""
}

variable "secret_json_keys" {
  description = "JSON keys expected inside the app secret."
  type = object({
    secret_key        = string
    jwt_secret_key    = string
    openai_api_key    = string
    tavily_api_key    = string
    newsapi_key       = string
    qdrant_url        = string
    qdrant_api_key    = string
    gemini_api_key    = string
    anthropic_api_key = string
  })
  default = {
    secret_key        = "SECRET_KEY"
    jwt_secret_key    = "JWT_SECRET_KEY"
    openai_api_key    = "OPENAI_API_KEY"
    tavily_api_key    = "TAVILY_API_KEY"
    newsapi_key       = "NEWSAPI_KEY"
    qdrant_url        = "QDRANT_URL"
    qdrant_api_key    = "QDRANT_API_KEY"
    gemini_api_key    = "GEMINI_API_KEY"
    anthropic_api_key = "ANTHROPIC_API_KEY"
  }
}
