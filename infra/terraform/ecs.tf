resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "app" {
  name = local.name_prefix
}

locals {
  redis_endpoint = aws_elasticache_replication_group.redis.primary_endpoint_address
  api_url        = var.certificate_arn != "" ? "https://${aws_lb.app.dns_name}/v1" : "http://${aws_lb.app.dns_name}/v1"

  backend_environment = [
    { name = "AWS_REGION", value = var.aws_region },
    { name = "ENVIRONMENT", value = "production" },
    { name = "DEBUG", value = "false" },
    { name = "API_V1_PREFIX", value = "/v1" },
    { name = "DYNAMODB_TABLE_PREFIX", value = var.dynamodb_table_prefix },
    { name = "S3_BUCKET", value = local.s3_bucket_name },
    { name = "S3_IMAGES_PREFIX", value = "article-images/" },
    { name = "BEDROCK_REGION", value = var.aws_region },
    { name = "BEDROCK_MODEL", value = "us.anthropic.claude-haiku-4-5-20251001-v1:0" },
    { name = "LLM_PROVIDER", value = "bedrock,openai" },
    { name = "OPENAI_MODEL", value = "gpt-4o-mini" },
    { name = "GEMINI_MODEL", value = "gemini-1.5-mini" },
    { name = "QDRANT_MODE", value = "cloud" },
    { name = "QDRANT_COLLECTION_NAME", value = var.qdrant_collection_name },
    { name = "OPENAI_EMBEDDING_MODEL", value = var.openai_embedding_model },
    { name = "AGENT_CORE_BASE_URL", value = "http://${aws_lb.agent_core.dns_name}:8080" },
    { name = "REDIS_URL", value = "redis://${local.redis_endpoint}:6379/0" },
    { name = "CELERY_BROKER_URL", value = "redis://${local.redis_endpoint}:6379/1" },
    { name = "CELERY_RESULT_BACKEND", value = "redis://${local.redis_endpoint}:6379/2" },
  ]

  backend_secrets = [
    { name = "SECRET_KEY", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.secret_key}::" },
    { name = "JWT_SECRET_KEY", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.jwt_secret_key}::" },
    { name = "OPENAI_API_KEY", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.openai_api_key}::" },
    { name = "TAVILY_API_KEY", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.tavily_api_key}::" },
    { name = "NEWSAPI_KEY", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.newsapi_key}::" },
    { name = "QDRANT_URL", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.qdrant_url}::" },
    { name = "QDRANT_API_KEY", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.qdrant_api_key}::" },
    { name = "GEMINI_API_KEY", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.gemini_api_key}::" },
    { name = "ANTHROPIC_API_KEY", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.anthropic_api_key}::" },
  ]
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name_prefix}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.backend.repository_url}:${var.backend_image_tag}"
    essential = true
    command   = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
    environment = local.backend_environment
    secrets     = local.backend_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "api"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${local.name_prefix}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn

  container_definitions = jsonencode([{
    name      = "frontend"
    image     = "${aws_ecr_repository.frontend.repository_url}:${var.frontend_image_tag}"
    essential = true
    portMappings = [{
      containerPort = 3000
      protocol      = "tcp"
    }]
    environment = [
      { name = "NODE_ENV", value = "production" },
      { name = "NEXT_PUBLIC_API_URL", value = "/v1" },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "frontend"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name_prefix}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name        = "worker"
    image       = "${aws_ecr_repository.backend.repository_url}:${var.backend_image_tag}"
    essential   = true
    command     = ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=2", "--max-tasks-per-child=5"]
    environment = local.backend_environment
    secrets     = local.backend_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "worker"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "beat" {
  family                   = "${local.name_prefix}-beat"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name        = "beat"
    image       = "${aws_ecr_repository.backend.repository_url}:${var.backend_image_tag}"
    essential   = true
    command     = ["celery", "-A", "app.workers.celery_app", "beat", "--loglevel=info"]
    environment = local.backend_environment
    secrets     = local.backend_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "beat"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "api"
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.public_subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener_rule.api_http]
}

resource "aws_ecs_service" "frontend" {
  name            = "frontend"
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.frontend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.public_subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "worker" {
  name            = "worker"
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.public_subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }
}

resource "aws_ecs_service" "beat" {
  name            = "beat"
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.beat.arn
  desired_count   = var.beat_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.public_subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }
}

# CloudWatch Alarms for Worker Service Monitoring
resource "aws_cloudwatch_metric_alarm" "worker_memory_high" {
  alarm_name          = "${local.name_prefix}-worker-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 70
  alarm_description   = "Alert when worker memory utilization exceeds 70% (healthy threshold with 2GB upgrade)"
  dimensions = {
    ServiceName = aws_ecs_service.worker.name
    ClusterName = aws_ecs_cluster.app.name
  }
  treat_missing_data = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "worker_cpu_sustained_high" {
  alarm_name          = "${local.name_prefix}-worker-cpu-sustained-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when worker CPU sustained > 80% for 3 minutes (indicates need for concurrency increase or horizontal scaling)"
  dimensions = {
    ServiceName = aws_ecs_service.worker.name
    ClusterName = aws_ecs_cluster.app.name
  }
  treat_missing_data = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "worker_task_count_anomaly" {
  alarm_name          = "${local.name_prefix}-worker-task-count-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RunningCount"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 0.5
  alarm_description   = "Alert when worker running task count drops (indicates task failures or crash loop)"
  dimensions = {
    ServiceName = aws_ecs_service.worker.name
    ClusterName = aws_ecs_cluster.app.name
  }
  treat_missing_data = "breaching"
}

# Agent Core Runtime Task Definition
resource "aws_ecs_task_definition" "agent_core" {
  family                   = "${local.name_prefix}-agent-core"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.agent_core_cpu
  memory                   = var.agent_core_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "agent-core"
    image     = "${aws_ecr_repository.agent_core.repository_url}:${var.agent_core_image_tag}"
    essential = true
    command   = ["python", "-m", "agent_core.server"]
    portMappings = [{
      containerPort = 8080
      protocol      = "tcp"
    }]
    environment = [
      { name = "AWS_REGION", value = var.aws_region },
      { name = "ENVIRONMENT", value = "production" },
      { name = "DEBUG", value = "false" },
      { name = "BEDROCK_REGION", value = var.aws_region },
      { name = "AGENT_MODEL", value = var.agent_core_model },
      { name = "TOOL_TIMEOUT", value = tostring(var.agent_core_tool_timeout) },
      { name = "BROWSER_TIMEOUT", value = "60" },
      { name = "CODE_INTERPRETER_TIMEOUT", value = "60" },
      { name = "BROWSER_IDENTIFIER", value = "aws.browser.v1" },
      { name = "CODE_INTERPRETER_IDENTIFIER", value = "aws.codeinterpreter.v1" },
      { name = "QDRANT_MODE", value = "cloud" },
      { name = "QDRANT_COLLECTION_NAME", value = var.qdrant_collection_name },
      { name = "OPENAI_EMBEDDING_MODEL", value = var.openai_embedding_model },
      { name = "MAX_SEARCH_RESULTS", value = "8" },
    ]
    secrets = [
      { name = "OPENAI_API_KEY", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.openai_api_key}::" },
      { name = "QDRANT_URL", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.qdrant_url}::" },
      { name = "QDRANT_API_KEY", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.qdrant_api_key}::" },
      # MEMORY_ID: optional — set to AWS Bedrock AgentCore Memory resource ID after provisioning
      { name = "MEMORY_ID", valueFrom = "${local.app_secret_arn}:${var.secret_json_keys.agent_core_memory_id}::" },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.agent_core.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "agent-core"
      }
    }
  }])
}

# Agent Core Service
resource "aws_ecs_service" "agent_core" {
  name            = "agent-core"
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.agent_core.arn
  desired_count   = var.agent_core_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.public_subnet_ids
    security_groups  = [aws_security_group.agent_core.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.agent_core.arn
    container_name   = "agent-core"
    container_port   = 8080
  }

  depends_on = [aws_lb_listener.agent_core]
}

# Auto-scaling for Agent Core
resource "aws_appautoscaling_target" "agent_core" {
  max_capacity       = var.agent_core_max_count
  min_capacity       = var.agent_core_min_count
  resource_id        = "service/${aws_ecs_cluster.app.name}/${aws_ecs_service.agent_core.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "agent_core_cpu" {
  name               = "${local.name_prefix}-agent-core-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.agent_core.resource_id
  scalable_dimension = aws_appautoscaling_target.agent_core.scalable_dimension
  service_namespace  = aws_appautoscaling_target.agent_core.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

resource "aws_appautoscaling_policy" "agent_core_memory" {
  name               = "${local.name_prefix}-agent-core-memory"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.agent_core.resource_id
  scalable_dimension = aws_appautoscaling_target.agent_core.scalable_dimension
  service_namespace  = aws_appautoscaling_target.agent_core.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value = 75.0
  }
}

# CloudWatch Log Group for Agent Core
resource "aws_cloudwatch_log_group" "agent_core" {
  name              = "/ecs/${local.name_prefix}-agent-core"
  retention_in_days = 30
}

# CloudWatch Alarms for Agent Core
resource "aws_cloudwatch_metric_alarm" "agent_core_memory_high" {
  alarm_name          = "${local.name_prefix}-agent-core-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Alert when Agent Core memory utilization exceeds 85%"
  dimensions = {
    ServiceName = aws_ecs_service.agent_core.name
    ClusterName = aws_ecs_cluster.app.name
  }
  treat_missing_data = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "agent_core_cpu_high" {
  alarm_name          = "${local.name_prefix}-agent-core-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when Agent Core CPU utilization exceeds 80% for 2 minutes"
  dimensions = {
    ServiceName = aws_ecs_service.agent_core.name
    ClusterName = aws_ecs_cluster.app.name
  }
  treat_missing_data = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "agent_core_unhealthy_hosts" {
  alarm_name          = "${local.name_prefix}-agent-core-unhealthy"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 0
  alarm_description   = "Alert when Agent Core has unhealthy targets"
  dimensions = {
    TargetGroup  = aws_lb_target_group.agent_core.arn_suffix
    LoadBalancer = aws_lb.agent_core.arn_suffix
  }
  treat_missing_data = "notBreaching"
}
