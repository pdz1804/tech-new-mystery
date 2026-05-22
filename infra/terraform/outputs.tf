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
