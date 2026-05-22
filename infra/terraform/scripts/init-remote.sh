#!/usr/bin/env bash
set -euo pipefail

BUCKET="${BUCKET:?Set BUCKET to the Terraform state bucket name}"
LOCK_TABLE="${LOCK_TABLE:-tech-news-mystery-terraform-locks}"
REGION="${REGION:-us-west-2}"
STATE_KEY="${STATE_KEY:-tech-news-mystery/prod/terraform.tfstate}"

terraform init -reconfigure \
  -backend-config="bucket=$BUCKET" \
  -backend-config="key=$STATE_KEY" \
  -backend-config="region=$REGION" \
  -backend-config="dynamodb_table=$LOCK_TABLE" \
  -backend-config="encrypt=true"
