# Path B: Local Development with AWS Storage

**Remove ECS/ALB from AWS. Run app locally in Docker. Keep all data in AWS.**

**Result:** Save $170/month ($2,046/year). Takes 35 minutes.

---

## Quick Start

### 1. Verify AWS Credentials (5 min)
```bash
aws sts get-caller-identity
# Should show your AWS account
```

### 2. Destroy Cloud Compute (10 min)
```bash
cd infra/terraform
terraform plan -var-file="local-dev.tfvars"   # preview
terraform apply -var-file="local-dev.tfvars"  # execute (type "yes")
# Wait 3-5 minutes for completion
```

**What's removed:** ECS services, ALB, compute resources  
**What's preserved:** DynamoDB, S3, Redis (all data safe)

### 3. Set AWS Credentials (5 min)
```bash
cp .env.example .env
# Edit .env with your AWS Access Key ID and Secret Access Key
```

### 4. Start Local Services (10 min)
```bash
docker-compose -f docker-compose.local.yml up
# Wait for: "Uvicorn running on http://0.0.0.0:8000"
# Keep this terminal open
```

### 5. Verify Everything Works (5 min)

In a new terminal:
```bash
# Test backend
curl http://localhost:8000/health
# Expected: {"status":"ok",...}

# Test frontend
open http://localhost:3000
# Expected: App loads successfully
```

### 6. Commit Changes (5 min)
```bash
git add infra/terraform/local-dev.tfvars docker-compose.local.yml .env.example
git commit -m "feat: implement Path B - local dev with AWS storage"
git push
```

---

## Daily Usage

### Morning: Start Services
```bash
docker-compose -f docker-compose.local.yml up
```

### Work: Develop Locally
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Code changes auto-reload
- All data saves to AWS automatically

### Evening: Stop Services
```
Ctrl+C in terminal
```

---

## Cost Impact

```
Before:  $235/month
After:   $65/month
Savings: $170/month ($2,046/year)
```

---

## Architecture

```
Your Laptop (Docker)           AWS (Storage)
├─ Backend API                 ├─ DynamoDB
├─ Frontend                    ├─ S3
├─ Worker                      ├─ Redis
├─ Beat                        ├─ Secrets
└─ Redis                       └─ Bedrock
```

---

## Files You Need

- `docker-compose.local.yml` - Docker setup
- `.env.example` → copy to `.env` - AWS credentials
- `infra/terraform/local-dev.tfvars` - Terraform config
- `PATH_B_CHECKLIST.md` - Step-by-step checklist (if you need it)

---

## Troubleshooting

### "AWS credentials not found"
```bash
aws configure
# Enter your Access Key ID and Secret Access Key
```

### "Port 8000 already in use"
```bash
# Find and kill the process
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### "Docker not running"
- Start Docker Desktop (Windows/Mac)
- Or start Docker daemon (Linux): `systemctl start docker`

### "DynamoDB connection fails"
```bash
# Verify .env has AWS credentials
cat .env | grep AWS_

# Restart services
Ctrl+C
docker-compose -f docker-compose.local.yml up
```

---

## Can You Scale Back to AWS Later?

**Yes, anytime:**
```bash
cd infra/terraform
git checkout -- terraform.tfvars
terraform apply
# Back online in 10-15 minutes
```

Data is never affected (always in AWS).

---

## Sharing with Team

1. Share `docker-compose.local.yml` and `.env.example`
2. Each team member: `cp .env.example .env` and fill in their AWS credentials
3. Each team member: `docker-compose -f docker-compose.local.yml up`
4. Everyone develops against the same AWS backend (same DynamoDB/S3)

---

## Environment Variables

Fill in `.env` with your AWS credentials:

```
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
```

**WARNING:** Never commit `.env` to git (contains secrets)

---

**Ready?** Start with Step 1 above, or follow `PATH_B_CHECKLIST.md` for detailed checkboxes.
