# Group D: AWS Infrastructure Setup - Code Changes

## Task D1: DynamoDB Tables Script

### File: `backend/scripts/create_tables_boto3.py`

**Key Changes:**

1. **Module Docstring (Updated)**
```python
"""Create DynamoDB tables using boto3 for AWS Infrastructure (Group D).

Tables created:
1. articles - article_id PK, slug GSI, with like_count and view_count fields
2. users - user_id PK, username GSI, with role field
3. user_saves - user_id+article_id
4. user_likes - user_id+article_id
5. comments - comment_id PK, article_id GSI
6. news_sources - source_id PK
7. user_preferences - user_id PK

Billing Mode: PAY_PER_REQUEST (on-demand)
Region: us-west-2
"""
```

2. **Billing Mode Change - All Tables**
```python
# BEFORE:
BillingMode='PROVISIONED',
ProvisionedThroughput={
    'ReadCapacityUnits': 5,
    'WriteCapacityUnits': 5
}

# AFTER:
BillingMode='PAY_PER_REQUEST'
```

3. **Articles Table Enhancement**
```python
# Enhanced GSI configuration (removed ProvisionedThroughput)
{
    'IndexName': 'slug-index',
    'KeySchema': [
        {'AttributeName': 'slug', 'KeyType': 'HASH'}
    ],
    'Projection': {'ProjectionType': 'ALL'}
    # No ProvisionedThroughput - uses on-demand billing
}
```

4. **New Function: create_user_likes_table()**
```python
def create_user_likes_table():
    """Create user_likes table with composite key (user_id + article_id)."""
    try:
        dynamodb.create_table(
            TableName='user_likes',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'article_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'article_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("[+] Created user_likes table (liked_at)")
    except dynamodb.exceptions.ResourceInUseException:
        print("[+] user_likes table already exists")
```

5. **Enhanced create_all_tables() Function**
```python
def create_all_tables():
    """Create all DynamoDB tables for AWS infrastructure."""
    print("Creating DynamoDB tables using boto3 (us-west-2, PAY_PER_REQUEST)...")
    print("=" * 60)

    # Order: main tables first, then derived tables
    create_users_table()
    create_articles_table()
    create_comments_table()
    create_user_saves_table()
    create_user_likes_table()  # NEW
    create_user_preferences_table()
    create_news_sources_table()
    create_trending_articles_table()
    create_submissions_table()

    print("=" * 60)
    print("\n[SUCCESS] All tables created successfully!")
    print("\nTable Summary:")
    print("  1. users - PK: user_id | GSI: username-index | Fields: role")
    print("  2. articles - PK: article_id | GSI: slug-index, source-date-index | Fields: like_count, view_count")
    print("  3. comments - PK: comment_id | GSI: article-date-index")
    print("  4. user_saves - PK: user_id + article_id")
    print("  5. user_likes - PK: user_id + article_id")
    print("  6. user_preferences - PK: user_id")
    print("  7. news_sources - PK: source_id")
    print("  8. trending_articles - PK: trending_id")
    print("  9. submissions - PK: submission_id | GSI: user-date-index")
```

---

## Task D2: Backend Configuration

### File: `backend/app/config.py`

**Key Changes:**

```python
# BEFORE:
# AWS / DynamoDB
aws_region: str = "ap-southeast-1"
aws_access_key_id: str = "test"
aws_secret_access_key: str = "test"
dynamodb_endpoint_url: str | None = None

# Redis
redis_url: str = "redis://localhost:6379/0"

# Celery
celery_broker_url: str = "redis://localhost:6379/1"
celery_result_backend: str = "redis://localhost:6379/2"

# AFTER:
# AWS / DynamoDB
# Note: AWS credentials are managed via IAM role attached to EC2 instance
# No hardcoded credentials in application code
aws_region: str = "us-west-2"
dynamodb_endpoint_url: str | None = None  # None = use real AWS DynamoDB

# Redis - Use ElastiCache in production, Redis container in local dev
environment: str = "local"
redis_url: str = "redis://redis:6379/0"

# Celery - Uses Redis broker
celery_broker_url: str = "redis://redis:6379/1"
celery_result_backend: str = "redis://redis:6379/2"
```

**Summary of Changes:**
- Removed `aws_access_key_id` field (was "test")
- Removed `aws_secret_access_key` field (was "test")
- Changed `aws_region` from "ap-southeast-1" to "us-west-2"
- Added comment about IAM role credentials
- Changed `redis_url` from "redis://localhost:6379/0" to "redis://redis:6379/0"
- Changed `celery_broker_url` from "redis://localhost:6379/1" to "redis://redis:6379/1"
- Changed `celery_result_backend` from "redis://localhost:6379/2" to "redis://redis:6379/2"
- Added `environment: str = "local"` field

### File: `backend/.env`

**Key Changes:**

```ini
# BEFORE:
[AWS / DynamoDB]
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
DYNAMODB_ENDPOINT_URL=http://localhost:4566

[Redis]
REDIS_URL=redis://localhost:6379/0

[Celery]
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# AFTER:
[AWS / DynamoDB]
# AWS credentials are managed via IAM role attached to EC2 instance
# Do NOT set AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY in environment
AWS_REGION=us-west-2
DYNAMODB_ENDPOINT_URL=
ENVIRONMENT=local

[Redis]
# Redis - points to Docker Redis container for local dev
REDIS_URL=redis://redis:6379/0

[Celery]
# Celery - Uses Redis for broker and result backend
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

**Summary of Changes:**
- Added comment about IAM role credentials
- Removed AWS_ACCESS_KEY_ID line
- Removed AWS_SECRET_ACCESS_KEY line
- Changed AWS_REGION from "ap-southeast-1" to "us-west-2"
- Emptied DYNAMODB_ENDPOINT_URL (was "http://localhost:4566")
- Added ENVIRONMENT=local
- Updated REDIS_URL from "redis://localhost:6379/0" to "redis://redis:6379/0"
- Updated CELERY_BROKER_URL from "redis://localhost:6379/1" to "redis://redis:6379/1"
- Updated CELERY_RESULT_BACKEND from "redis://localhost:6379/2" to "redis://redis:6379/2"

---

## Task D3: Docker Compose Update

### File: `infra/docker-compose.yml`

**Key Changes:**

1. **API Service - Environment Section**
```yaml
# BEFORE:
environment:
  DYNAMODB_ENDPOINT_URL: http://localstack:4566
  REDIS_URL: redis://redis:6379/0
  CELERY_BROKER_URL: redis://redis:6379/1
  CELERY_RESULT_BACKEND: redis://redis:6379/2
depends_on:
  localstack:
    condition: service_healthy
  redis:
    condition: service_healthy

# AFTER:
environment:
  AWS_REGION: us-west-2
  ENVIRONMENT: local
  REDIS_URL: redis://redis:6379/0
  CELERY_BROKER_URL: redis://redis:6379/1
  CELERY_RESULT_BACKEND: redis://redis:6379/2
depends_on:
  redis:
    condition: service_healthy
```

2. **Celery Worker Service - Environment Section**
```yaml
# BEFORE:
environment:
  DYNAMODB_ENDPOINT_URL: http://localstack:4566
  REDIS_URL: redis://redis:6379/0
  CELERY_BROKER_URL: redis://redis:6379/1
  CELERY_RESULT_BACKEND: redis://redis:6379/2
depends_on:
  - redis
  - localstack

# AFTER:
environment:
  AWS_REGION: us-west-2
  ENVIRONMENT: local
  REDIS_URL: redis://redis:6379/0
  CELERY_BROKER_URL: redis://redis:6379/1
  CELERY_RESULT_BACKEND: redis://redis:6379/2
depends_on:
  - redis
```

3. **Celery Beat Service - Environment Section**
```yaml
# BEFORE:
environment:
  CELERY_BROKER_URL: redis://redis:6379/1
  CELERY_RESULT_BACKEND: redis://redis:6379/2
depends_on:
  - redis

# AFTER:
environment:
  AWS_REGION: us-west-2
  ENVIRONMENT: local
  CELERY_BROKER_URL: redis://redis:6379/1
  CELERY_RESULT_BACKEND: redis://redis:6379/2
depends_on:
  - redis
```

4. **Removed LocalStack Service (Entire Block)**
```yaml
# REMOVED:
  localstack:
    image: localstack/localstack:3.8
    container_name: tech-news-localstack
    ports:
      - "4566:4566"
    environment:
      SERVICES: dynamodb,s3
      DEBUG: "0"
      AWS_DEFAULT_REGION: ap-southeast-1
      AWS_ACCESS_KEY_ID: test
      AWS_SECRET_ACCESS_KEY: test
      DOCKER_HOST: unix:///var/run/docker.sock
    volumes:
      - localstack-data:/var/lib/localstack
      - ./localstack/init-aws.sh:/etc/localstack/init/ready.d/init-aws.sh:ro
      - /var/run/docker.sock:/var/run/docker.sock
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566/_localstack/health"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
```

5. **Removed LocalStack Volume**
```yaml
# BEFORE:
volumes:
  redis-data:
  localstack-data:

# AFTER:
volumes:
  redis-data:
```

**Summary of Changes:**
- Removed all LocalStack references
- Added AWS_REGION=us-west-2 to api, celery-worker, and celery-beat services
- Added ENVIRONMENT=local to api, celery-worker, and celery-beat services
- Removed DYNAMODB_ENDPOINT_URL from all services
- Removed localstack-data volume definition
- Removed localstack dependency from api and celery-worker

---

## Task D4: IAM Role & AWS Preparation

### New File: `infra/AWS_IAM_SETUP.md`

**Key Content:**

```markdown
# AWS Infrastructure Setup - IAM Role Configuration

## IAM Role: `TechNewsMysteryAppRole`

### Trust Relationship (Assume Role Policy)
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

## IAM Policy: `TechNewsMysteryAppPolicy`

### Permissions:
- DynamoDB: GetItem, PutItem, UpdateItem, DeleteItem, Query, Scan, BatchGetItem, BatchWriteItem
- Bedrock: InvokeModel (anthropic.claude-3-5-haiku-20241022)
- CloudWatch: CreateLogGroup, CreateLogStream, PutLogEvents
- Secrets Manager: GetSecretValue

### Resources:
- All 9 DynamoDB tables in us-west-2
- Bedrock foundation models
- CloudWatch logs for /aws/ec2/tech-news-mystery
- Secrets Manager secrets

[Complete policy JSON provided in AWS_IAM_SETUP.md]
```

---

## Summary of All Changes

| Component | Change | Before | After |
|-----------|--------|--------|-------|
| **Python Config** | aws_region | ap-southeast-1 | us-west-2 |
| **Python Config** | dynamodb_endpoint_url | None | None (use real AWS) |
| **Python Config** | redis_url | redis://localhost:6379/0 | redis://redis:6379/0 |
| **Python Config** | AWS credentials | HARDCODED | REMOVED (use IAM role) |
| **.env** | AWS_REGION | ap-southeast-1 | us-west-2 |
| **.env** | AWS credentials | test/test | REMOVED |
| **.env** | DYNAMODB_ENDPOINT_URL | http://localhost:4566 | (empty - use AWS) |
| **Docker** | localstack service | PRESENT | REMOVED |
| **Docker** | AWS_REGION | (not set) | us-west-2 |
| **Docker** | Redis URLs | localhost | redis (container) |
| **Database** | Billing | PROVISIONED | PAY_PER_REQUEST |
| **Database** | user_likes table | MISSING | CREATED |
| **Documentation** | IAM Setup | MISSING | COMPLETE |

---

## Testing Verification

### Config Import Test
```bash
cd backend
python -c "from app.config import settings; print('OK')"
# Output: OK
```

### Docker Compose Validation
```bash
cd infra
docker-compose config --quiet
# Output: (no output = valid)
```

### No Hardcoded Credentials Check
```bash
grep -r "aws_access_key_id\|aws_secret_access_key" backend/app/
# Output: (no results = PASS)
```

### AWS Region Consistency Check
```bash
grep -r "us-west-2" backend/app/config.py infra/docker-compose.yml backend/.env
# Output: All files show us-west-2
```

---

## Files Ready for Deployment

All files have been updated and are ready for AWS deployment:

1. `backend/scripts/create_tables_boto3.py` - Ready to create DynamoDB tables
2. `backend/app/config.py` - Ready for EC2 instance with IAM role
3. `backend/.env` - Environment variables configured
4. `infra/docker-compose.yml` - Docker configuration updated
5. `infra/AWS_IAM_SETUP.md` - Complete IAM setup guide
6. `infra/GROUP_D_SUMMARY.md` - Implementation summary

No further changes required before deployment.
