# Documentation

This folder contains the durable engineering references for Tech News Mystery. The root [README](../README.md) is the product overview and quick start; this folder is for the deeper implementation details.

## Core References

| Document | What It Covers |
| --- | --- |
| [Architecture](ARCHITECTURE.md) | Full system architecture — all services, data stores, request flows, and Mermaid diagrams for the chat pipeline, ingestion pipeline, and LLM fallback chain. |
| [Deployment Architecture](DEPLOYMENT_ARCHITECTURE.md) | AWS infrastructure topology, VPC/network design, ECS service config, Secrets Manager, CI/CD pipeline, and local dev environment — all with Mermaid diagrams. |
| [API Reference](API_REFERENCE.md) | Current HTTP endpoints and response behavior. |
| [Manual Startup](MANUAL_STARTUP.md) | Local service startup, ports, and health checks. |
| [CI/CD Configuration](CI_CD_CONFIGURATION.md) | GitHub Actions, ECS deployment variables, secrets, and troubleshooting. |

## Product Areas

| Document | What It Covers |
| --- | --- |
| [Chatbot Guide](CHATBOT_GUIDE.md) | Chat sessions, streaming, Agent Core integration, persistence, and troubleshooting. |
| [Agent Core](AGENT_CORE.md) | LangGraph agent runtime, tools, memory, prompts, streaming, and current scope. |
| [Voice Agent Implementation](VOICE_AGENT_IMPLEMENTATION.md) | LiveKit + ElevenLabs STT/TTS voice path, LangSmith telemetry, voice UX, metrics, and edge-case handling. |
| [Clustering Guide](CLUSTERING_GUIDE.md) | Topic clustering, evaluations, worker flow, tables, and operations. |
| [Clustering PCA Map](CLUSTERING_PCA_MAP.md) | Worker-backed article embedding projection and Neo4j-style map behavior. |
| [Crawl4AI Guide](CRAWL4AI_GUIDE.md) | Article crawling and extraction behavior. |

## Frontend

| Document | What It Covers |
| --- | --- |
| [Frontend Documentation Index](frontend/DOCUMENTATION_INDEX.md) | Current frontend routes, components, and UI direction. |
| [Design System](frontend/DESIGN_SYSTEM.md) | Liquid Glass visual language, tokens, motion, layout, and accessibility guidance. |

## Documentation Rules

- Keep the root README product-focused and friendly for first-time readers.
- Put technical implementation details in the guides above instead of expanding the README forever.
- Avoid new one-off status reports, task dumps, or historical investigation notes unless they document an active incident.
- When behavior changes, update the closest durable guide and link it here.
