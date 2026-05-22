resource "aws_s3_bucket" "articles" {
  count  = var.create_s3_bucket ? 1 : 0
  bucket = local.s3_bucket_name
}

resource "aws_s3_bucket_public_access_block" "articles" {
  count                   = var.create_s3_bucket ? 1 : 0
  bucket                  = aws_s3_bucket.articles[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "articles" {
  count  = var.create_s3_bucket ? 1 : 0
  bucket = aws_s3_bucket.articles[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "articles" {
  count  = var.create_s3_bucket ? 1 : 0
  bucket = aws_s3_bucket.articles[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "articles" {
  count  = var.create_s3_bucket ? 1 : 0
  bucket = aws_s3_bucket.articles[0].id

  rule {
    id     = "expire-old-noncurrent-versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}
