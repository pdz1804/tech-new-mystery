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
