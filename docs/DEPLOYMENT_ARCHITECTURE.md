# Deployment Architecture

Production is deployed to AWS `us-west-2` with Terraform in
`infra/terraform`.

## AWS Topology

```mermaid
flowchart TB
  Internet((Internet)) --> ALB[Application Load Balancer]

  subgraph VPC[tech-news-mystery-prod VPC]
    subgraph Public[Public subnets]
      ALB
      FrontendSvc[ECS service: frontend]
      ApiSvc[ECS service: api]
      WorkerSvc[ECS service: worker]
      BeatSvc[ECS service: beat]
    end

    subgraph Private[Private subnets]
      Redis[(ElastiCache Redis)]
    end
  end

  ALB -->|/| FrontendSvc
  ALB -->|/v1/* and /health| ApiSvc

  ApiSvc --> Dynamo[(DynamoDB)]
  ApiSvc --> S3[(S3 images bucket)]
  ApiSvc --> Redis
  WorkerSvc --> Redis
  WorkerSvc --> Dynamo
  WorkerSvc --> S3
  BeatSvc --> Redis

  ApiSvc --> Secrets[Secrets Manager]
  WorkerSvc --> Secrets
  BeatSvc --> Secrets
  ApiSvc --> Bedrock[AWS Bedrock]
  WorkerSvc --> Bedrock
```

## CI/CD Flow

```mermaid
flowchart LR
  PR[Pull request] --> Checks[Backend and frontend checks]
  Main[Push to main] --> Checks
  Checks --> Build[Build backend and frontend images]
  Build --> ECR[ECR images]
  ECR --> ECS[ECS force new deployment]
  ECS --> ALB[Public ALB URL]
  Infra[Manual Terraform CLI] -. only when infra changes .-> AWSInfra[AWS infrastructure]
```

The active GitHub workflow is `.github/workflows/deploy.yml`. The Terraform
workflow is parked as `.github/workflows/terraform.yml.bak`, so app commits do
not automatically redeploy infrastructure.

## Terraform State

```mermaid
flowchart LR
  Terraform[Terraform CLI] --> StateBucket[(S3 tfstate bucket)]
  Terraform --> LockTable[(DynamoDB lock table)]
  Terraform --> AWS[AWS resources]
```

State backend resources:

| Resource | Name |
| --- | --- |
| S3 state bucket | `tech-news-mystery-tfstate-381492273521` |
| DynamoDB lock table | `tech-news-mystery-terraform-locks` |

## Existing Imported Resources

These resources existed before Terraform and are imported into state:

| Type | Name |
| --- | --- |
| S3 bucket | `tech-news-articles-381492273521` |
| DynamoDB table | `tech-news-users` |
| DynamoDB table | `tech-news-articles` |
| DynamoDB table | `tech-news-comments` |
| DynamoDB table | `tech-news-user_saves` |
| DynamoDB table | `tech-news-user_likes` |
| DynamoDB table | `tech-news-user_preferences` |
| DynamoDB table | `tech-news-news_sources` |
| DynamoDB table | `tech-news-pending-searches` |
| DynamoDB table | `tech-news-trending_articles` |
| DynamoDB table | `tech-news-submissions` |

## Operational Checks

```powershell
terraform output
aws ecs describe-services --region us-west-2 --cluster tech-news-mystery-prod --services frontend api worker beat
aws logs tail /ecs/tech-news-mystery-prod --region us-west-2 --follow
```
