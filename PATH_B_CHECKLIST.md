# Path B Implementation Checklist

Estimated time: 35 minutes | Savings: $2,046/year

---

## Prerequisites
- [ ] Verify AWS credentials: `aws sts get-caller-identity`
- [ ] Docker installed and running
- [ ] Terminal open in project directory

---

## Step 1: Destroy Cloud Compute (10 min)
```bash
cd infra/terraform
terraform plan -var-file="local-dev.tfvars"   # preview
terraform apply -var-file="local-dev.tfvars"  # type "yes"
# Wait 3-5 minutes
```
- [ ] Terraform apply completed
- [ ] Verify storage preserved: `aws dynamodb list-tables --region us-west-2`
- [ ] Verify S3: `aws s3 ls s3://tech-news-articles-381492273521/`

---

## Step 2: Set Up Local Environment (5 min)
```bash
cp .env.example .env
# Edit .env: fill in AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
```
- [ ] .env file created and filled in
- [ ] .env is in .gitignore (verify: `grep .env .gitignore`)

---

## Step 3: Start Local Services (10 min)
```bash
docker-compose -f docker-compose.local.yml up
# Wait 2-3 min for services to start
```
- [ ] See "Uvicorn running on http://0.0.0.0:8000" (backend ready)
- [ ] See "ready - started server on 0.0.0.0:3000" (frontend ready)
- [ ] Keep this terminal open

---

## Step 4: Verify Everything Works (10 min)

Open NEW terminal, test:

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok",...}

open http://localhost:3000
# Expected: App loads

docker exec tech-news-api aws dynamodb list-tables --region us-west-2
# Expected: See all tech-news-* tables
```

- [ ] Backend responds to health check
- [ ] Frontend loads at http://localhost:3000
- [ ] DynamoDB tables accessible
- [ ] S3/Redis accessible

---

## Step 5: Commit to Git (5 min)
```bash
git add infra/terraform/local-dev.tfvars docker-compose.local.yml .env.example
git commit -m "feat: implement Path B - local dev with AWS storage"
git push origin main
```
- [ ] Files committed
- [ ] Pushed to GitHub

---

## Done! 🎉

✅ Cloud compute removed (ECS/ALB gone)
✅ Storage preserved (DynamoDB, S3, Redis in AWS)
✅ Local services running
✅ Data persists to AWS
✅ Cost reduced: $235 → $65/month ($2,046/year saved)

---

## Daily Workflow

**Morning:** `docker-compose -f docker-compose.local.yml up`  
**Work:** Develop locally at http://localhost:3000  
**Evening:** `Ctrl+C` to stop services  
**Data:** Always synced to AWS

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| AWS credentials error | Run `aws configure` |
| Port 8000 in use | `taskkill /PID <PID> /F` |
| Docker not running | Start Docker Desktop |
| DynamoDB fails | Check .env has AWS credentials |

See `README_PATH_B.md` for more details.

