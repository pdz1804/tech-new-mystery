# Clustering Worker Infrastructure
# Provides ECS task definition, service, auto-scaling, and monitoring
# for the dedicated clustering worker that performs article clustering jobs

# CloudWatch Log Group for Clustering Worker
resource "aws_cloudwatch_log_group" "clustering" {
  name              = "/ecs/${local.name_prefix}-clustering"
  retention_in_days = 30

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-clustering-logs"
  })
}

# ECS Task Definition for Clustering Worker
resource "aws_ecs_task_definition" "clustering" {
  family                   = "${local.name_prefix}-clustering"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.clustering_task_cpu
  memory                   = var.clustering_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "clustering"
    image     = "${aws_ecr_repository.backend.repository_url}:${var.backend_image_tag}"
    essential = true
    command = [
      "celery", "-A", "app.workers.celery_app",
      "worker",
      "--loglevel=info",
      "--concurrency=1",
      "--max-tasks-per-child=1",
      "-Q", "clustering"
    ]
    environment = local.backend_environment
    secrets     = local.backend_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.clustering.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "clustering"
      }
    }
  }])

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-clustering-task"
  })
}

# ECS Service for Clustering Worker
resource "aws_ecs_service" "clustering" {
  name            = "clustering"
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.clustering.arn
  desired_count   = var.clustering_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.public_subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-clustering-service"
  })

  depends_on = [aws_cloudwatch_log_group.clustering]
}

# Auto-Scaling Target for Clustering Service
resource "aws_appautoscaling_target" "clustering" {
  max_capacity       = var.clustering_max_count
  min_capacity       = var.clustering_min_count
  resource_id        = "service/${aws_ecs_cluster.app.name}/${aws_ecs_service.clustering.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-clustering-scaling"
  })
}

# CPU-based Auto-Scaling Policy for Clustering
resource "aws_appautoscaling_policy" "clustering_cpu" {
  name               = "${local.name_prefix}-clustering-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.clustering.resource_id
  scalable_dimension = aws_appautoscaling_target.clustering.scalable_dimension
  service_namespace  = aws_appautoscaling_target.clustering.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 600
    scale_out_cooldown = 60
  }
}

# Memory-based Auto-Scaling Policy for Clustering
resource "aws_appautoscaling_policy" "clustering_memory" {
  name               = "${local.name_prefix}-clustering-memory"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.clustering.resource_id
  scalable_dimension = aws_appautoscaling_target.clustering.scalable_dimension
  service_namespace  = aws_appautoscaling_target.clustering.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 75.0
    scale_in_cooldown  = 600
    scale_out_cooldown = 60
  }
}

# DynamoDB Backup Configuration Note:
# Backups for article_clusters, cluster_metadata, and article_embeddings tables
# are configured via point_in_time_recovery in dynamodb.tf
# PITR enables restore to any point in time within the 35-day retention window

# DynamoDB Backup Configuration for Clustering Tables
# Note: Point-in-time recovery for clustering tables is already configured in dynamodb.tf
# These are enabled on:
# - article_clusters (via point_in_time_recovery block)
# - cluster_metadata (via point_in_time_recovery block)
# - article_embeddings (via point_in_time_recovery block)
# - clustering_evaluation (via point_in_time_recovery block)
# - clustering_params (via point_in_time_recovery block)

# CloudWatch Alarms for Clustering Worker Memory
resource "aws_cloudwatch_metric_alarm" "clustering_memory_high" {
  alarm_name          = "${local.name_prefix}-clustering-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Alert when clustering worker memory exceeds 85%"

  dimensions = {
    ServiceName = aws_ecs_service.clustering.name
    ClusterName = aws_ecs_cluster.app.name
  }

  treat_missing_data = "notBreaching"
}

# CloudWatch Alarms for Clustering Worker CPU
resource "aws_cloudwatch_metric_alarm" "clustering_cpu_sustained_high" {
  alarm_name          = "${local.name_prefix}-clustering-cpu-sustained-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when clustering CPU remains > 80% for 15 minutes"

  dimensions = {
    ServiceName = aws_ecs_service.clustering.name
    ClusterName = aws_ecs_cluster.app.name
  }

  treat_missing_data = "notBreaching"
}

# CloudWatch Alarm for Clustering Task Count
resource "aws_cloudwatch_metric_alarm" "clustering_task_count_low" {
  alarm_name          = "${local.name_prefix}-clustering-task-count-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RunningCount"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 0.5
  alarm_description   = "Alert when clustering running task count drops below minimum"

  dimensions = {
    ServiceName = aws_ecs_service.clustering.name
    ClusterName = aws_ecs_cluster.app.name
  }

  treat_missing_data = "breaching"
}
