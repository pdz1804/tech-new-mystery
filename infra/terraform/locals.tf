data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  public_subnet_ids  = var.create_vpc ? aws_subnet.public[*].id : var.existing_public_subnet_ids
  private_subnet_ids = var.create_vpc ? aws_subnet.private[*].id : length(var.existing_private_subnet_ids) > 0 ? var.existing_private_subnet_ids : var.existing_public_subnet_ids
  vpc_id             = var.create_vpc ? aws_vpc.this[0].id : var.existing_vpc_id

  s3_bucket_name = var.create_s3_bucket ? var.s3_bucket_name : var.existing_s3_bucket_name

  app_secret_arn = var.secrets_manager_arn != "" ? var.secrets_manager_arn : aws_secretsmanager_secret.app[0].arn

  table_names = toset([
    "articles",
    "users",
    "comments",
    "user_saves",
    "user_likes",
    "user_preferences",
    "news_sources",
    "pending-searches",
    "trending_articles",
    "submissions",
  ])
}
