# Deployment Architecture

## Infrastructure

Infrastructure is managed in `infra/terraform`.

Main deployed compute services on ECS:
- `frontend`
- `api`
- `worker`
- `beat`
- `agent-core`

The `agent-core` runtime is deployed separately from backend/frontend and is invoked by backend over internal HTTP.

## CI/CD

### App pipeline
Workflow: `.github/workflows/deploy.yml`

- Runs backend/frontend checks.
- Builds and pushes Docker images:
  - backend image
  - frontend image
  - agent-core image
- Forces ECS rollout for:
  - `api`
  - `frontend`
  - `worker`
  - `beat`
  - `agent-core`

### Terraform pipeline
Workflow: `.github/workflows/terraform.yml`

- `terraform fmt -check`
- `terraform init`
- `terraform validate`
- `terraform plan`
- `terraform apply` on `main` push

## Required CI/CD Variables/Secrets

- `AWS_ROLE_TO_ASSUME` (secret)
- `TF_STATE_BUCKET` (secret)
- `TF_STATE_LOCK_TABLE` (secret)
- `AWS_REGION` (variable, default `us-west-2`)
- `ECS_CLUSTER` (variable)
- `BACKEND_ECR_REPOSITORY` (variable)
- `FRONTEND_ECR_REPOSITORY` (variable)
- `AGENT_CORE_ECR_REPOSITORY` (variable)

## Agent Core AWS Secrets (Secrets Manager JSON keys)

These keys must exist in the app Secrets Manager secret:

| Key | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | Yes | Embeddings for semantic search |
| `QDRANT_URL` | Yes | Vector DB endpoint |
| `QDRANT_API_KEY` | Yes | Vector DB auth |
| `AGENT_CORE_MEMORY_ID` | Optional | AWS Bedrock AgentCore Memory resource ID — omit to disable long-term memory |
| `AGENT_CORE_API_KEY` | Optional | Shared secret for backend→agent-core auth |

To provision a Memory resource, use the AWS console or add a `aws_bedrock_agentcore_memory` resource to Terraform once the provider supports it, then set `AGENT_CORE_MEMORY_ID` to the returned memory ID.

