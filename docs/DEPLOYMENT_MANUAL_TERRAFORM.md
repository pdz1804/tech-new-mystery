# Manual Terraform Application Guide

## Current Situation

**CI/CD is blocked** due to Hashicorp's expired GPG signing key affecting all AWS provider versions.

- Status: https://github.com/hashicorp/terraform/issues/35164
- Impact: Cannot download Terraform providers via CI/CD
- Workaround: Apply Terraform manually on local machine
- Temporary: Once Hashicorp rotates key, CI/CD works automatically

## Prerequisites

Before applying locally, ensure you have:

```bash
# 1. Terraform installed (v1.6.0+)
terraform version

# 2. AWS credentials configured
aws sts get-caller-identity
# Should show: Account ID, UserId, and ARN

# 3. AWS role with Terraform permissions
# (GitHub Actions role: github-actions-tech-news-mystery)
# This role should already exist and have the required permissions

# 4. Git repository cloned locally
cd "d:/FPT/Demo/Tech-News-Mystery"
```

## Step-by-Step Application

### 1. Initialize Terraform Backend

```bash
cd infra/terraform

terraform init \
  -backend-config="bucket=tech-news-mystery-tfstate-381492273521" \
  -backend-config="key=terraform.tfstate" \
  -backend-config="region=us-west-2" \
  -backend-config="dynamodb_table=tech-news-mystery-terraform-locks"
```

**Expected output:**
```
Successfully configured the backend "s3"! Terraform will automatically
use this backend unless the backend configuration changes.
```

### 2. Review Plan

```bash
terraform plan -out=tfplan
```

**What will be created:**
- ✅ Bedrock AgentCore Runtime
- ✅ Agent Memory (conversation history)
- ✅ Agent Browser (web navigation tool)
- ✅ Agent Code Interpreter (execute code)
- ✅ ECS AutoScaling policies for clustering service
- ✅ CloudWatch dashboards
- ✅ IAM roles and policies

**Review the plan output** to ensure nothing unexpected will be created.

### 3. Apply Configuration

```bash
terraform apply tfplan
```

**Expected time:** 2-3 minutes

**Monitor output for:**
- ✅ `aws_bedrockagentcore_agent_runtime.agent_core` created
- ✅ `aws_bedrockagentcore_memory.agent_core` created
- ✅ `aws_bedrockagentcore_browser.agent_core` created
- ✅ `aws_bedrockagentcore_code_interpreter.agent_core` created
- ✅ ECS autoscaling targets created

### 4. Verify Creation

```bash
# Show all outputs
terraform output -json

# Or check AWS Console:
# AWS Console → Bedrock → Agent Runtime
# Should see: tech_news_mystery_prod_agent runtime
```

## After Terraform Completes

### 1. Backend will automatically redeploy

The ECS service detects the new `AGENT_CORE_RUNTIME_ARN` and redeploys:
- Backend redeploys with Agent Core connected
- Worker/Beat services update
- CloudWatch logs start flowing

### 2. Test the deployment

```bash
# Check API health
curl -s https://<api-domain>/v1/health

# Test clusters endpoint
curl -s https://<api-domain>/v1/clusters | head -20

# Browser: Navigate to Topics page
# Should load clusters instead of 500 error ✅
```

### 3. Monitor logs

```bash
# Backend logs
aws logs tail /ecs/tech-news-mystery-prod/api --follow

# Agent Core logs
aws logs tail /ecs/tech-news-mystery-prod/agent-core --follow
```

## Troubleshooting

### Issue: "bucket does not exist"

**Solution:** Backend S3 bucket already exists:
```bash
aws s3 ls | grep terraform
# Should show: tech-news-mystery-tfstate-381492273521
```

### Issue: "error checking signature: openpgp: key expired"

**This is expected** - it's the Hashicorp issue we're working around.
- Don't use CI/CD until Hashicorp fixes it
- Apply locally as described above
- When Hashicorp rotates key, remove workaround from `.github/workflows/terraform.yml`

### Issue: "Access Denied" when applying

**Verify AWS credentials:**
```bash
aws sts get-caller-identity
# Should show your account and role

# If using AWS SSO:
aws sso login --profile <profile-name>
```

## Once Hashicorp Fixes Key

When Hashicorp rotates their signing key (they're aware and working on it):

1. Update `.github/workflows/terraform.yml`:
   - Remove `TF_SKIP_PROVIDER_VERIFICATION`
   - Remove `TF_PLUGIN_CACHE_DIR`
   - Simplify terraform init command

2. Remove manual application instructions from this doc

3. CI/CD will automatically handle Terraform from then on

## What Gets Created

This Terraform application creates the **Agent Core runtime** which enables:

- **Semantic Search**: Vectorized article search via Qdrant
- **Web Browsing**: Agent can browse websites and extract content
- **Code Execution**: Agent can write and execute Python/JavaScript
- **Memory**: Persistent conversation history
- **Real Streaming**: Token-by-token response streaming

### Architecture After Application

```
User Request
    ↓
API (ECS)
    ↓
Backend (Bedrock Chat)
    ↓
Agent Core Runtime (Bedrock AgentCore)
    ↓
Tools: Search + Browse + Execute + Memory
    ↓
Response streams back to browser
```

## Next Steps

1. ✅ **Apply Terraform locally** (follow steps above)
2. ✅ **Verify Agent Core runtime created** in AWS Console
3. ✅ **Check Topics page loads** without 500 errors
4. ✅ **Monitor CloudWatch logs** for any issues
5. ⏳ **Wait for Hashicorp key rotation** (ongoing)
6. ⏳ **Remove workaround from CI/CD** when fixed
7. ✅ **CI/CD Terraform automation** will work

## Support

If you hit issues during application:

1. Check terraform output for specific error
2. Verify AWS credentials and permissions
3. Check CloudWatch logs for runtime errors
4. Reference this guide's troubleshooting section

For ongoing issues, check GitHub issue: https://github.com/hashicorp/terraform/issues/35164
