# CloudWatch Monitoring for Clustering Infrastructure
# Includes custom metrics, dashboards, and alarms for clustering job monitoring

# ============================================================================
# CUSTOM METRICS NAMESPACE
# ============================================================================

# CloudWatch Log Group for Custom Metrics (filtering)
# Custom metrics are emitted by clustering tasks and ingested via this log group
locals {
  clustering_metrics_namespace = "${local.name_prefix}/clustering"
}

# ============================================================================
# CLUSTERING JOB SUCCESS/FAILURE METRICS
# ============================================================================

# Metric Alarm: Clustering Job Failure Rate
# Triggers when job failure rate exceeds 10% over a 1-hour period
resource "aws_cloudwatch_metric_alarm" "clustering_job_failure_rate" {
  alarm_name          = "${local.name_prefix}-clustering-job-failure-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "JobFailureCount"
  namespace           = local.clustering_metrics_namespace
  period              = 3600 # 1 hour
  statistic           = "Sum"
  threshold           = 2 # More than 2 failures in an hour
  alarm_description   = "Alert when clustering job failure count exceeds threshold (>10% failure rate)"
  treat_missing_data  = "notBreaching"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-clustering-job-failure-alarm"
  })
}

# Metric Alarm: Clustering Job Success Rate
resource "aws_cloudwatch_metric_alarm" "clustering_job_success_rate" {
  alarm_name          = "${local.name_prefix}-clustering-job-success-rate"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "JobSuccessCount"
  namespace           = local.clustering_metrics_namespace
  period              = 86400 # 24 hours (daily job should succeed at least once)
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Alert when clustering job has not succeeded in 24 hours"
  treat_missing_data  = "breaching"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-clustering-job-success-alarm"
  })
}

# ============================================================================
# CLUSTERING DURATION METRICS (AVG, MAX, P95)
# ============================================================================

# Metric Alarm: Clustering Duration (MAX > 30 minutes)
# Using Maximum statistic instead of p95 since p95 requires Statistics field
resource "aws_cloudwatch_metric_alarm" "clustering_duration_p95_high" {
  alarm_name          = "${local.name_prefix}-clustering-duration-p95-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ClusteringDurationSeconds"
  namespace           = local.clustering_metrics_namespace
  period              = 3600
  statistic           = "Maximum"
  threshold           = 1800 # 30 minutes in seconds
  alarm_description   = "Alert when maximum clustering duration exceeds 30 minutes"
  treat_missing_data  = "notBreaching"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-clustering-duration-p95-alarm"
  })
}

# Metric Alarm: Clustering Duration (MAX > 45 minutes)
resource "aws_cloudwatch_metric_alarm" "clustering_duration_max_high" {
  alarm_name          = "${local.name_prefix}-clustering-duration-max-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ClusteringDurationSeconds"
  namespace           = local.clustering_metrics_namespace
  period              = 3600
  statistic           = "Maximum"
  threshold           = 2700 # 45 minutes in seconds
  alarm_description   = "Alert when maximum clustering duration exceeds 45 minutes"
  treat_missing_data  = "notBreaching"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-clustering-duration-max-alarm"
  })
}

# ============================================================================
# DYNAMODB METRICS FOR CLUSTERING TABLES
# ============================================================================

# Metric Alarm: DynamoDB Read Capacity Throttling
resource "aws_cloudwatch_metric_alarm" "dynamodb_clustering_read_throttle" {
  alarm_name          = "${local.name_prefix}-dynamodb-clustering-read-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 0 # Any throttle event
  alarm_description   = "Alert when DynamoDB clustering tables experience read throttling"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.article_clusters[0].name
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-dynamodb-read-throttle-alarm"
  })
}

# Metric Alarm: DynamoDB Write Capacity Throttling
resource "aws_cloudwatch_metric_alarm" "dynamodb_clustering_write_throttle" {
  alarm_name          = "${local.name_prefix}-dynamodb-clustering-write-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 0 # Any throttle event
  alarm_description   = "Alert when DynamoDB clustering tables experience write throttling"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.article_clusters[0].name
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-dynamodb-write-throttle-alarm"
  })
}

# Metric Alarm: DynamoDB Consumed Read Capacity
resource "aws_cloudwatch_metric_alarm" "dynamodb_clustering_read_capacity_high" {
  alarm_name          = "${local.name_prefix}-dynamodb-clustering-read-capacity-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ConsumedReadCapacityUnits"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Average"
  threshold           = 100 # 100 RCU average over 5 min - indicates heavy read load
  alarm_description   = "Alert when clustering table read capacity usage is high (avg > 100 RCU)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.article_clusters[0].name
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-dynamodb-read-capacity-alarm"
  })
}

# Metric Alarm: DynamoDB Consumed Write Capacity
resource "aws_cloudwatch_metric_alarm" "dynamodb_clustering_write_capacity_high" {
  alarm_name          = "${local.name_prefix}-dynamodb-clustering-write-capacity-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ConsumedWriteCapacityUnits"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Average"
  threshold           = 50 # 50 WCU average over 5 min
  alarm_description   = "Alert when clustering table write capacity usage is high (avg > 50 WCU)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.article_clusters[0].name
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-dynamodb-write-capacity-alarm"
  })
}

# ============================================================================
# API ENDPOINT RESPONSE TIME METRICS
# ============================================================================

# Metric Alarm: Cluster Endpoint Latency (Average > 5 seconds)
resource "aws_cloudwatch_metric_alarm" "api_cluster_latency_p95" {
  alarm_name          = "${local.name_prefix}-api-cluster-latency-p95"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Average"
  threshold           = 5 # 5 seconds
  alarm_description   = "Alert when average cluster API response time exceeds 5 seconds"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TargetGroup  = aws_lb_target_group.api.arn_suffix
    LoadBalancer = aws_lb.app.arn_suffix
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-latency-p95-alarm"
  })
}

# Metric Alarm: Cluster Endpoint Latency (max > 10 seconds)
resource "aws_cloudwatch_metric_alarm" "api_cluster_latency_max" {
  alarm_name          = "${local.name_prefix}-api-cluster-latency-max"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Maximum"
  threshold           = 10 # 10 seconds
  alarm_description   = "Alert when maximum cluster API response time exceeds 10 seconds"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TargetGroup  = aws_lb_target_group.api.arn_suffix
    LoadBalancer = aws_lb.app.arn_suffix
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-latency-max-alarm"
  })
}

# ============================================================================
# API ERROR RATE METRICS (4xx, 5xx)
# ============================================================================

# Metric Alarm: API 404 Error Rate
resource "aws_cloudwatch_metric_alarm" "api_404_error_rate" {
  alarm_name          = "${local.name_prefix}-api-404-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_4XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 20 # More than 20 404s in 5 min
  alarm_description   = "Alert when 404 error rate exceeds threshold (>20 in 5 min)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TargetGroup  = aws_lb_target_group.api.arn_suffix
    LoadBalancer = aws_lb.app.arn_suffix
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-404-alarm"
  })
}

# Metric Alarm: API 5xx Server Error Rate
resource "aws_cloudwatch_metric_alarm" "api_500_error_rate" {
  alarm_name          = "${local.name_prefix}-api-500-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 5 # More than 5 500s in 5 min
  alarm_description   = "Alert when 5xx error rate exceeds threshold (>5 in 5 min)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TargetGroup  = aws_lb_target_group.api.arn_suffix
    LoadBalancer = aws_lb.app.arn_suffix
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-500-alarm"
  })
}

# ============================================================================
# DASHBOARDS
# ============================================================================

# Clustering Metrics Overview Dashboard
resource "aws_cloudwatch_dashboard" "clustering_overview" {
  dashboard_name = "${local.name_prefix}-clustering-overview"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            [local.clustering_metrics_namespace, "JobSuccessCount"],
            [".", "JobFailureCount"]
          ]
          period = 3600
          stat   = "Sum"
          region = var.aws_region
          title  = "Clustering Job Status"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            [local.clustering_metrics_namespace, "ClusteringDurationSeconds"]
          ]
          period = 3600
          stat   = "Average"
          region = var.aws_region
          title  = "Clustering Duration (seconds)"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization"],
            [".", "MemoryUtilization"]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Clustering Worker Resource Utilization"
          yAxis = {
            left = { min = 0, max = 100 }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits"],
            [".", "ConsumedWriteCapacityUnits"]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "DynamoDB Capacity Usage (Clustering Tables)"
          yAxis = {
            left = { min = 0 }
          }
        }
      }
    ]
  })
}

# API Performance Dashboard (includes cluster endpoints)
resource "aws_cloudwatch_dashboard" "api_performance" {
  dashboard_name = "${local.name_prefix}-api-performance"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime"]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "API Response Time"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "HTTPCode_Target_2XX_Count"],
            [".", "HTTPCode_Target_4XX_Count"],
            [".", "HTTPCode_Target_5XX_Count"]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "API HTTP Response Codes"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount"]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "API Request Volume"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "HealthyHostCount"],
            [".", "UnHealthyHostCount"]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "API Target Health"
          yAxis = {
            left = { min = 0 }
          }
        }
      }
    ]
  })
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "clustering_metrics_namespace" {
  description = "CloudWatch namespace for custom clustering metrics"
  value       = local.clustering_metrics_namespace
}

output "clustering_dashboard_url" {
  description = "URL to the clustering metrics dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.clustering_overview.dashboard_name}"
}

output "api_performance_dashboard_url" {
  description = "URL to the API performance dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.api_performance.dashboard_name}"
}
