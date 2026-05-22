# GitHub CI/CD

The repository currently has one active GitHub Actions workflow:

| Workflow | File | Purpose |
| --- | --- | --- |
| App CI/CD | `.github/workflows/deploy.yml` | Checks backend/frontend, builds images, pushes to ECR, and rolls ECS services |

The Terraform workflow is intentionally parked as
`.github/workflows/terraform.yml.bak`. It is kept as a reference, but it does
not run automatically. This avoids accidental infrastructure redeploys when
normal app code is committed.

## Required Repository Secrets

| Secret | Purpose |
| --- | --- |
| `AWS_ROLE_TO_ASSUME` | IAM role GitHub Actions assumes through OIDC |

## Optional Repository Variables

Defaults are already set in the workflows, but these variables can override them.

| Variable | Default |
| --- | --- |
| `AWS_REGION` | `us-west-2` |
| `ECS_CLUSTER` | `tech-news-mystery-prod` |
| `BACKEND_ECR_REPOSITORY` | `tech-news-mystery-prod-backend` |
| `FRONTEND_ECR_REPOSITORY` | `tech-news-mystery-prod-frontend` |
| `NEXT_PUBLIC_API_URL` | `/v1` |

## Checks

Pull requests and pushes touching app code run:

| Area | Check |
| --- | --- |
| Backend | `pip install -r requirements.txt` and `python -m compileall app scripts` |
| Frontend | `npm ci`, `npm run type-check`, `npm test`, `npm run build` |

Pull requests stop after checks. Pushes to `main` continue to deployment.

## Deploy Behavior

The deploy workflow pushes two tags for each image:

| Tag | Use |
| --- | --- |
| `${{ github.sha }}` | Immutable traceability for the commit |
| `latest` | Tag consumed by the current ECS task definitions |

After pushing images, the workflow forces a new ECS deployment for:

- `frontend`
- `api`
- `worker`
- `beat`

Then it waits until all four services are stable.

## Infrastructure Changes

Infrastructure is managed manually from `infra/terraform`.

Use this flow only when infrastructure really changed:


```powershell
cd infra/terraform
terraform init
terraform plan
terraform apply
```

When app secrets change:

```powershell
cd infra/terraform
.\scripts\put-app-secret-from-env.ps1 -EnvFile ..\..\backend\.env -Region us-west-2
```

The archived Terraform workflow can be restored by renaming
`.github/workflows/terraform.yml.bak` back to `.github/workflows/terraform.yml`.
