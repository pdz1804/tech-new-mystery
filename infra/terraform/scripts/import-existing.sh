#!/usr/bin/env bash
set -euo pipefail

REGION="${REGION:-us-west-2}"
TABLE_PREFIX="${TABLE_PREFIX:-tech-news-}"
S3_BUCKET="${S3_BUCKET:-tech-news-articles-381492273521}"

tables=(
  "users:aws_dynamodb_table.users[0]"
  "articles:aws_dynamodb_table.articles[0]"
  "comments:aws_dynamodb_table.comments[0]"
  "user_saves:aws_dynamodb_table.user_saves[0]"
  "user_likes:aws_dynamodb_table.user_likes[0]"
  "user_preferences:aws_dynamodb_table.user_preferences[0]"
  "news_sources:aws_dynamodb_table.news_sources[0]"
  "pending-searches:aws_dynamodb_table.pending_searches[0]"
  "trending_articles:aws_dynamodb_table.trending_articles[0]"
  "submissions:aws_dynamodb_table.submissions[0]"
)

in_state() {
  terraform state show "$1" >/dev/null 2>&1
}

for item in "${tables[@]}"; do
  name="${item%%:*}"
  resource="${item#*:}"
  full_name="${TABLE_PREFIX}${name}"
  if aws dynamodb describe-table --region "$REGION" --table-name "$full_name" >/dev/null 2>&1; then
    if in_state "$resource"; then
      echo "Already in Terraform state: $full_name"
    else
      echo "Importing existing DynamoDB table: $full_name"
      terraform import "$resource" "$full_name"
    fi
  else
    echo "DynamoDB table not found, Terraform will create: $full_name"
  fi
done

if [[ -n "$S3_BUCKET" ]]; then
  if aws s3api head-bucket --bucket "$S3_BUCKET" >/dev/null 2>&1; then
    if in_state "aws_s3_bucket.articles[0]"; then
      echo "Already in Terraform state: $S3_BUCKET"
    else
      echo "Importing existing S3 bucket: $S3_BUCKET"
      terraform import "aws_s3_bucket.articles[0]" "$S3_BUCKET"
    fi
  else
    echo "S3 bucket not found, Terraform will create: $S3_BUCKET"
  fi
fi
