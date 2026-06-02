# Frontend Documentation Index

The frontend is a Next.js application that implements article discovery, topic exploration, the Agent workspace, profile, and admin workflows.

## Current References

| Document | Purpose |
| --- | --- |
| [Design System](DESIGN_SYSTEM.md) | Visual primitives, colors, spacing, glass surfaces, buttons, cards, and accessibility rules. |
| [Project Architecture](../ARCHITECTURE.md) | Service boundaries and frontend/backend integration points. |
| [API Reference](../API_REFERENCE.md) | HTTP endpoints used by frontend pages and hooks. |
| [Clustering PCA Map](../CLUSTERING_PCA_MAP.md) | Article embedding map data flow and UI behavior. |
| [Chatbot Guide](../CHATBOT_GUIDE.md) | Text-chat UI, SSE streaming, and session behavior. |
| [Voice Agent Implementation](../VOICE_AGENT_IMPLEMENTATION.md) | Voice-test UI, LiveKit room setup, ElevenLabs STT/TTS, VAD, and interruption behavior. |

## Important Routes

| Route | Description |
| --- | --- |
| `/` | Home and article discovery entry point. |
| `/articles` | Article browsing and filtering. |
| `/articles/[slug]` | Article detail page. |
| `/topics` | Topic list, search/sort controls, and Neo4j-style article embedding map. |
| `/topics/[slug]` | Cluster detail and articles in topic. |
| `/chatbot` | Agent workspace with separate text-chat sessions and voice-test sessions. |
| `/profile` | User settings, preferences, and saved content. |
| `/admin/*` | Admin queue, users, articles, search, and clustering controls. |

## UI Direction

The current product style follows an Apple Liquid Glass direction:

- translucent surfaces with restrained blur;
- soft borders and inset highlights;
- blue accent for active controls;
- compact controls and readable dense cards;
- no decorative glass where it reduces clarity.

For new frontend work, prefer existing components and tokens before introducing new styles.

## Notes

- The previous frontend documentation index referenced generated reports that are no longer present in the repository. This file intentionally links only to existing docs.
- Browser console warning `bis_skin_checked` is usually injected by a browser extension and should not be documented as an app hydration bug unless reproduced in a clean browser profile.
