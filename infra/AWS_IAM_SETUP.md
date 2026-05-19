# AWS Infrastructure Setup - IAM Role Configuration

## Overview
This document outlines the IAM role and permissions required to run the Tech News Mystery application on AWS infrastructure (us-west-2 region).

## Important Security Notes
- **No hardcoded credentials in application code**
- AWS credentials are managed via IAM role attached to EC2 instance
- The application uses boto3 which automatically detects and uses IAM role credentials
- API keys (OpenAI, Tavily) are passed via environment variables from AWS Secrets Manager

## IAM Role: `TechNewsMysteryAppRole`

### Trust Relationship (Assume Role Policy)
```json
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

This policy allows EC2 instances to assume the role.

## IAM Policy: `TechNewsMysteryAppPolicy`

### DynamoDB Permissions
The application reads/writes to 9 DynamoDB tables (all use on-demand billing mode):
- articles
- users
- comments
- user_saves
- user_likes
- user_preferences
- news_sources
- trending_articles
- submissions

### Complete Policy Document
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBTableAccess",
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
      "Resource": [
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/articles",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/articles/index/slug-index",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/articles/index/source-date-index",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/users",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/users/index/username-index",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/comments",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/comments/index/article-date-index",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/user_saves",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/user_likes",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/user_preferences",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/news_sources",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/trending_articles",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/submissions",
        "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/submissions/index/user-date-index"
      ]
    },
    {
      "Sid": "BedrockInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
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
      "Resource": "arn:aws:logs:us-west-2:ACCOUNT_ID:log-group:/aws/ec2/tech-news-mystery:*"
    },
    {
      "Sid": "SecretsManagerRead",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:tech-news-mystery/openai-api-key-*",
        "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:tech-news-mystery/tavily-api-key-*"
      ]
    }
  ]
}
```

## Step-by-Step IAM Role Creation

### 1. Create the IAM Role

```bash
aws iam create-role \
  --role-name TechNewsMysteryAppRole \
  --assume-role-policy-document file://trust-policy.json
```

Where `trust-policy.json` contains:
```json
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

### 2. Create the IAM Policy

```bash
aws iam create-policy \
  --policy-name TechNewsMysteryAppPolicy \
  --policy-document file://app-policy.json
```

Save the policy JSON from above to `app-policy.json` (replacing ACCOUNT_ID with your AWS account ID).

### 3. Attach the Policy to the Role

```bash
aws iam attach-role-policy \
  --role-name TechNewsMysteryAppRole \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/TechNewsMysteryAppPolicy
```

### 4. Create an Instance Profile

```bash
aws iam create-instance-profile \
  --instance-profile-name TechNewsMysteryAppProfile

aws iam add-role-to-instance-profile \
  --instance-profile-name TechNewsMysteryAppProfile \
  --role-name TechNewsMysteryAppRole
```

### 5. Attach the Instance Profile to EC2 Instance

When launching an EC2 instance:
```bash
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --iam-instance-profile Name=TechNewsMysteryAppProfile \
  --region us-west-2
```

Or attach to an existing instance:
```bash
aws ec2 associate-iam-instance-profile \
  --iam-instance-profile Name=TechNewsMysteryAppProfile \
  --instance-id i-1234567890abcdef0
```

## Environment Variables Required

### On EC2 Instance
```bash
# AWS Configuration (credentials via IAM role, no hardcoding)
export AWS_REGION=us-west-2

# Application
export ENVIRONMENT=production
export DEBUG=false
export SECRET_KEY=<your-secret-key>
export API_V1_PREFIX=/v1

# Redis/ElastiCache
export REDIS_URL=redis://your-elasticache-endpoint:6379/0
export CELERY_BROKER_URL=redis://your-elasticache-endpoint:6379/1
export CELERY_RESULT_BACKEND=redis://your-elasticache-endpoint:6379/2

# LLM Providers
export LLM_PROVIDER=bedrock,openai
export OPENAI_API_KEY=<from-secrets-manager>
export TAVILY_API_KEY=<from-secrets-manager>
export BEDROCK_REGION=us-west-2
export BEDROCK_MODEL=anthropic.claude-3-5-haiku-20241022

# JWT
export JWT_SECRET_KEY=<your-jwt-secret>
export JWT_ALGORITHM=HS256
export ACCESS_TOKEN_EXPIRE_MINUTES=1440
export REFRESH_TOKEN_EXPIRE_DAYS=30
```

## DynamoDB Tables Created

All tables use **PAY_PER_REQUEST** billing (on-demand):

| Table Name | Primary Key | Attributes | Indexes |
|---|---|---|---|
| articles | article_id (S) | title, content, summary, slug, source_id, published_at, like_count, view_count | slug-index, source-date-index |
| users | user_id (S) | email, username, password_hash, role, created_at, updated_at | username-index |
| comments | comment_id (S) | user_id, article_id, content, created_at, updated_at | article-date-index |
| user_saves | user_id (S) + article_id (S) | saved_at, updated_at | - |
| user_likes | user_id (S) + article_id (S) | liked_at | - |
| user_preferences | user_id (S) | preferred_categories, theme, notifications_enabled, updated_at | - |
| news_sources | source_id (S) | name, url, category, description, created_at | - |
| trending_articles | trending_id (S) | article_id, score, computed_at | - |
| submissions | submission_id (S) | user_id, submitted_at | user-date-index |

## Verification Steps

### 1. Verify IAM Role
```bash
aws iam get-role --role-name TechNewsMysteryAppRole
aws iam list-attached-role-policies --role-name TechNewsMysteryAppRole
```

### 2. Test EC2 Instance Credentials
```bash
# SSH into EC2 instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Verify role credentials are available
aws sts get-caller-identity

# Output should show the role ARN:
# arn:aws:iam::ACCOUNT_ID:role/TechNewsMysteryAppRole
```

### 3. Test DynamoDB Access
```bash
# From EC2 instance, test table access
aws dynamodb list-tables --region us-west-2
```

### 4. Test Bedrock Access
```bash
# Test Bedrock model invocation
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-5-haiku-20241022 \
  --region us-west-2 \
  --body '{"messages":[{"role":"user","content":"Hello"}]}'
```

## Troubleshooting

### Issue: "No credentials found"
**Solution**: Ensure the EC2 instance has the IAM instance profile attached.
```bash
aws ec2 describe-instances --instance-ids i-xxxxx --region us-west-2
# Check IAM InstanceProfiles section
```

### Issue: "User is not authorized to perform: dynamodb:GetItem"
**Solution**: Verify the policy is attached and includes all required table ARNs.
```bash
aws iam get-role-policy \
  --role-name TechNewsMysteryAppRole \
  --policy-name TechNewsMysteryAppPolicy
```

### Issue: "AccessDenied on bedrock:InvokeModel"
**Solution**: Ensure Bedrock is available in us-west-2 and the model ARN is correct.

## Local Development (Docker)

For local development without AWS credentials:
- Use the provided `docker-compose.yml`
- Redis and local services are provided
- No DynamoDB access needed during local testing
- Use mock AWS services for unit tests

## Production Deployment Checklist

- [ ] IAM role created: `TechNewsMysteryAppRole`
- [ ] IAM policy created and attached: `TechNewsMysteryAppPolicy`
- [ ] Instance profile created: `TechNewsMysteryAppProfile`
- [ ] EC2 instance launched with instance profile
- [ ] DynamoDB tables created in us-west-2
- [ ] ElastiCache Redis cluster deployed in us-west-2
- [ ] Bedrock model `anthropic.claude-3-5-haiku-20241022` available in us-west-2
- [ ] Secrets Manager secrets created for API keys
- [ ] CloudWatch Log Group created: `/aws/ec2/tech-news-mystery`
- [ ] Environment variables configured on EC2 instance
- [ ] Security Groups allow appropriate traffic
- [ ] VPC configuration verified
- [ ] Backup and disaster recovery plan in place

## Security Best Practices

1. **Principle of Least Privilege**: The policy above grants only necessary permissions
2. **Resource-Based Access**: All DynamoDB resources are specified explicitly
3. **Managed via IAM Role**: No credentials in environment or code
4. **Secrets Manager**: Use for sensitive API keys, not environment variables
5. **CloudWatch Monitoring**: Enable CloudTrail for audit logging
6. **Regular Audits**: Review IAM permissions quarterly
7. **MFA for Admin Access**: Use MFA for AWS console access
8. **Key Rotation**: Rotate API keys periodically

## Related Documentation

- AWS DynamoDB: https://docs.aws.amazon.com/dynamodb/
- AWS Bedrock: https://docs.aws.amazon.com/bedrock/
- boto3 Documentation: https://boto3.amazonaws.com/
- IAM Best Practices: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
