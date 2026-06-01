# Documentation Index

This folder contains operational and engineering documentation for Tech News Mystery. The root [README](../README.md) is the project front door; this index points to deeper references.

## Start Here

| Document | Use When |
| --- | --- |
| [Architecture](ARCHITECTURE.md) | You need the system map, service responsibilities, data stores, and major flows. |
| [API Reference](API_REFERENCE.md) | You need current HTTP endpoints and response behavior. |
| [Manual Startup](MANUAL_STARTUP.md) | You need to run the stack locally. |
| [Deployment Architecture](DEPLOYMENT_ARCHITECTURE.md) | You need production infrastructure context. |

## Product Features

| Document | Scope |
| --- | --- |
| [Chatbot Guide](CHATBOT_GUIDE.md) | Chat sessions, SSE streaming, Agent Core integration, and troubleshooting. |
| [Chatbot Feature Spec](CHATBOT_FEATURE_SPEC.md) | Long-form design notes and historical requirements for chat. |
| [Clustering Guide](CLUSTERING_GUIDE.md) | Clustering pipeline, worker flow, tables, APIs, and operational guidance. |
| [Clustering PCA Map](CLUSTERING_PCA_MAP.md) | Worker-backed Neo4j-style article embedding map. |
| [Clustering Feature Spec](CLUSTERING_FEATURE_SPEC.md) | Long-form design notes and historical requirements for clustering. |
| [Crawl4AI Guide](CRAWL4AI_GUIDE.md) | Article crawling and scraping integration. |

## Frontend

| Document | Scope |
| --- | --- |
| [Frontend Documentation Index](frontend/DOCUMENTATION_INDEX.md) | Current frontend docs map. |
| [Design System](frontend/DESIGN_SYSTEM.md) | Visual language, Liquid Glass patterns, colors, spacing, and components. |

## Delivery And Infrastructure

| Document | Scope |
| --- | --- |
| [CI/CD Configuration](CI_CD_CONFIGURATION.md) | Workflow configuration and deployment variables. |
| [CI/CD Readiness](CI_CD_READINESS.md) | Readiness checklist for CI/CD rollout. |
| [GitHub CI/CD](GITHUB_CICD.md) | Short guide to GitHub workflow behavior. |
| [Terraform Deployment Manual](DEPLOYMENT_MANUAL_TERRAFORM.md) | Manual Terraform deployment flow. |
| [Terraform CI/CD Issues](TERRAFORM_CI_CD_ISSUES.md) | Known Terraform workflow issues and fixes. |

## Investigations And Working Notes

| Document | Notes |
| --- | --- |
| [Streaming Lag Investigation](STREAMING_LAG_INVESTIGATION.md) | Historical analysis of chat streaming latency. |
| [Startup Correct Commands](STARTUP_CORRECT_COMMANDS.md) | Quick command reference for local startup. |
| [Tasks](TASKS.md) | Historical task planning and implementation notes. |

## Documentation Hygiene

- Prefer updating the concise guides first: `ARCHITECTURE.md`, `API_REFERENCE.md`, and feature guides.
- Keep large feature specs only when they preserve design rationale that is not captured elsewhere.
- Avoid adding new “status complete” reports unless they are tied to a release or incident.
- Link new operational behavior from this index and the root README.
