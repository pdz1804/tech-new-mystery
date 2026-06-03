# Documentation

This folder contains the durable engineering references for Tech News Mystery. The root [README](../README.md) is the product overview and quick start; this folder is for the deeper implementation details.

## Core References

| Document | What It Covers |
| --- | --- |
| [Architecture](ARCHITECTURE.md) | Full system architecture — services, data stores, chat and voice request flows, ingestion pipeline, observability, and Mermaid diagrams. |
| [Deployment Architecture](DEPLOYMENT_ARCHITECTURE.md) | AWS infrastructure topology, VPC/network design, ECS service config, voice-provider secrets, CI/CD pipeline, and local dev environment. |
| [API Reference](API_REFERENCE.md) | Current HTTP endpoints and response behavior, including chat SSE and voice-agent endpoints. |
| [Manual Startup](MANUAL_STARTUP.md) | Local service startup, ports, and health checks. |
| [CI/CD Configuration](CI_CD_CONFIGURATION.md) | GitHub Actions, ECS deployment variables, secrets, and troubleshooting. |

## Product Areas

| Document | What It Covers |
| --- | --- |
| [Chatbot Guide](CHATBOT_GUIDE.md) | Chat sessions, streaming, Agent Core integration, persistence, and troubleshooting for the text-chat mode. |
| [Agent Core](AGENT_CORE.md) | LangGraph chat and voice runtimes, active tools, memory, prompts, streaming, and current scope. |
| [Voice Agent Implementation](VOICE_AGENT_IMPLEMENTATION.md) | LiveKit + ElevenLabs STT/TTS voice path, LangSmith telemetry, VAD, talk-over interruption, voice UX, metrics, and edge-case handling. |
| [Dialable Voice Agent Blueprint](DIALABLE_VOICE_AGENT_BLUEPRINT.md) | Target architecture for a responsive web voice bot and dialable LiveKit SIP voice agent, including turn-taking, interruption, DTMF, noise cancellation, and references. |
| [LiveKit Voice Worker](../backend/LIVEKIT_VOICE_WORKER.md) | Local and production runbook for the dialable SIP worker, phone-number routing, barge-in behavior, and real-call diagnostics. |
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
