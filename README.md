# Tech News Mystery

Tech News Mystery is a full-stack tech news application with two major AI features:
- Semantic article clustering (HDBSCAN + evaluation metrics)
- Chatbot with a separate Agent Core runtime (LangGraph + LangChain + Bedrock)

## Current Feature Status

### Clustering
- Backend clustering pipeline is implemented with:
  - OpenAI embeddings (`text-embedding-3-small`)
  - HDBSCAN clustering (`metric=cosine`, `algorithm=generic`)
  - Quality metrics: Silhouette, Davies-Bouldin, Calinski-Harabasz
  - Evaluation persistence and trending/list/detail APIs
- Frontend topics/cluster pages are integrated in the main app.

### Chatbot
- Chat is integrated as `/chatbot` in the existing frontend app (not a separate frontend).
- Chat sessions/messages are persisted in DynamoDB:
  - `tech-news-conversation_sessions`
  - `tech-news-conversation_messages`
- Backend supports create/list/get/rename/archive/restore/delete sessions and SSE streaming.
- Backend streams to a separate `agent-core` service via HTTP and persists user/assistant messages.

## Runtime Architecture

- `frontend`: Next.js
- `api`: FastAPI
- `worker`: Celery worker
- `beat`: Celery beat scheduler
- `agent-core`: separate agent runtime service (LangGraph/LangChain/Bedrock)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/DEPLOYMENT_ARCHITECTURE.md](docs/DEPLOYMENT_ARCHITECTURE.md).

## CI/CD and Infra

- App CI/CD: `.github/workflows/deploy.yml`
  - Runs backend/frontend checks
  - Builds and pushes images for `backend`, `frontend`, and `agent-core`
  - Forces ECS rollout for `api`, `frontend`, `worker`, `beat`, `agent-core`
- Terraform workflow: `.github/workflows/terraform.yml`
  - `fmt`, `init`, `validate`, `plan`
  - `apply` on push to `main`

## Local Development

1. Start infrastructure services:
```powershell
cd infra
docker compose up redis agent-core
```

2. Start backend:
```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

3. Start frontend:
```powershell
cd frontend
npm install
npm run dev
```

Local URLs:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Agent Core health: `http://localhost:8080/health`

## Docs Index

- [docs/README.md](docs/README.md)
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DEPLOYMENT_ARCHITECTURE.md](docs/DEPLOYMENT_ARCHITECTURE.md)
- [docs/MANUAL_STARTUP.md](docs/MANUAL_STARTUP.md)
- [docs/GITHUB_CICD.md](docs/GITHUB_CICD.md)

