#!/usr/bin/env bash
set -euo pipefail

REGION="${REGION:-us-west-2}"
TABLE_PREFIX="${TABLE_PREFIX:-tech-news-}"
S3_BUCKET="${S3_BUCKET:-tech-news-articles-381492273521}"
NAME_PREFIX="${NAME_PREFIX:-tech-news-mystery-prod}"
APP_SECRET_NAME="${APP_SECRET_NAME:-${NAME_PREFIX}/app}"
REDIS_SUBNET_GROUP="${REDIS_SUBNET_GROUP:-${NAME_PREFIX}-redis}"
CODEBUILD_SOURCE_BUCKET="${CODEBUILD_SOURCE_BUCKET:-${NAME_PREFIX}-codebuild-sources-${AWS_ACCOUNT_ID:-}}"

tables=(
  "users:aws_dynamodb_table.users[0]"
  "articles:aws_dynamodb_table.articles[0]"
  "comments:aws_dynamodb_table.comments[0]"
  "user_saves:aws_dynamodb_table.user_saves[0]"
  "user_likes:aws_dynamodb_table.user_likes[0]"
  "user_preferences:aws_dynamodb_table.user_preferences[0]"
  "news_sources:aws_dynamodb_table.news_sources[0]"
  "pending-searches:aws_dynamodb_table.pending_searches[0]"
  "trending_articles:aws_dynamodb_table.trending_articles[0]"
  "submissions:aws_dynamodb_table.submissions[0]"
  "conversation_sessions:aws_dynamodb_table.conversation_sessions[0]"
  "conversation_messages:aws_dynamodb_table.conversation_messages[0]"
  "chat_user_preferences:aws_dynamodb_table.chat_user_preferences[0]"
  "article_clusters:aws_dynamodb_table.article_clusters[0]"
  "cluster_metadata:aws_dynamodb_table.cluster_metadata[0]"
  "article_embeddings:aws_dynamodb_table.article_embeddings[0]"
  "clustering_evaluation:aws_dynamodb_table.clustering_evaluation[0]"
  "clustering_params:aws_dynamodb_table.clustering_params[0]"
)

in_state() {
  terraform state show "$1" >/dev/null 2>&1
}

import_if_needed() {
  local resource="$1"
  local id="$2"

  if in_state "$resource"; then
    echo "Already in Terraform state: $resource"
  else
    echo "Importing existing resource: $resource ($id)"
    terraform import -lock-timeout=5m "$resource" "$id"
  fi
}

for item in "${tables[@]}"; do
  name="${item%%:*}"
  resource="${item#*:}"
  full_name="${TABLE_PREFIX}${name}"
  if aws dynamodb describe-table --region "$REGION" --table-name "$full_name" >/dev/null 2>&1; then
    import_if_needed "$resource" "$full_name"
  else
    echo "DynamoDB table not found, Terraform will create: $full_name"
  fi
done

if [[ -n "$S3_BUCKET" ]]; then
  if aws s3api head-bucket --bucket "$S3_BUCKET" >/dev/null 2>&1; then
    import_if_needed "aws_s3_bucket.articles[0]" "$S3_BUCKET"
  else
    echo "S3 bucket not found, Terraform will create: $S3_BUCKET"
  fi
fi

if aws secretsmanager describe-secret --region "$REGION" --secret-id "$APP_SECRET_NAME" >/dev/null 2>&1; then
  import_if_needed "aws_secretsmanager_secret.app[0]" "$APP_SECRET_NAME"
else
  echo "Secrets Manager secret not found, Terraform will create: $APP_SECRET_NAME"
fi

if aws elasticache describe-cache-subnet-groups --region "$REGION" --cache-subnet-group-name "$REDIS_SUBNET_GROUP" >/dev/null 2>&1; then
  import_if_needed "aws_elasticache_subnet_group.redis" "$REDIS_SUBNET_GROUP"
else
  echo "ElastiCache subnet group not found, Terraform will create: $REDIS_SUBNET_GROUP"
fi

ecr_repositories=(
  "${NAME_PREFIX}-backend:aws_ecr_repository.backend"
  "${NAME_PREFIX}-frontend:aws_ecr_repository.frontend"
  "${NAME_PREFIX}-agent-core:aws_ecr_repository.agent_core"
)

for item in "${ecr_repositories[@]}"; do
  name="${item%%:*}"
  resource="${item#*:}"
  if aws ecr describe-repositories --region "$REGION" --repository-names "$name" >/dev/null 2>&1; then
    import_if_needed "$resource" "$name"
  else
    echo "ECR repository not found, Terraform will create: $name"
  fi
done

if aws ecs describe-clusters --region "$REGION" --clusters "$NAME_PREFIX" --query 'clusters[?status==`ACTIVE`].clusterName' --output text | tr '\t' '\n' | grep -Fxq "$NAME_PREFIX"; then
  import_if_needed "aws_ecs_cluster.app" "$NAME_PREFIX"
else
  echo "ECS cluster not found, Terraform will create: $NAME_PREFIX"
fi

log_groups=(
  "/ecs/${NAME_PREFIX}:aws_cloudwatch_log_group.app"
  "/ecs/${NAME_PREFIX}-clustering:aws_cloudwatch_log_group.clustering"
)

for item in "${log_groups[@]}"; do
  name="${item%%:*}"
  resource="${item#*:}"
  if aws logs describe-log-groups --region "$REGION" --log-group-name-prefix "$name" --query 'logGroups[].logGroupName' --output text | tr '\t' '\n' | grep -Fxq "$name"; then
    import_if_needed "$resource" "$name"
  else
    echo "CloudWatch log group not found, Terraform will create: $name"
  fi
done

if [[ -n "$CODEBUILD_SOURCE_BUCKET" ]]; then
  if aws s3api head-bucket --bucket "$CODEBUILD_SOURCE_BUCKET" >/dev/null 2>&1; then
    import_if_needed "aws_s3_bucket.codebuild_sources" "$CODEBUILD_SOURCE_BUCKET"
  else
    echo "CodeBuild source bucket not found, Terraform will create: $CODEBUILD_SOURCE_BUCKET"
  fi
fi
