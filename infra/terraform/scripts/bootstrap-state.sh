#!/usr/bin/env bash
set -euo pipefail

BUCKET="${BUCKET:?Set BUCKET to the Terraform state bucket name}"
LOCK_TABLE="${LOCK_TABLE:-tech-news-mystery-terraform-locks}"
REGION="${REGION:-us-west-2}"

if aws s3api head-bucket --bucket "$BUCKET" >/dev/null 2>&1; then
  echo "State bucket already exists: $BUCKET"
else
  echo "Creating state bucket: $BUCKET"
  aws s3api create-bucket \
    --bucket "$BUCKET" \
    --region "$REGION" \
    --create-bucket-configuration "LocationConstraint=$REGION"

  aws s3api put-bucket-versioning \
    --bucket "$BUCKET" \
    --versioning-configuration Status=Enabled

  aws s3api put-bucket-encryption \
    --bucket "$BUCKET" \
    --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

  aws s3api put-public-access-block \
    --bucket "$BUCKET" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
fi

if aws dynamodb describe-table --region "$REGION" --table-name "$LOCK_TABLE" >/dev/null 2>&1; then
  echo "Lock table already exists: $LOCK_TABLE"
else
  echo "Creating lock table: $LOCK_TABLE"
  aws dynamodb create-table \
    --region "$REGION" \
    --table-name "$LOCK_TABLE" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST

  aws dynamodb wait table-exists --region "$REGION" --table-name "$LOCK_TABLE"
fi

echo "Terraform backend bootstrap complete."
