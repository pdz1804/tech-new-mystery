# CI/CD Configuration Reference

Complete guide to deploying Tech News Mystery infrastructure, services, and runtime configuration.

## Architecture Overview

```
GitHub (main branch)
    ↓
CI/CD Pipeline (.github/workflows/deploy.yml)
    ├─ Backend checks (Python compile, tests)
    ├─ Frontend checks (TypeScript, tests, build)
    ├─ Agent Core checks (Python compile, pytest)
    └─ Deploy (on main branch only)
         ├─ Build & push Backend image → ECR
         ├─ Build & push Frontend image → ECR
         ├─ Build Agent Core (CodeBuild) → ECR
         └─ Rollout: api, frontend, worker, beat services
```

## GitHub Actions Workflow

**File**: `.github/workflows/deploy.yml`

### Triggers
- **Push to main**: Deploy on success
- **Pull requests**: Run checks only (no deploy)
- **Manual dispatch**: Trigger anytime

### Required Secrets in GitHub

```
AWS_ROLE_TO_ASSUME          # ARN of IAM role for OIDC assume-role
```

### Required Variables in GitHub

All have defaults but can be overridden:

```
AWS_REGION                          = us-west-2
ECS_CLUSTER                         = tech-news-mystery-prod
BACKEND_ECR_REPOSITORY              = tech-news-mystery-prod-backend
FRONTEND_ECR_REPOSITORY             = tech-news-mystery-prod-frontend
AGENT_CORE_ECR_REPOSITORY           = tech-news-mystery-prod-agent-core
AGENT_CORE_CODEBUILD_PROJECT        = tech-news-mystery-prod-agent-core-arm64-image
AGENT_CORE_CODEBUILD_SOURCE_BUCKET  = tech-news-mystery-prod-codebuild-sources-{ACCOUNT_ID}
NEXT_PUBLIC_API_URL                 = /v1
```

## Backend Configuration

### Docker Build
**File**: `infra/docker/backend.Dockerfile`

### Environment Variables (ECS Task Definition)

Required in **api, worker, beat** services:

```env
# App
DEBUG=false
SECRET_KEY=<generate-secure-random>
API_V1_PREFIX=/v1

# AWS / DynamoDB
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=<from-iam-user>
AWS_SECRET_ACCESS_KEY=<from-iam-user>
DYNAMODB_ENDPOINT_URL=<auto-managed-by-vpc>

# Redis
REDIS_URL=redis://redis.internal:6379/0

# Celery
CELERY_BROKER_URL=redis://redis.internal:6379/1
CELERY_RESULT_BACKEND=redis://redis.internal:6379/2

# LLM
ANTHROPIC_API_KEY=<from-secrets-manager>
ANTHROPIC_MODEL=claude-haiku-4-5

# Vector DB
OPENAI_API_KEY=<from-secrets-manager>

# Search
TAVILY_API_KEY=<from-secrets-manager>

# JWT
JWT_SECRET_KEY=<generate-secure-random>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Agent Core
AGENT_CORE_BASE_URL=http://agent-core.internal:8080
AGENT_CORE_TIMEOUT=300
```

### ECS Task Definition

The api service runs on port 8000:

```json
{
  "containerDefinitions": [
    {
      "name": "api",
      "image": "<ECR_REGISTRY>/tech-news-mystery-prod-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        // ... see above env vars
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/tech-news-mystery-prod/api",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "family": "tech-news-mystery-prod-backend-api",
  "networkMode": "awsvpc"
}
```

## Frontend Configuration

### Docker Build
**File**: `frontend/Dockerfile`

Build argument:
```
NEXT_PUBLIC_API_URL=/v1
```

### Environment Variables

**Runtime** (set at build time):
```
NEXT_PUBLIC_API_URL=/v1
```

**No secrets** — frontend runs in browser, all communication is via API with CORS.

### ECS Task Definition

Frontend service runs on port 3000:

```json
{
  "containerDefinitions": [
    {
      "name": "frontend",
      "image": "<ECR_REGISTRY>/tech-news-mystery-prod-frontend:latest",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NEXT_PUBLIC_API_URL",
          "value": "/v1"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/tech-news-mystery-prod/frontend",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "family": "tech-news-mystery-prod-backend-frontend",
  "networkMode": "awsvpc"
}
```

## Agent Core Configuration

### Docker Build
**File**: `infra/docker/agent-core.Dockerfile`

Built via AWS CodeBuild with ARM64 architecture (cost optimization).

### Environment Variables (ECS Task Definition)

Required in **agent-core** service:

```env
# Runtime
ENVIRONMENT=production
DEBUG=false

# Agent Core Runtime
AGENT_CORE_API_KEY=<optional-if-using-auth>
REQUIRE_TRUE_STREAMING=true

# AWS / Bedrock
AWS_REGION=us-west-2
BEDROCK_REGION=us-west-2
AGENT_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0

# AWS AgentCore Resources (set by Terraform)
MEMORY_ID=<from-bedrock-agentcore-memory>
BROWSER_ID=<from-bedrock-agentcore-browser>
CODE_INTERPRETER_ID=<from-bedrock-agentcore-code-interpreter>

# Secrets Manager ARN (for loading secrets at runtime)
APP_SECRET_ARN=arn:aws:secretsmanager:us-west-2:{ACCOUNT_ID}:secret:tech-news-mystery-prod-agentcore

# Embeddings
OPENAI_API_KEY=<loaded-from-secrets-manager>
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Vector DB
QDRANT_MODE=cloud
QDRANT_URL=<loaded-from-secrets-manager>
QDRANT_API_KEY=<loaded-from-secrets-manager>
QDRANT_COLLECTION_NAME=articles

# Tool Config
TOOL_TIMEOUT=30
BROWSER_TIMEOUT=60
CODE_INTERPRETER_TIMEOUT=60
MAX_SEARCH_RESULTS=8
```

### ECS Task Definition

Agent Core service runs on port 8080:

```json
{
  "containerDefinitions": [
    {
      "name": "agent-core",
      "image": "<ECR_REGISTRY>/tech-news-mystery-prod-agent-core:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        // ... see above env vars
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/tech-news-mystery-prod/agent-core",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "requiresCompatibilities": ["FARGATE"],
      "cpu": "1024",
      "memory": "2048"
    }
  ],
  "family": "tech-news-mystery-prod-agent-core",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048"
}
```

## Supporting Services

### Redis
- **Purpose**: Celery broker, cache, session store
- **URL**: `redis://redis.internal:6379`
- **Configuration**: In VPC, security group allows port 6379 from api/worker/beat

### DynamoDB
- **Purpose**: Chat sessions, articles, user data
- **Tables**:
  - `tech-news-mystery-prod-chat-sessions`
  - `tech-news-mystery-prod-articles`
  - `tech-news-mystery-prod-users`
- **Configuration**: AWS managed, access via IAM role

### Qdrant Vector DB
- **Purpose**: Vector embeddings for semantic search
- **URL**: Cloud-hosted or self-hosted via environment variable
- **Configuration**: API key from Secrets Manager

## Secrets Manager

**ARN**: `arn:aws:secretsmanager:us-west-2:{ACCOUNT_ID}:secret:tech-news-mystery-prod-agentcore`

**Stored JSON**:
```json
{
  "OPENAI_API_KEY": "sk-...",
  "QDRANT_URL": "https://...",
  "QDRANT_API_KEY": "..."
}
```

Loaded at runtime by:
- `agent_core/config.py`: Loads via `app_secret_arn` in task definition
- `backend/app/config.py`: Can also load via Secrets Manager for multi-secret scenarios

## Network Configuration

### VPC Setup
- **Subnets**: Private subnets for ECS services
- **Security Groups**:
  - `api-sg`: Port 8000 from ALB, internal only
  - `frontend-sg`: Port 3000 from ALB, internal only
  - `agent-core-sg`: Port 8080 from api/worker, internal only
  - `redis-sg`: Port 6379 from api/worker/beat
  - `alb-sg`: Port 80/443 from internet

### Service Discovery
- `api.internal` → api ECS service
- `frontend.internal` → frontend ECS service
- `agent-core.internal` → agent-core ECS service
- `redis.internal` → Redis service

## Deployment Flow

1. **Push to main** → GitHub Actions triggered
2. **Run checks**: Python compile, TypeScript, tests
3. **Build images**:
   - Backend: `docker build` → `docker push` ECR
   - Frontend: `docker build --build-arg NEXT_PUBLIC_API_URL=/v1` → push ECR
   - Agent Core: `git archive` → S3 → CodeBuild (ARM64) → ECR
4. **ECS rollout**:
   - `force-new-deployment` on api, frontend, worker, beat
   - `wait services-stable` (max 10 minutes)
5. **Monitoring**:
   - CloudWatch Logs in `/ecs/tech-news-mystery-prod/{service}`
   - ECS console for task status

## Troubleshooting

### Service won't start
1. Check CloudWatch Logs: `/ecs/tech-news-mystery-prod/{service}`
2. Check ECS task for error messages
3. Verify environment variables in task definition

### Agent Core connection fails
1. Verify `AGENT_CORE_BASE_URL` in api task definition
2. Check agent-core service is running: `aws ecs describe-services`
3. Check security group allows port 8080 from api

### Frontend can't connect to API
1. Verify `NEXT_PUBLIC_API_URL` environment variable (default `/v1`)
2. Check API ALB health: `aws elbv2 describe-target-health`
3. Check CORS configuration in `backend/app/config.py`

## CI/CD Variables Checklist

- [ ] AWS_ROLE_TO_ASSUME set in GitHub Secrets
- [ ] All ECR repositories created
- [ ] CodeBuild project created for Agent Core ARM64
- [ ] ECS cluster and services created
- [ ] CloudWatch Log Groups created
- [ ] Redis service running in VPC
- [ ] DynamoDB tables created
- [ ] Qdrant service accessible (cloud or self-hosted)
- [ ] Secrets Manager secret created with OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY
- [ ] IAM role for ECS task execution has permissions for SecretsManager

## Testing Deployment

```bash
# 1. Trigger workflow
git push origin main

# 2. Monitor deployment
aws ecs describe-services --cluster tech-news-mystery-prod \
  --services api frontend worker beat

# 3. Check logs
aws logs tail /ecs/tech-news-mystery-prod/api --follow
aws logs tail /ecs/tech-news-mystery-prod/agent-core --follow

# 4. Test API
curl -X POST https://<api-domain>/v1/chat/send \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "message": "Hello"}'

# 5. Test Frontend
open https://<frontend-domain>
```
