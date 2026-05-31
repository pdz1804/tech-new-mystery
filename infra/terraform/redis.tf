resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name_prefix}-redis"
  subnet_ids = local.private_subnet_ids

  lifecycle {
    ignore_changes = [subnet_ids]
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = substr("${local.name_prefix}-redis", 0, 40)
  description                = "Redis broker/cache for ${local.name_prefix}"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = var.redis_node_type
  num_cache_clusters         = 1
  automatic_failover_enabled = false
  multi_az_enabled           = false
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = false
}
