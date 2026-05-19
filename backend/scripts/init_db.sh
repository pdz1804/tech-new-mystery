#!/bin/bash

# Initialize DynamoDB tables on container startup
# This script runs before the FastAPI app starts

set -e

echo "Initializing DynamoDB tables..."

# Wait for DynamoDB/LocalStack to be ready
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
  if python -c "import boto3; client = boto3.client('dynamodb', endpoint_url='${DYNAMODB_ENDPOINT_URL:-http://localstack:4566}', region_name='${AWS_REGION:-us-east-1}'); client.list_tables()" 2>/dev/null; then
    echo "✓ DynamoDB is ready"
    break
  fi

  attempt=$((attempt + 1))
  echo "Waiting for DynamoDB... (attempt $attempt/$max_attempts)"
  sleep 2
done

if [ $attempt -eq $max_attempts ]; then
  echo "✗ DynamoDB failed to start in time"
  exit 1
fi

# Create tables
python scripts/create_tables_boto3.py

echo "✓ Database initialization complete"
