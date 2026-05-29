# Manual Startup

## Prerequisites

- Docker Desktop running (for Redis and agent-core)
- WSL Ubuntu with `venv_wsl` activated (for backend)
- Node.js 22 for frontend
- AWS credentials in `~/.aws/credentials` (us-west-2)

---

## 1. Start Redis (required by backend Celery)

```powershell
cd infra
docker compose up redis -d
```

---

## 2. Start Backend (WSL Ubuntu)

```bash
# In WSL terminal
wsl -d Ubuntu
cd /mnt/d/FPT/Demo/Tech-News-Mystery/backend
source venv_wsl/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 3. Start Agent Core (Docker)

```powershell
cd infra
docker compose up agent-core -d
```

Agent Core needs AWS credentials mounted. On Windows Docker Desktop, credentials
in `~/.aws` are automatically available via the AWS SDK credential chain.

**Required env vars** (set in `.env` or docker-compose overrides):
- `OPENAI_API_KEY` — for embeddings
- `QDRANT_URL` + `QDRANT_API_KEY` — for semantic search
- `MEMORY_ID` *(optional)* — AWS Bedrock AgentCore Memory resource ID (omit to disable long-term memory)
- `AGENT_CORE_API_KEY` *(optional)* — shared secret for backend authentication

---

## 4. Start Frontend

```powershell
cd frontend
npm install
npm run dev
```

---

## URLs

| Service | URL |
|---|---|
| Frontend | `http://localhost:3000` (or 3001 if 3000 in use) |
| Backend API | `http://localhost:8000` |
| Backend Swagger | `http://localhost:8000/docs` |
| Agent Core | `http://localhost:8080` |

---

## Health Checks

```bash
# Backend
curl http://localhost:8000/health

# Agent Core circuit breaker state
curl http://localhost:8000/health/agent-core

# Agent Core runtime (BedrockAgentCoreApp /ping)
curl http://localhost:8080/ping
```

---

## Start Everything via Docker Compose

```powershell
cd infra
docker compose up -d
```

Services: `redis`, `agent-core`, `api`, `celery-worker`, `celery-beat`, `frontend`.

---

## Celery Worker (optional, for background tasks)

```bash
# In WSL, same venv
cd /mnt/d/FPT/Demo/Tech-News-Mystery/backend
source venv_wsl/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
```
