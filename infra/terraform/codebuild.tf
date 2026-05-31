locals {
  agent_core_build_source_bucket = "${local.name_prefix}-codebuild-sources-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "codebuild_sources" {
  bucket = local.agent_core_build_source_bucket
}

resource "aws_s3_bucket_public_access_block" "codebuild_sources" {
  bucket                  = aws_s3_bucket.codebuild_sources.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "codebuild_sources" {
  bucket = aws_s3_bucket.codebuild_sources.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "codebuild_sources" {
  bucket = aws_s3_bucket.codebuild_sources.id

  rule {
    id     = "expire-build-sources"
    status = "Enabled"

    filter {
      prefix = "agent-core/"
    }

    expiration {
      days = 7
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

resource "aws_iam_role" "codebuild_agent_core" {
  name = "${local.name_prefix}-agent-core-codebuild"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "codebuild.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

resource "aws_iam_role_policy" "codebuild_agent_core" {
  name = "${local.name_prefix}-agent-core-codebuild"
  role = aws_iam_role.codebuild_agent_core.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/codebuild/${local.name_prefix}-agent-core-arm64-image*"
      },
      {
        Sid      = "ReadBuildSource"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.codebuild_sources.arn}/agent-core/*"
      },
      {
        Sid      = "ListBuildSourceBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.codebuild_sources.arn
      },
      {
        Sid      = "ECRAuth"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "PushAgentCoreImage"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart"
        ]
        Resource = aws_ecr_repository.agent_core.arn
      }
    ]
  })
}

resource "aws_codebuild_project" "agent_core_image" {
  name          = "${local.name_prefix}-agent-core-arm64-image"
  description   = "Build and push the AgentCore runtime image on native arm64 CodeBuild compute."
  service_role  = aws_iam_role.codebuild_agent_core.arn
  build_timeout = 60

  artifacts {
    type = "NO_ARTIFACTS"
  }

  cache {
    type  = "LOCAL"
    modes = ["LOCAL_DOCKER_LAYER_CACHE", "LOCAL_SOURCE_CACHE"]
  }

  environment {
    type                        = "ARM_CONTAINER"
    image                       = "aws/codebuild/amazonlinux-aarch64-standard:3.0"
    compute_type                = "BUILD_GENERAL1_LARGE"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }

    environment_variable {
      name  = "ECR_REPOSITORY_URI"
      value = aws_ecr_repository.agent_core.repository_url
    }
  }

  source {
    type      = "S3"
    location  = "${aws_s3_bucket.codebuild_sources.bucket}/agent-core/source.zip"
    buildspec = <<-BUILDSPEC
      version: 0.2

      phases:
        pre_build:
          commands:
            - aws ecr get-login-password --region "$AWS_DEFAULT_REGION" | docker login --username AWS --password-stdin "$ECR_REPOSITORY_URI"
            - IMAGE_TAG="$${IMAGE_TAG:-latest}"
        build:
          commands:
            - docker build --platform linux/arm64 -f infra/docker/agent-core.Dockerfile -t "$ECR_REPOSITORY_URI:$IMAGE_TAG" -t "$ECR_REPOSITORY_URI:latest" .
        post_build:
          commands:
            - docker push "$ECR_REPOSITORY_URI:$IMAGE_TAG"
            - docker push "$ECR_REPOSITORY_URI:latest"
      BUILDSPEC
  }
}
