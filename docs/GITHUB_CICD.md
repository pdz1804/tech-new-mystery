# GitHub CI/CD

## Active Workflows

- App CI/CD: `.github/workflows/deploy.yml`
- Terraform CI/CD: `.github/workflows/terraform.yml`

## App CI/CD Behavior

Trigger paths: `backend/**`, `frontend/**`, `agent_core/**`, `infra/docker/**`

On PRs and pushes (matching paths), the workflow runs three parallel check jobs:
- `backend-checks` — `python -m compileall app`
- `frontend-checks` — type-check, tests, build
- `agent-core-checks` — `python -m compileall agent_core` + unit tests

On push to `main`, after all checks pass it additionally:
- builds and pushes Docker images to ECR:
  - backend
  - frontend
  - agent-core
- forces ECS deployment of:
  - `api`
  - `frontend`
  - `worker`
  - `beat`
  - `agent-core`

## Terraform Workflow Behavior

On PRs/pushes for `infra/terraform/**`, the workflow runs:
- `terraform fmt -check -recursive`
- `terraform init`
- `terraform validate`
- `terraform plan`
- `terraform apply` on `main` push

## Required Secrets

- `AWS_ROLE_TO_ASSUME`
- `TF_STATE_BUCKET`
- `TF_STATE_LOCK_TABLE`

## Useful Variables

- `AWS_REGION` (default `us-west-2`)
- `ECS_CLUSTER`
- `BACKEND_ECR_REPOSITORY`
- `FRONTEND_ECR_REPOSITORY`
- `AGENT_CORE_ECR_REPOSITORY`
- `NEXT_PUBLIC_API_URL`

