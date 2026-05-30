# Terraform CI/CD Issues & Fixes

## Current Failures

### 1. Missing IAM Permissions for GitHub Actions

**Error**:
```
Error: reading Application AutoScaling Target (service/tech-news-mystery-prod/clustering): 
operation error Application Auto Scaling: DescribeScalableTargets
User: arn:aws:sts::381492273521:assumed-role/github-actions-tech-news-mystery/GitHubActions 
is not authorized to perform: application-autoscaling:DescribeScalableTargets
```

**Root Cause**: The GitHub Actions OIDC role lacks `application-autoscaling:*` permissions needed for ECS autoscaling.

**Fix**: Update the GitHub Actions IAM policy in `infra/terraform/iam.tf`:

```hcl
# In the github_actions_role policy, add:
{
  "Effect": "Allow",
  "Action": [
    "application-autoscaling:DescribeScalableTargets",
    "application-autoscaling:DescribeScalingActivities",
    "application-autoscaling:DescribeScalingPolicies",
    "application-autoscaling:PutScalingPolicy",
    "application-autoscaling:DeleteScalingPolicy",
    "application-autoscaling:RegisterScalableTarget",
    "application-autoscaling:DeregisterScalableTarget"
  ],
  "Resource": "*"
}
```

**Current Policy Location**: `infra/terraform/iam.tf` (github_actions role)

### 2. DynamoDB Deprecated `hash_key` Argument

**Warning**: Multiple DynamoDB tables using deprecated `hash_key` instead of `key_schema`

Example:
```
resource "aws_dynamodb_table" "users" {
  hash_key = "user_id"  # ❌ DEPRECATED
}
```

**Fix**: Update all DynamoDB tables in `infra/terraform/dynamodb.tf`:

```hcl
# Change from:
resource "aws_dynamodb_table" "users" {
  hash_key = "user_id"
  # ...
}

# To:
resource "aws_dynamodb_table" "users" {
  key_schema = [
    {
      attribute_name = "user_id"
      key_type       = "HASH"
    }
  ]
  # ...
}
```

**Affected Tables** (27 total):
- users
- articles
- submissions
- comments
- conversation_sessions
- conversation_messages
- user_preferences
- user_likes
- trending_articles
- pending_searches
- cluster_metadata
- clustering_evaluation
- clustering_params
- article_embeddings

**Deprecation Timeline**: Terraform will remove support in v2.0 (estimated 2027)

## CI/CD Terraform Workflow

**File**: `.github/workflows/terraform.yml` (needs creation)

Suggested workflow:

```yaml
name: Terraform

on:
  push:
    paths:
      - "infra/terraform/**"
      - ".github/workflows/terraform.yml"
  pull_request:
    paths:
      - "infra/terraform/**"

env:
  AWS_REGION: us-west-2
  TF_VERSION: 1.6.0

jobs:
  terraform-plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}
      
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Terraform Init
        working-directory: infra/terraform
        run: terraform init
      
      - name: Terraform Format Check
        working-directory: infra/terraform
        run: terraform fmt -check
      
      - name: Terraform Validate
        working-directory: infra/terraform
        run: terraform validate
      
      - name: Terraform Plan
        working-directory: infra/terraform
        run: terraform plan -out=tfplan
      
      - name: Upload Plan
        uses: actions/upload-artifact@v4
        with:
          name: tfplan
          path: infra/terraform/tfplan

  terraform-apply:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: terraform-plan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}
      
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Download Plan
        uses: actions/download-artifact@v4
        with:
          name: tfplan
          path: infra/terraform
      
      - name: Terraform Init
        working-directory: infra/terraform
        run: terraform init
      
      - name: Terraform Apply
        working-directory: infra/terraform
        run: terraform apply -auto-approve tfplan
```

## Required Secrets for Terraform CI/CD

In GitHub Actions Secrets:
```
AWS_ROLE_TO_ASSUME    # IAM role ARN for assume-role (same as app CI/CD)
```

## Terraform State Management

### Current Setup
- **Backend**: S3 + DynamoDB (for locking)
- **Location**: `infra/terraform/main.tf` (backend configuration)
- **State file**: `s3://tech-news-mystery-prod-terraform-state/terraform.tfstate`
- **Lock table**: `tech-news-mystery-prod-terraform-locks`

### Backup Strategy
```bash
# Manual backup
aws s3 cp s3://tech-news-mystery-prod-terraform-state/terraform.tfstate \
  ./terraform.tfstate.backup

# List all versions
aws s3api list-object-versions \
  --bucket tech-news-mystery-prod-terraform-state
```

### State Locking
- DynamoDB table prevents concurrent applies
- Lock acquisition timeout: 30s (configurable)
- If stuck, force unlock with: `terraform force-unlock <LOCK_ID>`

## Deployment Order

1. **Terraform**: Apply infrastructure changes (separate CI/CD)
2. **App**: Deploy services after infrastructure is ready
3. **Post-deploy**: Run smoke tests

Current workflow doesn't enforce this order — both can run in parallel, which may cause race conditions.

## Recommended Fixes (Priority Order)

### P0 (Blocking)
- [ ] Add `application-autoscaling:*` permissions to GitHub Actions IAM role
- [ ] Create `.github/workflows/terraform.yml` for infrastructure CI/CD

### P1 (High)
- [ ] Migrate all DynamoDB tables from `hash_key` to `key_schema`
- [ ] Add Terraform dependency between app and infrastructure deployments

### P2 (Medium)
- [ ] Add Terraform cost estimation in PR comments
- [ ] Add `terraform taint` / `terraform refresh` workflows
- [ ] Enable Terraform Cloud integration for better state management

### P3 (Low)
- [ ] Add Terratest for infrastructure testing
- [ ] Document manual recovery procedures
- [ ] Set up Terraform cost alerts

## Testing Infrastructure Changes

```bash
# Local testing
cd infra/terraform

# Format check
terraform fmt -check

# Validate syntax
terraform validate

# Plan without applying
terraform plan -out=tfplan

# Review changes
terraform show tfplan

# Apply (requires approval)
terraform apply tfplan
```

## Rollback Procedures

### State-based rollback
```bash
# List historical states
aws s3api list-object-versions \
  --bucket tech-news-mystery-prod-terraform-state

# Restore previous state
aws s3api get-object \
  --bucket tech-news-mystery-prod-terraform-state \
  --key terraform.tfstate \
  --version-id <VERSION_ID> \
  terraform.tfstate.previous

# Apply previous state
terraform apply -refresh=false -var-file=terraform.tfvars
```

### Manual resource rollback
```bash
# Mark resource for update
terraform taint aws_ecs_service.api

# Re-apply to update only that resource
terraform apply -auto-approve
```

## Monitoring Terraform Drift

```bash
# Check for drift (manual)
terraform refresh
terraform plan

# Automated drift detection (requires scheduling)
# Add to cron job:
cd infra/terraform && terraform plan -json > drift-report.json
```

## CI/CD Health Checklist

- [ ] GitHub Actions role has all required permissions
- [ ] Terraform workflow triggers on correct paths
- [ ] Terraform state is backed up and locked
- [ ] DynamoDB tables use modern `key_schema`
- [ ] Infrastructure changes are separate from app deployments
- [ ] Drift detection runs regularly
- [ ] Rollback procedures are documented and tested
