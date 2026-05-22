# Terraform AWS Deployment

This stack deploys Tech News Mystery to AWS `us-west-2` with:

- ECS Fargate services for FastAPI, Next.js, Celery worker, and Celery beat
- Application Load Balancer with `/v1/*` and `/health` routed to FastAPI
- ECR repositories for backend and frontend images
- ElastiCache Redis for cache/Celery broker
- DynamoDB tables matching `backend/scripts/create_tables_boto3.py`
  and `backend/app/models/pending_search.py`
- S3 article image bucket
- IAM roles with scoped DynamoDB, S3, Bedrock, ECR, logs, and Secrets Manager access

## Existing Resources

Terraform creates resources only when they are declared in state. If a DynamoDB
table or S3 bucket already exists in AWS but is not in Terraform state, a normal
`terraform apply` will try to create it and AWS will reject the duplicate.

Use one of these approaches:

1. Import existing resources into state with `scripts/import-existing.ps1`.
2. Set `create_dynamodb_tables = false` or `create_s3_bucket = false` in your
   tfvars and provide existing names.

That is the honest Terraform version of "if exists, skip; if not, create."

## First Run

For a quick local syntax check that does not need an S3 backend yet:

```powershell
cd infra/terraform
.\scripts\validate-local.ps1
```

Do not run plain `terraform init` for the production stack. The stack uses an S3
backend, so Terraform needs the backend bucket and lock table.

```powershell
cd infra/terraform
Copy-Item terraform.tfvars.example terraform.tfvars
.\scripts\bootstrap-state.ps1 -Bucket <globally-unique-tf-state-bucket> -LockTable tech-news-mystery-terraform-locks
.\scripts\init-remote.ps1 -Bucket <globally-unique-tf-state-bucket> -LockTable tech-news-mystery-terraform-locks
terraform plan
terraform apply
```

Before ECS tasks can run, put required secret values in the app secret:

```powershell
aws secretsmanager put-secret-value `
  --region us-west-2 `
  --secret-id <app_secret_arn_from_output> `
  --secret-string '{ "SECRET_KEY": "...", "JWT_SECRET_KEY": "...", "OPENAI_API_KEY": "", "TAVILY_API_KEY": "", "NEWSAPI_KEY": "", "QDRANT_URL": "", "QDRANT_API_KEY": "", "GEMINI_API_KEY": "", "ANTHROPIC_API_KEY": "" }'
```

## Import Existing DynamoDB/S3

```powershell
cd infra/terraform
.\scripts\init-remote.ps1 -Bucket <globally-unique-tf-state-bucket> -LockTable tech-news-mystery-terraform-locks
.\scripts\import-existing.ps1 -Region us-west-2 -TablePrefix tech-news- -S3Bucket tech-news-articles-381492273521
terraform plan
```

The import helper checks each expected table and bucket. If it exists, it imports
it. If it does not exist, it leaves Terraform to create it.

## CI/CD

The repository includes:

- `.github/workflows/terraform.yml`: validates and plans Terraform on PRs, applies on `main`
- `.github/workflows/deploy.yml`: builds and pushes Docker images to ECR, then updates ECS services

Required GitHub secrets/variables:

- `AWS_ROLE_TO_ASSUME`: IAM role ARN trusted by GitHub OIDC
- `AWS_REGION`: `us-west-2`
- `TF_STATE_BUCKET`: S3 bucket for Terraform state
- `TF_STATE_LOCK_TABLE`: DynamoDB table for Terraform state locking
- `TF_STATE_KEY`: optional, defaults to `tech-news-mystery/prod/terraform.tfstate`

Create the backend state bucket/lock table once with `scripts/bootstrap-state.ps1`
or `scripts/bootstrap-state.sh`. Keep application resources in this stack.
