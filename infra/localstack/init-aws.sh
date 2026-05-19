#!/bin/bash
set -e

echo "Initializing LocalStack DynamoDB tables..."

AWS_CMD="aws --endpoint-url=http://localhost:4566 --region ap-southeast-1"

# Create DynamoDB Tables using JSON format for proper parameter parsing
echo "Creating users table..."
$AWS_CMD dynamodb create-table \
  --table-name users \
  --attribute-definitions '[{"AttributeName":"user_id","AttributeType":"S"},{"AttributeName":"username","AttributeType":"S"}]' \
  --key-schema '[{"AttributeName":"user_id","KeyType":"HASH"}]' \
  --global-secondary-indexes '[{"IndexName":"username-index","KeySchema":[{"AttributeName":"username","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}}]' \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 || true

echo "Creating articles table..."
$AWS_CMD dynamodb create-table \
  --table-name articles \
  --attribute-definitions '[{"AttributeName":"article_id","AttributeType":"S"},{"AttributeName":"slug","AttributeType":"S"},{"AttributeName":"source_id","AttributeType":"S"},{"AttributeName":"published_at","AttributeType":"N"}]' \
  --key-schema '[{"AttributeName":"article_id","KeyType":"HASH"}]' \
  --global-secondary-indexes '[{"IndexName":"slug-index","KeySchema":[{"AttributeName":"slug","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}},{"IndexName":"source-date-index","KeySchema":[{"AttributeName":"source_id","KeyType":"HASH"},{"AttributeName":"published_at","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}}]' \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 || true

echo "Creating news_sources table..."
$AWS_CMD dynamodb create-table \
  --table-name news_sources \
  --attribute-definitions '[{"AttributeName":"source_id","AttributeType":"S"}]' \
  --key-schema '[{"AttributeName":"source_id","KeyType":"HASH"}]' \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1 || true

echo "Creating comments table..."
$AWS_CMD dynamodb create-table \
  --table-name comments \
  --attribute-definitions '[{"AttributeName":"comment_id","AttributeType":"S"},{"AttributeName":"article_id","AttributeType":"S"},{"AttributeName":"created_at","AttributeType":"N"}]' \
  --key-schema '[{"AttributeName":"comment_id","KeyType":"HASH"}]' \
  --global-secondary-indexes '[{"IndexName":"article-date-index","KeySchema":[{"AttributeName":"article_id","KeyType":"HASH"},{"AttributeName":"created_at","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}}]' \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 || true

echo "Creating user_saves table..."
$AWS_CMD dynamodb create-table \
  --table-name user_saves \
  --attribute-definitions '[{"AttributeName":"user_id","AttributeType":"S"},{"AttributeName":"article_id","AttributeType":"S"}]' \
  --key-schema '[{"AttributeName":"user_id","KeyType":"HASH"},{"AttributeName":"article_id","KeyType":"RANGE"}]' \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 || true

echo "Creating submissions table..."
$AWS_CMD dynamodb create-table \
  --table-name submissions \
  --attribute-definitions '[{"AttributeName":"submission_id","AttributeType":"S"},{"AttributeName":"user_id","AttributeType":"S"},{"AttributeName":"submitted_at","AttributeType":"N"}]' \
  --key-schema '[{"AttributeName":"submission_id","KeyType":"HASH"}]' \
  --global-secondary-indexes '[{"IndexName":"user-date-index","KeySchema":[{"AttributeName":"user_id","KeyType":"HASH"},{"AttributeName":"submitted_at","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}}]' \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 || true

echo "Creating user_preferences table..."
$AWS_CMD dynamodb create-table \
  --table-name user_preferences \
  --attribute-definitions '[{"AttributeName":"user_id","AttributeType":"S"}]' \
  --key-schema '[{"AttributeName":"user_id","KeyType":"HASH"}]' \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1 || true

echo "Creating trending_articles table..."
$AWS_CMD dynamodb create-table \
  --table-name trending_articles \
  --attribute-definitions '[{"AttributeName":"trending_id","AttributeType":"S"}]' \
  --key-schema '[{"AttributeName":"trending_id","KeyType":"HASH"}]' \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1 || true

echo "✓ All tables created successfully!"
