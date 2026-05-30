resource "aws_dynamodb_table" "users" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "username"
    type = "S"
  }

  global_secondary_index {
    name            = "username-index"
    hash_key        = "username"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "articles" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}articles"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "article_id"

  attribute {
    name = "article_id"
    type = "S"
  }

  attribute {
    name = "slug"
    type = "S"
  }

  attribute {
    name = "source_id"
    type = "S"
  }

  attribute {
    name = "published_at"
    type = "N"
  }

  global_secondary_index {
    name            = "slug-index"
    hash_key        = "slug"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "source-date-index"
    hash_key        = "source_id"
    range_key       = "published_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "comments" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}comments"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "comment_id"

  attribute {
    name = "comment_id"
    type = "S"
  }

  attribute {
    name = "article_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "N"
  }

  global_secondary_index {
    name            = "article-date-index"
    hash_key        = "article_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "user_saves" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}user_saves"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "article_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "article_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "user_likes" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}user_likes"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "article_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "article_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "user_preferences" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}user_preferences"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "news_sources" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}news_sources"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "source_id"

  attribute {
    name = "source_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "pending_searches" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}pending-searches"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "search_id"

  attribute {
    name = "search_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "trending_articles" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}trending_articles"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "trending_id"

  attribute {
    name = "trending_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "submissions" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}submissions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "submission_id"

  attribute {
    name = "submission_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "submitted_at"
    type = "N"
  }

  global_secondary_index {
    name            = "user-date-index"
    hash_key        = "user_id"
    range_key       = "submitted_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "conversation_sessions" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}conversation_sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "session_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "last_message_at"
    type = "N"
  }

  global_secondary_index {
    name            = "user-last-message-index"
    hash_key        = "user_id"
    range_key       = "last_message_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "conversation_messages" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}conversation_messages"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"
  range_key    = "message_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "message_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  global_secondary_index {
    name            = "session-timestamp-index"
    hash_key        = "session_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "chat_user_preferences" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}chat_user_preferences"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "article_clusters" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}article_clusters"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cluster_id"
  range_key    = "article_id"

  attribute {
    name = "cluster_id"
    type = "S"
  }

  attribute {
    name = "article_id"
    type = "S"
  }

  global_secondary_index {
    name            = "article_id-index"
    hash_key        = "article_id"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "cluster_metadata" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}cluster_metadata"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cluster_id"

  attribute {
    name = "cluster_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "article_embeddings" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}article_embeddings"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "article_id"

  attribute {
    name = "article_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }
}

# Clustering Evaluation Results Table
# Stores quality metrics (silhouette, davies-bouldin, calinski-harabasz) for k-value evaluation
# PK: evaluation_id (UUID format "eval-YYYY-MM-DD-HH-MM")
# GSI: run_timestamp for querying evaluation history (recent evaluations first)
# TTL: 30 days on ttl attribute for automatic cleanup of old evaluation results
resource "aws_dynamodb_table" "clustering_evaluation" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}clustering_evaluation"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "evaluation_id"

  attribute {
    name = "evaluation_id"
    type = "S"
  }

  attribute {
    name = "run_timestamp"
    type = "N"
  }

  # GSI for querying evaluations by run_timestamp (most recent first)
  # Enables efficient retrieval of latest evaluation results
  global_secondary_index {
    name            = "run_timestamp-index"
    hash_key        = "run_timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }
}

# Clustering Parameters Table
# Admin configuration for clustering evaluation weights and thresholds
# PK: param_id (string: "default" - single-row configuration)
# No TTL - this is admin configuration, not time-sensitive data
# Stores: metric weights (silhouette, davies-bouldin, calinski-harabasz),
#         quality thresholds, min cluster size, min samples, last_updated timestamp
resource "aws_dynamodb_table" "clustering_params" {
  count        = var.create_dynamodb_tables ? 1 : 0
  name         = "${var.dynamodb_table_prefix}clustering_params"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "param_id"

  attribute {
    name = "param_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}
