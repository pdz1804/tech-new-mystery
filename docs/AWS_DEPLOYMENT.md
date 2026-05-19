# AWS Deployment Guide
**Last Updated:** May 18, 2026  
**Status:** Phase 4 Implementation  
**Region:** us-west-2

---

## Overview

This guide covers deploying Tech News Mystery to AWS using:
- **DynamoDB** for database (replaces LocalStack)
- **ElastiCache** for Redis (production only)
- **EC2** for backend compute
- **CloudFront** for frontend CDN
- **IAM roles** for authentication (no credentials in code)

---

## Key Principles

✅ **NO hardcoded AWS credentials**
- Use IAM roles (EC2 instance profile or ECS task role)
- boto3 automatically uses credentials from IAM role
- Never put AWS keys in environment variables

✅ **Redis Configuration**
- **Development (local):** Docker container
- **Production:** AWS ElastiCache Redis cluster

✅ **Region:** us-west-2

---

## 1. Local Development

### Setup
```bash
cd infra
docker-compose up -d
```

### Services
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Redis: localhost:6379 (Docker container)
- DynamoDB: Real AWS (reads are free tier)

### Environment Variables
```env
# backend/.env
ENVIRONMENT=local
AWS_REGION=us-west-2
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
TAVILY_API_KEY=...
```

**Note:** No AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY needed!

---

## 2. AWS Infrastructure Setup

### 2.1 DynamoDB Tables

Create tables in us-west-2:

```bash
python backend/scripts/create_dynamodb_tables.py
```

**Tables:**
- `articles` - Article data with slug GSI
- `users` - User accounts with username GSI
- `user_saves` - Saved articles (user_id + article_id)
- `user_likes` - Liked articles (user_id + article_id)
- `comments` - Article comments
- `news_sources` - News source metadata
- `user_preferences` - User preferences

**Billing Mode:** PAY_PER_REQUEST (no capacity planning)

### 2.2 IAM Role for Application

Create IAM role with policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": "arn:aws:dynamodb:us-west-2:*:table/*"
    },
    {
      "Sid": "BedrockAccess",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-haiku-20241022"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-west-2:*:log-group:*"
    }
  ]
}
```

**Steps:**
1. Go to AWS IAM Console
2. Create role → Choose EC2 service
3. Attach inline policy (above)
4. Name: `tech-news-api-role`
5. Attach to EC2 instance when launching

### 2.3 ElastiCache Redis (Optional, for production)

```bash
# Via AWS Console or AWS CLI:
aws elasticache create-cache-cluster \
  --cache-cluster-id tech-news-redis \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --engine-version 7.4 \
  --region us-west-2 \
  --num-cache-nodes 1
```

**Get endpoint:**
```bash
aws elasticache describe-cache-clusters \
  --cache-cluster-id tech-news-redis \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint'
```

Save endpoint → Add to `.env` as `ELASTICACHE_ENDPOINT`

---

## 3. Backend Configuration

### 3.1 Application Config

**File:** `backend/app/config.py`

```python
import os

class Config:
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
    
    # DynamoDB - No endpoint URL = use real AWS
    DYNAMODB_ENDPOINT_URL = None  # Important!
    # boto3 uses IAM role automatically
    
    # Redis - Conditional based on environment
    if ENVIRONMENT == "local":
        REDIS_URL = "redis://redis:6379/0"
    else:  # production
        REDIS_URL = os.getenv("ELASTICACHE_ENDPOINT", "redis://localhost:6379/0")
    
    CELERY_BROKER_URL = f"{REDIS_URL}/1"
    CELERY_RESULT_BACKEND = f"{REDIS_URL}/2"
    
    # APIs
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    BEDROCK_MODEL = "anthropic.claude-3-5-haiku-20241022"
    BEDROCK_REGION = "us-west-2"
    
    # JWT
    JWT_SECRET = os.getenv("JWT_SECRET", "change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS = 30
```

### 3.2 Docker Compose

**File:** `infra/docker-compose.yml`

```yaml
services:
  api:
    build:
      context: ../backend
      dockerfile: ../infra/docker/backend.Dockerfile
    environment:
      AWS_REGION: us-west-2
      ENVIRONMENT: ${ENVIRONMENT:-local}
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    depends_on:
      redis:
        condition: service_healthy

  celery-worker:
    environment:
      AWS_REGION: us-west-2
      ENVIRONMENT: ${ENVIRONMENT:-local}
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    depends_on:
      - redis

  redis:
    # Local development only
    image: redis:7.4-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

  # ❌ REMOVED: localstack - use real AWS
```

---

## 4. Deployment to EC2

### 4.1 Launch EC2 Instance

1. **Region:** us-west-2
2. **AMI:** Amazon Linux 2 or Ubuntu 22.04
3. **Instance Type:** t3.small (minimum)
4. **IAM Role:** Attach `tech-news-api-role` created above
5. **Security Group:** Allow ports 80, 443, 8000

### 4.2 Deploy Backend

```bash
# SSH into instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker ec2-user

# Clone repository
git clone https://github.com/your-org/tech-news-mystery.git
cd tech-news-mystery

# Create environment file
cat > backend/.env << EOF
ENVIRONMENT=production
AWS_REGION=us-west-2
ELASTICACHE_ENDPOINT=redis://your-elasticache-endpoint.cache.amazonaws.com:6379
TAVILY_API_KEY=your-tavily-key
JWT_SECRET=generate-secure-random-string
EOF

# Start services
cd infra
docker-compose up -d

# Verify
docker-compose ps
curl http://localhost:8000/health
```

### 4.3 Setup Reverse Proxy (Optional)

```bash
# Install nginx
sudo yum install -y nginx

# Create config
sudo tee /etc/nginx/conf.d/app.conf << EOF
upstream app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 4.4 Deploy Frontend

```bash
# Build
cd frontend
npm run build

# Option A: Serve from EC2
npm run start -p 3000

# Option B: Deploy to S3 + CloudFront
# Build: npm run build
# Upload to S3: aws s3 sync .next/static s3://your-bucket/
# Create CloudFront distribution pointing to S3
```

---

## 5. SSL/HTTPS Setup

### Option A: Application Load Balancer (ALB)

```bash
# Create ALB in AWS Console
# Add target: EC2 instance on port 8000
# Add HTTPS listener with ACM certificate
# Update security group to allow 443
```

### Option B: Self-Signed (Development)

```bash
# Generate certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Configure nginx
sudo tee /etc/nginx/conf.d/app.conf << EOF
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}

server {
    listen 80;
    return 301 https://$host$request_uri;
}
EOF
```

---

## 6. Monitoring & Logs

### CloudWatch Logs

```bash
# View logs
aws logs tail /aws/ecs/tech-news-api --follow --region us-west-2

# Create log group
aws logs create-log-group --log-group-name /tech-news/api --region us-west-2
```

### Health Checks

```bash
# API health
curl http://your-instance:8000/health

# DynamoDB
aws dynamodb list-tables --region us-west-2

# Redis
redis-cli -h your-elasticache-endpoint ping
```

---

## 7. Troubleshooting

### Issue: DynamoDB Connection Refused
**Error:** `botocore.exceptions.NoCredentialsError`

**Solution:**
1. Verify IAM role attached to EC2 instance
2. Check role has DynamoDB permissions
3. Verify `DYNAMODB_ENDPOINT_URL` is NOT set

```bash
# Check instance role
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

### Issue: Redis Connection Refused
**Solution:**
- Local: `docker-compose up redis`
- Production: Verify ElastiCache endpoint in `.env`

### Issue: Bedrock Access Denied
**Error:** `User is not authorized to perform: bedrock:InvokeModel`

**Solution:**
1. Verify IAM role has `bedrock:InvokeModel` action
2. Verify correct Bedrock region (us-west-2)
3. Verify model ARN matches policy

---

## 8. Cost Estimation

| Service | Cost | Notes |
|---------|------|-------|
| DynamoDB | <$1/month | Pay-per-request, free tier eligible |
| ElastiCache | $0 | Free tier (t3.micro) or $0.017/hour |
| EC2 t3.small | $17/month | ~$0.023/hour |
| **Total** | **~$17/month** | Minimal setup |

---

## 9. Security Best Practices

- [ ] No AWS credentials in code or env vars
- [ ] Use IAM roles for all AWS access
- [ ] Enable DynamoDB encryption at rest
- [ ] Use HTTPS/TLS everywhere
- [ ] Restrict security group ingress
- [ ] Enable CloudWatch alarms
- [ ] Enable DynamoDB point-in-time recovery
- [ ] Rotate JWT secret regularly
- [ ] Use strong database passwords

---

## 10. Next Steps

1. Create DynamoDB tables in us-west-2
2. Create IAM role with permissions
3. Launch EC2 instance with IAM role
4. Clone and deploy application
5. Set up domain and HTTPS
6. Configure monitoring and logging
7. Run load testing before production
8. Set up automated backups

---

**Maintained by:** DevOps Team  
**Last Updated:** May 18, 2026
