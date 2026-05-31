#!/usr/bin/env bash
set -euo pipefail

REGION="${REGION:-us-west-2}"
TABLE_PREFIX="${TABLE_PREFIX:-tech-news-}"
S3_BUCKET="${S3_BUCKET:-tech-news-articles-381492273521}"
NAME_PREFIX="${NAME_PREFIX:-tech-news-mystery-prod}"
APP_SECRET_NAME="${APP_SECRET_NAME:-${NAME_PREFIX}/app}"
REDIS_SUBNET_GROUP="${REDIS_SUBNET_GROUP:-${NAME_PREFIX}-redis}"
CODEBUILD_SOURCE_BUCKET="${CODEBUILD_SOURCE_BUCKET:-${NAME_PREFIX}-codebuild-sources-${AWS_ACCOUNT_ID:-}}"
AGENTCORE_NAME_PREFIX="${AGENTCORE_NAME_PREFIX:-${NAME_PREFIX//-/_}}"
AGENTCORE_RUNTIME_NAME="${AGENTCORE_RUNTIME_NAME:-${AGENTCORE_NAME_PREFIX}_agent}"
AGENTCORE_MEMORY_NAME="${AGENTCORE_MEMORY_NAME:-${AGENTCORE_NAME_PREFIX}_memory}"
AGENTCORE_BROWSER_NAME="${AGENTCORE_BROWSER_NAME:-${AGENTCORE_NAME_PREFIX}_browser}"
AGENTCORE_CODE_INTERPRETER_NAME="${AGENTCORE_CODE_INTERPRETER_NAME:-${AGENTCORE_NAME_PREFIX}_code_interpreter}"
AGENT_CORE_CODEBUILD_PROJECT="${AGENT_CORE_CODEBUILD_PROJECT:-${NAME_PREFIX}-agent-core-arm64-image}"

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

APP_SECRET_ARN="$(aws secretsmanager describe-secret --region "$REGION" --secret-id "$APP_SECRET_NAME" --query ARN --output text 2>/dev/null || true)"
if [[ -n "$APP_SECRET_ARN" && "$APP_SECRET_ARN" != "None" ]]; then
  import_if_needed "aws_secretsmanager_secret.app[0]" "$APP_SECRET_ARN"
else
  echo "Secrets Manager secret not found, Terraform will create: $APP_SECRET_NAME"
fi

if aws elasticache describe-cache-subnet-groups --region "$REGION" --cache-subnet-group-name "$REDIS_SUBNET_GROUP" >/dev/null 2>&1; then
  import_if_needed "aws_elasticache_subnet_group.redis" "$REDIS_SUBNET_GROUP"
else
  echo "ElastiCache subnet group not found, Terraform will create: $REDIS_SUBNET_GROUP"
fi

REDIS_REPLICATION_GROUP="$(printf "%.40s" "${NAME_PREFIX}-redis")"
if aws elasticache describe-replication-groups --region "$REGION" --replication-group-id "$REDIS_REPLICATION_GROUP" >/dev/null 2>&1; then
  import_if_needed "aws_elasticache_replication_group.redis" "$REDIS_REPLICATION_GROUP"
else
  echo "ElastiCache replication group not found, Terraform will create: $REDIS_REPLICATION_GROUP"
fi

iam_roles=(
  "${NAME_PREFIX}-ecs-execution:aws_iam_role.ecs_task_execution"
  "${NAME_PREFIX}-ecs-task:aws_iam_role.ecs_task"
  "${NAME_PREFIX}-agentcore-runtime:aws_iam_role.agentcore_runtime"
  "${NAME_PREFIX}-agentcore-memory:aws_iam_role.agentcore_memory"
  "${NAME_PREFIX}-agent-core-codebuild:aws_iam_role.codebuild_agent_core"
)

for item in "${iam_roles[@]}"; do
  name="${item%%:*}"
  resource="${item#*:}"
  if aws iam get-role --role-name "$name" >/dev/null 2>&1; then
    import_if_needed "$resource" "$name"
  else
    echo "IAM role not found, Terraform will create: $name"
  fi
done

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

if aws codebuild batch-get-projects --region "$REGION" --names "$AGENT_CORE_CODEBUILD_PROJECT" --query 'projects[0].name' --output text 2>/dev/null | grep -Fxq "$AGENT_CORE_CODEBUILD_PROJECT"; then
  import_if_needed "aws_codebuild_project.agent_core_image" "$AGENT_CORE_CODEBUILD_PROJECT"
else
  echo "CodeBuild project not found, Terraform will create: $AGENT_CORE_CODEBUILD_PROJECT"
fi

ecs_services=(api frontend worker beat clustering)
for service in "${ecs_services[@]}"; do
  if aws ecs describe-services --region "$REGION" --cluster "$NAME_PREFIX" --services "$service" --query 'services[?status==`ACTIVE`].serviceName' --output text 2>/dev/null | tr '\t' '\n' | grep -Fxq "$service"; then
    import_if_needed "aws_ecs_service.${service}" "${NAME_PREFIX}/${service}"
  else
    echo "ECS service not found, Terraform will create: $service"
  fi
done

MEMORY_ID=""
for memory_id in $(aws bedrock-agentcore-control list-memories --region "$REGION" --query 'memories[].id' --output text 2>/dev/null | tr '\t' '\n' || true); do
  memory_name="$(aws bedrock-agentcore-control get-memory --region "$REGION" --memory-id "$memory_id" --query 'memory.name' --output text 2>/dev/null || true)"
  if [[ "$memory_name" == "$AGENTCORE_MEMORY_NAME" ]]; then
    MEMORY_ID="$memory_id"
    break
  fi
done
if [[ -n "$MEMORY_ID" ]]; then
  import_if_needed "aws_bedrockagentcore_memory.agent_core" "$MEMORY_ID"
else
  echo "AgentCore memory not found, Terraform will create: $AGENTCORE_MEMORY_NAME"
fi

BROWSER_ID="$(aws bedrock-agentcore-control list-browsers --region "$REGION" --query "browserSummaries[?name==\`${AGENTCORE_BROWSER_NAME}\`].browserId | [0]" --output text 2>/dev/null || true)"
if [[ -n "$BROWSER_ID" && "$BROWSER_ID" != "None" ]]; then
  import_if_needed "aws_bedrockagentcore_browser.agent_core" "$BROWSER_ID"
else
  echo "AgentCore browser not found, Terraform will create: $AGENTCORE_BROWSER_NAME"
fi

CODE_INTERPRETER_ID="$(aws bedrock-agentcore-control list-code-interpreters --region "$REGION" --query "codeInterpreterSummaries[?name==\`${AGENTCORE_CODE_INTERPRETER_NAME}\`].codeInterpreterId | [0]" --output text 2>/dev/null || true)"
if [[ -n "$CODE_INTERPRETER_ID" && "$CODE_INTERPRETER_ID" != "None" ]]; then
  import_if_needed "aws_bedrockagentcore_code_interpreter.agent_core" "$CODE_INTERPRETER_ID"
else
  echo "AgentCore code interpreter not found, Terraform will create: $AGENTCORE_CODE_INTERPRETER_NAME"
fi

AGENT_RUNTIME_ID="$(aws bedrock-agentcore-control list-agent-runtimes --region "$REGION" --query "agentRuntimes[?agentRuntimeName==\`${AGENTCORE_RUNTIME_NAME}\`].agentRuntimeId | [0]" --output text 2>/dev/null || true)"
if [[ -n "$AGENT_RUNTIME_ID" && "$AGENT_RUNTIME_ID" != "None" ]]; then
  import_if_needed "aws_bedrockagentcore_agent_runtime.agent_core" "$AGENT_RUNTIME_ID"
else
  echo "AgentCore runtime not found, Terraform will create: $AGENTCORE_RUNTIME_NAME"
fi

LB_NAME="$(printf "%.32s" "${NAME_PREFIX}-alb")"
LB_ARN="$(aws elbv2 describe-load-balancers --region "$REGION" --names "$LB_NAME" --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null || true)"
if [[ -n "$LB_ARN" && "$LB_ARN" != "None" ]]; then
  import_if_needed "aws_lb.app" "$LB_ARN"

  HTTP_LISTENER_ARN="$(aws elbv2 describe-listeners --region "$REGION" --load-balancer-arn "$LB_ARN" --query 'Listeners[?Port==`80`].ListenerArn | [0]' --output text 2>/dev/null || true)"
  if [[ -n "$HTTP_LISTENER_ARN" && "$HTTP_LISTENER_ARN" != "None" ]]; then
    import_if_needed "aws_lb_listener.http" "$HTTP_LISTENER_ARN"

    API_HTTP_RULE_ARN="$(aws elbv2 describe-rules --region "$REGION" --listener-arn "$HTTP_LISTENER_ARN" --query 'Rules[?Priority==`10`].RuleArn | [0]' --output text 2>/dev/null || true)"
    if [[ -n "$API_HTTP_RULE_ARN" && "$API_HTTP_RULE_ARN" != "None" ]]; then
      import_if_needed "aws_lb_listener_rule.api_http" "$API_HTTP_RULE_ARN"
    else
      echo "HTTP API listener rule not found, Terraform will create priority 10 rule"
    fi
  else
    echo "HTTP listener not found, Terraform will create it"
  fi
else
  echo "ALB not found, Terraform will create: $LB_NAME"
fi

target_groups=(
  "$(printf "%.32s" "${NAME_PREFIX}-api"):aws_lb_target_group.api"
  "$(printf "%.32s" "${NAME_PREFIX}-frontend"):aws_lb_target_group.frontend"
)

for item in "${target_groups[@]}"; do
  name="${item%%:*}"
  resource="${item#*:}"
  tg_arn="$(aws elbv2 describe-target-groups --region "$REGION" --names "$name" --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null || true)"
  if [[ -n "$tg_arn" && "$tg_arn" != "None" ]]; then
    import_if_needed "$resource" "$tg_arn"
  else
    echo "Target group not found, Terraform will create: $name"
  fi
done
