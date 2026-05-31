#!/bin/bash
set -e

cd "$(dirname "$0")/../infra/terraform"

echo "=== Importing existing AWS resources into Terraform state ==="

# DynamoDB tables
echo "Importing DynamoDB tables..."
terraform import aws_dynamodb_table.users[0] users || true
terraform import aws_dynamodb_table.articles[0] articles || true
terraform import aws_dynamodb_table.comments[0] comments || true
terraform import aws_dynamodb_table.user_saves[0] user_saves || true
terraform import aws_dynamodb_table.user_likes[0] user_likes || true
terraform import aws_dynamodb_table.user_preferences[0] user_preferences || true
terraform import aws_dynamodb_table.news_sources[0] news_sources || true
terraform import aws_dynamodb_table.pending_searches[0] pending_searches || true
terraform import aws_dynamodb_table.trending_articles[0] trending_articles || true
terraform import aws_dynamodb_table.submissions[0] submissions || true
terraform import aws_dynamodb_table.conversation_sessions[0] conversation_sessions || true
terraform import aws_dynamodb_table.conversation_messages[0] conversation_messages || true
terraform import aws_dynamodb_table.chat_user_preferences[0] chat_user_preferences || true
terraform import aws_dynamodb_table.article_clusters[0] article_clusters || true
terraform import aws_dynamodb_table.cluster_metadata[0] cluster_metadata || true
terraform import aws_dynamodb_table.article_embeddings[0] article_embeddings || true
terraform import aws_dynamodb_table.clustering_evaluation[0] clustering_evaluation || true
terraform import aws_dynamodb_table.clustering_params[0] clustering_params || true

# S3 bucket
echo "Importing S3 bucket..."
terraform import aws_s3_bucket.articles[0] tech-news-mystery-prod-articles || true

# Secrets Manager
echo "Importing Secrets Manager secret..."
terraform import aws_secretsmanager_secret.app[0] tech-news-mystery-prod-app || true

# VPC and networking
echo "Importing VPC and networking resources..."
terraform import aws_vpc.this[0] vpc-07f5f6659edf8ee09
terraform import aws_internet_gateway.this[0] igw-05aa61214e78bc2a8
terraform import aws_route_table.public[0] rtb-0f87490ec5768c59e

# Route table associations - MUST use format: subnet_id/route_table_id
echo "Importing route table associations..."
terraform import 'aws_route_table_association.public[0]' 'subnet-0e2b628b1d40866ca/rtb-0f87490ec5768c59e'
terraform import 'aws_route_table_association.public[1]' 'subnet-025e94804ee685cff/rtb-0f87490ec5768c59e'

# Public subnets
echo "Importing public subnets..."
terraform import 'aws_subnet.public[0]' subnet-0e2b628b1d40866ca
terraform import 'aws_subnet.public[1]' subnet-025e94804ee685cff

# Private subnets
echo "Importing private subnets..."
terraform import 'aws_subnet.private[0]' subnet-07d62f968936175a7
terraform import 'aws_subnet.private[1]' subnet-0d007a1c91214f5c7

echo "=== Import complete ==="
