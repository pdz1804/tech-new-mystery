# System Architecture

Tech News Mystery is a full-stack news discovery platform. The frontend is a
Next.js app, the backend is FastAPI, persistent data lives in DynamoDB, async
work is handled by Celery, and AI processing uses AWS Bedrock with OpenAI as a
fallback.

## Runtime Components

```mermaid
flowchart LR
  User[Browser] --> Frontend[Next.js frontend]
  Frontend --> Api[FastAPI API]
  Api --> Dynamo[(DynamoDB)]
  Api --> S3[(S3 article images)]
  Api --> Redis[(Redis)]
  Api --> Bedrock[AWS Bedrock]
  Api --> OpenAI[OpenAI fallback]
  Api --> Qdrant[Qdrant vector DB]
  Api --> Tavily[Tavily Search]
  Api --> NewsAPI[NewsAPI]
  Worker[Celery worker] --> Redis
  Worker --> Dynamo
  Worker --> S3
  Worker --> Bedrock
  Beat[Celery beat scheduler] --> Redis
```

## Request Flow

```mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant F as Next.js Frontend
  participant A as FastAPI API
  participant D as DynamoDB
  participant R as Redis
  participant W as Celery Worker
  participant L as LLM Provider

  U->>F: Browse/search articles
  F->>A: GET /v1/articles or /v1/search
  A->>D: Query article tables
  D-->>A: Article data
  A-->>F: JSON response
  F-->>U: Render UI

  U->>F: Submit/search new source
  F->>A: POST admin/search or article create
  A->>R: Queue background job
  R-->>W: Deliver job
  W->>L: Summarize/categorize/extract
  W->>D: Store pending or published article
```

## Data Stores

| Store | Purpose |
| --- | --- |
| DynamoDB | Users, articles, comments, saves, likes, submissions, pending searches |
| S3 | Article image/object storage |
| Redis | Cache, Celery broker, Celery result backend |
| Qdrant | Vector search collection for article embeddings |

## DynamoDB Tables

```mermaid
erDiagram
  USERS {
    string user_id PK
    string username
    string role
  }
  ARTICLES {
    string article_id PK
    string slug
    string source_id
    number published_at
  }
  COMMENTS {
    string comment_id PK
    string article_id
    number created_at
  }
  USER_SAVES {
    string user_id PK
    string article_id SK
  }
  USER_LIKES {
    string user_id PK
    string article_id SK
  }
  USER_PREFERENCES {
    string user_id PK
  }
  NEWS_SOURCES {
    string source_id PK
  }
  TRENDING_ARTICLES {
    string trending_id PK
  }
  SUBMISSIONS {
    string submission_id PK
    string user_id
    number submitted_at
  }
  PENDING_SEARCHES {
    string search_id PK
    string status
  }

  USERS ||--o{ USER_SAVES : saves
  USERS ||--o{ USER_LIKES : likes
  USERS ||--o{ COMMENTS : writes
  ARTICLES ||--o{ COMMENTS : receives
  ARTICLES ||--o{ USER_SAVES : saved_as
  ARTICLES ||--o{ USER_LIKES : liked_as
```

## Why Four ECS Services?

The deployed ECS services map directly to separate runtime responsibilities:

| ECS service | Command | Why it exists |
| --- | --- | --- |
| `frontend` | `npm run start` | Serves the Next.js production UI |
| `api` | `uvicorn app.main:app` | Serves synchronous HTTP API requests |
| `worker` | `celery -A app.workers.celery_app worker` | Executes crawl/search/AI/background jobs |
| `beat` | `celery -A app.workers.celery_app beat` | Schedules recurring Celery tasks |

`worker` and `beat` are separate so the scheduler remains singleton-like while
workers can scale independently.

## Redis Resolution

Local and production use the same settings names, but different values:

```mermaid
flowchart TD
  Local[Local docker-compose] --> LocalRedis[redis://redis:6379]
  Manual[Manual backend .env] --> HostRedis[redis://localhost:6379]
  Prod[Terraform ECS task env] --> ElastiCache[redis://tech-news-mystery-prod-redis...:6379]
```

The application reads `REDIS_URL`, `CELERY_BROKER_URL`, and
`CELERY_RESULT_BACKEND` from environment variables through `backend/app/config.py`.
