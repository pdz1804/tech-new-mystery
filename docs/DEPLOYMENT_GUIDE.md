# Tech News Mystery - Deployment Guide

**Version:** 1.0  
**Date:** May 18, 2026  
**Target Environment:** AWS (us-west-2)

---

## 1. Prerequisites

### AWS Account Requirements
- [ ] AWS Account with permissions for DynamoDB, Bedrock, ElastiCache, EC2/ECS, IAM
- [ ] IAM user with programmatic access (for initial setup only)
- [ ] Region: **us-west-2** (all services)

### External APIs
- [ ] OPENAI_API_KEY (from OpenAI)
- [ ] TAVILY_API_KEY (from Tavily)
- [ ] Bedrock access enabled in us-west-2

### Local Setup
- [ ] Git repository access
- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed
- [ ] Docker & Docker Compose installed

---

## 2. Local Development Setup

### Step 1: Clone Repository
```bash
git clone <repo-url>
cd Tech-News-Mystery
```

### Step 2: Backend Setup
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -e .
```

### Step 3: Environment Configuration
Create `.env` file in root:
```env
# AWS Configuration
AWS_REGION=us-west-2
ENVIRONMENT=local

# LLM Configuration
BEDROCK_REGION=us-west-2
BEDROCK_MODEL=anthropic.claude-3-5-haiku-20241022
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Search API
TAVILY_API_KEY=tvly-...

# Database & Cache (local development)
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

### Step 4: Start Containers
```bash
cd infra
docker-compose up -d

# Verify services
docker-compose ps

# Logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Step 5: Initialize Database
```bash
cd backend
python scripts/create_tables_boto3.py

# Verify tables created
aws dynamodb list-tables --region us-west-2
```

### Step 6: Verify Setup
```bash
# Health check
curl http://localhost:8000/health

# Frontend
open http://localhost:3000
```

---

## 3. AWS Infrastructure Setup

### Step 1: Create IAM Role for EC2/ECS

```bash
# Create role
aws iam create-role \
  --role-name TechNewsMysteryAppRole \
  --assume-role-policy-document file://ec2-trust-policy.json \
  --region us-west-2

# Trust policy (ec2-trust-policy.json):
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Step 2: Attach Policies

```bash
# DynamoDB Full Access
aws iam attach-role-policy \
  --role-name TechNewsMysteryAppRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess \
  --region us-west-2

# Bedrock Full Access
aws iam attach-role-policy \
  --role-name TechNewsMysteryAppRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess \
  --region us-west-2

# ElastiCache Access
aws iam attach-role-policy \
  --role-name TechNewsMysteryAppRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonElastiCacheFullAccess \
  --region us-west-2
```

### Step 3: Create DynamoDB Tables (Production)

```bash
cd backend
ENVIRONMENT=production python scripts/create_tables_boto3.py
```

Tables created:
- `articles` (on-demand, 50 GB max)
- `users` (on-demand, 10 GB max)
- `user_likes` (on-demand, 10 GB max)
- `user_saves` (on-demand, 10 GB max)
- `comments` (on-demand, 10 GB max)
- `news_sources` (on-demand, 1 GB max)

### Step 4: Set Up ElastiCache (Redis)

```bash
# Create Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id tech-news-mystery-redis \
  --engine redis \
  --cache-node-type cache.t3.small \
  --engine-version 7.0 \
  --region us-west-2 \
  --num-cache-nodes 1

# Get endpoint (wait ~10 minutes)
aws elasticache describe-cache-clusters \
  --cache-cluster-id tech-news-mystery-redis \
  --region us-west-2 \
  --show-cache-node-info
```

Update `.env` with ElastiCache endpoint:
```env
REDIS_URL=redis://<elasticache-endpoint>:6379/0
CELERY_BROKER_URL=redis://<elasticache-endpoint>:6379/1
CELERY_RESULT_BACKEND=redis://<elasticache-endpoint>:6379/2
```

### Step 5: Configure Application Secrets

**NEVER** put secrets in code or environment variables on EC2. Use AWS Systems Manager Parameter Store:

```bash
# Store API keys
aws ssm put-parameter \
  --name /tech-news-mystery/openai-api-key \
  --value "sk-..." \
  --type SecureString \
  --region us-west-2

aws ssm put-parameter \
  --name /tech-news-mystery/tavily-api-key \
  --value "tvly-..." \
  --type SecureString \
  --region us-west-2
```

Update application to load from Parameter Store:
```python
import boto3

ssm = boto3.client('ssm', region_name='us-west-2')

openai_key = ssm.get_parameter(
    Name='/tech-news-mystery/openai-api-key',
    WithDecryption=True
)['Parameter']['Value']
```

---

## 4. Docker Image Build & Push

### Step 1: Build Images

```bash
# Backend
docker build -f backend/Dockerfile -t tech-news-mystery-backend:1.0 ./backend

# Frontend
docker build -f frontend/Dockerfile -t tech-news-mystery-frontend:1.0 ./frontend
```

### Step 2: Push to ECR

```bash
# Create repositories
aws ecr create-repository \
  --repository-name tech-news-mystery-backend \
  --region us-west-2

aws ecr create-repository \
  --repository-name tech-news-mystery-frontend \
  --region us-west-2

# Get login token
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com

# Tag and push
docker tag tech-news-mystery-backend:1.0 <account-id>.dkr.ecr.us-west-2.amazonaws.com/tech-news-mystery-backend:1.0
docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/tech-news-mystery-backend:1.0

docker tag tech-news-mystery-frontend:1.0 <account-id>.dkr.ecr.us-west-2.amazonaws.com/tech-news-mystery-frontend:1.0
docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/tech-news-mystery-frontend:1.0
```

---

## 5. ECS Deployment (Recommended)

### Step 1: Create ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name tech-news-mystery \
  --region us-west-2
```

### Step 2: Create Task Definition

Create `backend-task-definition.json`:
```json
{
  "family": "tech-news-mystery-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<account-id>.dkr.ecr.us-west-2.amazonaws.com/tech-news-mystery-backend:1.0",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "us-west-2"
        },
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:ssm:us-west-2:<account>:parameter/tech-news-mystery/openai-api-key"
        }
      ]
    }
  ],
  "executionRoleArn": "arn:aws:iam::<account>:role/ecsTaskExecutionRole"
}
```

### Step 3: Register & Deploy

```bash
aws ecs register-task-definition \
  --cli-input-json file://backend-task-definition.json \
  --region us-west-2

aws ecs create-service \
  --cluster tech-news-mystery \
  --service-name backend \
  --task-definition tech-news-mystery-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --region us-west-2
```

---

## 6. EC2 Deployment (Alternative)

### Step 1: Launch EC2 Instance

```bash
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --iam-instance-profile Name=TechNewsMysteryAppRole \
  --security-groups default \
  --region us-west-2
```

### Step 2: Configure Instance

```bash
# SSH into instance
ssh -i key.pem ec2-user@<instance-ip>

# Install dependencies
sudo yum update -y
sudo yum install python3 docker git -y

# Clone repository
git clone <repo-url>
cd Tech-News-Mystery

# Build and run
docker-compose -f infra/docker-compose.yml up -d
```

---

## 7. Load Balancer & DNS

### Step 1: Create ALB (Application Load Balancer)

```bash
aws elbv2 create-load-balancer \
  --name tech-news-mystery-alb \
  --subnets subnet-12345 subnet-67890 \
  --security-groups sg-12345 \
  --scheme internet-facing \
  --region us-west-2
```

### Step 2: Create Target Groups

```bash
# Backend
aws elbv2 create-target-group \
  --name backend-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-12345 \
  --region us-west-2

# Frontend
aws elbv2 create-target-group \
  --name frontend-targets \
  --protocol HTTP \
  --port 3000 \
  --vpc-id vpc-12345 \
  --region us-west-2
```

### Step 3: Create Listeners & Rules

```bash
aws elbv2 create-listener \
  --load-balancer-arn <alb-arn> \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=<target-group-arn> \
  --region us-west-2
```

---

## 8. CloudFront CDN

### Step 1: Create Distribution

```bash
# For frontend assets
aws cloudfront create-distribution \
  --origin-domain-name <alb-dns> \
  --default-root-object index.html \
  --region us-west-2
```

---

## 9. Monitoring & Logging

### CloudWatch Logs

```bash
# View logs
aws logs tail /aws/ecs/tech-news-mystery-backend --follow --region us-west-2

# Set up log groups
aws logs create-log-group --log-group-name /tech-news-mystery/backend --region us-west-2
aws logs create-log-group --log-group-name /tech-news-mystery/frontend --region us-west-2
```

### CloudWatch Alarms

```bash
# High API latency
aws cloudwatch put-metric-alarm \
  --alarm-name backend-high-latency \
  --alarm-description "Alert when p95 latency > 500ms" \
  --metric-name Latency \
  --namespace AWS/ELB \
  --statistic Average \
  --period 300 \
  --threshold 500 \
  --comparison-operator GreaterThanThreshold \
  --region us-west-2
```

---

## 10. Production Checklist

Before going live:

### Security
- [ ] All secrets in Parameter Store (not in code)
- [ ] HTTPS enabled (ACM certificate)
- [ ] Security groups restricted (whitelist IPs)
- [ ] DynamoDB encryption at rest enabled
- [ ] Backups configured

### Performance
- [ ] Load testing completed (1000+ concurrent users)
- [ ] Database indexes verified
- [ ] Cache hit ratio > 80%
- [ ] API p95 latency < 500ms

### Monitoring
- [ ] CloudWatch alarms configured
- [ ] Log retention set (30 days)
- [ ] Health checks enabled
- [ ] Metrics dashboard created

### Deployment
- [ ] Rollback plan documented
- [ ] Blue/green deployment tested
- [ ] Database migration scripts tested
- [ ] Disaster recovery plan in place

---

## 11. Rollback Procedure

```bash
# Rollback to previous ECS task definition
aws ecs update-service \
  --cluster tech-news-mystery \
  --service backend \
  --task-definition tech-news-mystery-backend:1 \
  --region us-west-2

# Rollback database
aws dynamodb restore-table-from-backup \
  --target-table-name articles \
  --backup-arn <backup-arn> \
  --region us-west-2
```

---

## 12. Scaling & Performance Tuning

### DynamoDB Scaling
```bash
# Monitor consumed capacity
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=articles \
  --start-time 2026-05-18T00:00:00Z \
  --end-time 2026-05-19T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### Redis Optimization
```bash
# Monitor cache hit ratio
redis-cli INFO stats | grep hits
```

### ECS Auto-Scaling
```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name tech-news-mystery-asg \
  --service-name backend \
  --desired-capacity 2 \
  --max-size 10 \
  --min-size 1 \
  --region us-west-2
```

---

## 13. Troubleshooting

### Backend not responding
```bash
# Check logs
aws logs tail /aws/ecs/tech-news-mystery-backend --follow

# Check task status
aws ecs describe-tasks --cluster tech-news-mystery --tasks <task-arn>
```

### Database connection errors
```bash
# Verify DynamoDB tables
aws dynamodb list-tables --region us-west-2

# Check security group rules
aws ec2 describe-security-groups --region us-west-2
```

### Redis connection issues
```bash
# Test Redis connection
redis-cli -h <elasticache-endpoint> ping
```

---

**Version:** 1.0  
**Last Updated:** May 18, 2026  
**Maintained By:** DevOps Team  
**Emergency Contact:** devops@example.com
