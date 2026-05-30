output "alb_dns_name" {
  description = "Public ALB DNS name."
  value       = aws_lb.app.dns_name
}

output "api_url" {
  description = "API base URL configured for the frontend."
  value       = local.api_url
}

output "backend_ecr_repository_url" {
  description = "Backend ECR repository."
  value       = aws_ecr_repository.backend.repository_url
}

output "frontend_ecr_repository_url" {
  description = "Frontend ECR repository."
  value       = aws_ecr_repository.frontend.repository_url
}

output "agent_core_ecr_repository_url" {
  description = "Agent Core ECR repository."
  value       = aws_ecr_repository.agent_core.repository_url
}

output "agent_core_codebuild_project_name" {
  description = "CodeBuild project that builds and pushes the AgentCore arm64 image."
  value       = aws_codebuild_project.agent_core_image.name
}

output "agent_core_codebuild_source_bucket" {
  description = "S3 bucket used by GitHub Actions to hand source archives to CodeBuild."
  value       = aws_s3_bucket.codebuild_sources.bucket
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.app.name
}

output "s3_bucket_name" {
  description = "Article image bucket used by the app."
  value       = local.s3_bucket_name
}

output "app_secret_arn" {
  description = "Secrets Manager ARN used by ECS tasks."
  value       = local.app_secret_arn
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint."
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "agent_core_runtime_arn" {
  description = "Terraform-managed Bedrock AgentCore Runtime ARN."
  value       = aws_bedrockagentcore_agent_runtime.agent_core.agent_runtime_arn
}

output "agent_core_memory_id" {
  description = "Terraform-managed Bedrock AgentCore Memory ID."
  value       = aws_bedrockagentcore_memory.agent_core.id
}

output "agent_core_browser_id" {
  description = "Terraform-managed Bedrock AgentCore Browser ID."
  value       = aws_bedrockagentcore_browser.agent_core.browser_id
}

output "agent_core_code_interpreter_id" {
  description = "Terraform-managed Bedrock AgentCore Code Interpreter ID."
  value       = aws_bedrockagentcore_code_interpreter.agent_core.code_interpreter_id
}

output "agentcore_runtime_role_arn" {
  description = "IAM role ARN for the AgentCore Runtime."
  value       = aws_iam_role.agentcore_runtime.arn
}

output "agentcore_memory_role_arn" {
  description = "IAM role ARN for AgentCore Memory."
  value       = aws_iam_role.agentcore_memory.arn
}

# ============================================================================
# CLUSTERING INFRASTRUCTURE OUTPUTS
# ============================================================================

output "clustering_task_definition_arn" {
  description = "ARN of the clustering worker ECS task definition."
  value       = aws_ecs_task_definition.clustering.arn
}

output "clustering_service_name" {
  description = "Name of the clustering worker ECS service."
  value       = aws_ecs_service.clustering.name
}

output "clustering_autoscaling_group_name" {
  description = "Name of the clustering worker auto-scaling group resource ID."
  value       = aws_appautoscaling_target.clustering.resource_id
}

output "clustering_log_group_name" {
  description = "CloudWatch log group name for clustering worker."
  value       = aws_cloudwatch_log_group.clustering.name
}

output "clustering_min_tasks" {
  description = "Minimum clustering worker task count."
  value       = var.clustering_min_count
}

output "clustering_max_tasks" {
  description = "Maximum clustering worker task count."
  value       = var.clustering_max_count
}

output "clustering_cpu_units" {
  description = "CPU units allocated per clustering task."
  value       = var.clustering_task_cpu
}

output "clustering_memory_mib" {
  description = "Memory in MiB allocated per clustering task."
  value       = var.clustering_task_memory
}
