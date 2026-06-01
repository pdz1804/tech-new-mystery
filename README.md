# Tech News Mystery

Tech News Mystery is an AI-powered technology news workspace. It collects articles, turns them into searchable knowledge, groups them into live topic clusters, and gives users a chat assistant for exploring what is happening across the tech landscape.

The README is intentionally product-first. For architecture, APIs, deployment, and operational details, start with the [documentation index](docs/README.md).

## What You Can Do

- Discover recent technology articles in a clean, searchable interface.
- Browse semantic topic clusters instead of scanning isolated article lists.
- See clustered articles as an interactive embedding map, with article nodes colored by topic.
- Drag, hover, and inspect article dots in a Neo4j-style topic view.
- Sort topics by size, recency, or diversity to understand what is broad, fresh, or varied.
- Retrigger clustering from the UI when new data should be regrouped.
- Ask the chatbot questions about the article corpus and receive streamed responses.
- Keep chat sessions so follow-up research does not disappear between page loads.
- Use semantic search so related stories can be found even when keywords do not match exactly.
- Run background crawling, embedding, clustering, evaluation, summaries, and map preparation jobs.
- Operate the system locally or deploy it with the included cloud infrastructure.
- Use admin and health endpoints to inspect system behavior during development and production checks.

## Main Experiences

### Article Discovery

The Discover experience is the main entry point for browsing technology news. Users can search articles, inspect details, and move from individual stories into broader topics.

### Topics And Clustering

The Topics page groups articles by meaning, not by exact keyword. It shows the latest clustering set and provides a visual map where each dot represents an article. Dot color comes from the cluster assignment, and labels stay out of the way until the user hovers or selects a node.

The heavy map preparation work runs in background workers, so the UI can stay responsive while embeddings are projected into two dimensions.

Technical details: [Clustering Guide](docs/CLUSTERING_GUIDE.md) and [Clustering PCA Map](docs/CLUSTERING_PCA_MAP.md).

### Chat Assistant

The Chat experience lets users ask questions about the news corpus. Responses stream back into the UI, sessions are persisted, and the assistant can use semantic retrieval to ground answers in relevant articles.

Technical details: [Chatbot Guide](docs/CHATBOT_GUIDE.md).

### Apple-Inspired Interface

The frontend uses a restrained Liquid Glass direction: translucent surfaces, soft borders, layered depth, compact controls, and responsive layouts that keep the product usable on desktop and smaller screens.

Design details: [Design System](docs/frontend/DESIGN_SYSTEM.md).

## Capabilities At A Glance

| Area | Capabilities |
| --- | --- |
| News ingestion | Crawl articles, extract readable content, store normalized article records. |
| Search | Keyword search, semantic search, and retrieval for chat/tooling flows. |
| Topics | Cluster articles, label topics, evaluate clustering quality, surface latest results. |
| Visualization | Worker-prepared PCA map, cluster-colored article nodes, hover/click inspection. |
| Chat | Streaming responses, persisted conversations, semantic article lookup, Agent Core integration. |
| Background work | Celery jobs for crawling, embedding, clustering, summaries, evaluations, and PCA maps. |
| Operations | Health checks, admin APIs, Terraform infrastructure, CI/CD configuration, local startup docs. |

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker Desktop
- AWS credentials for cloud-backed development paths
- OpenAI API key for embedding generation

### Start Local Services

```powershell
cd infra
docker compose up redis agent-core
```

### Start Backend

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Worker

```powershell
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

### Start Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Local URLs

| Target | URL |
| --- | --- |
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| Agent Core health | `http://localhost:8080/health` |

For the full startup sequence, ports, and health checks, see [Manual Startup](docs/MANUAL_STARTUP.md).

## Documentation

- [Documentation Index](docs/README.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Clustering Guide](docs/CLUSTERING_GUIDE.md)
- [Clustering PCA Map](docs/CLUSTERING_PCA_MAP.md)
- [Chatbot Guide](docs/CHATBOT_GUIDE.md)
- [Agent Core](docs/AGENT_CORE.md)
- [Crawl4AI Guide](docs/CRAWL4AI_GUIDE.md)
- [Deployment Architecture](docs/DEPLOYMENT_ARCHITECTURE.md)
- [CI/CD Configuration](docs/CI_CD_CONFIGURATION.md)
- [Frontend Design System](docs/frontend/DESIGN_SYSTEM.md)

## Repository Layout

```text
agent_core/        Agent runtime service for chat orchestration
backend/           FastAPI app, workers, repositories, services, tests
frontend/          Next.js app and UI components
infra/             Docker Compose and Terraform infrastructure
docs/              Durable architecture, product, operations, and frontend guides
scripts/           Operational helper scripts
```

## Developer Notes

- Browser warning `Extra attributes from the server: bis_skin_checked` is usually caused by a browser extension injecting attributes before React hydration. It is not generated by this codebase.
- The topic map does not invent relationship edges. It visualizes article embeddings as PCA-projected nodes colored by cluster.
- Heavy operations belong in workers. API routes should serve cached state, enqueue work, or stream lightweight events.

## License

See [LICENSE](LICENSE).
