# Clustering PCA Map

The Topics page includes a Neo4j-style article map. It visualizes article embeddings, not cluster counts.

## Purpose

The map helps users inspect semantic neighborhoods in the article corpus:

- each node is an article;
- node position comes from PCA over article embeddings;
- node color comes from the article's cluster assignment;
- hover shows the article title;
- click selects an article node and the detail panel links to the article by slug;
- drag lets users reposition nodes locally while exploring.

The visualization does not draw relationship edges because the system does not currently store graph relationships between articles.

## Data Flow

```text
GET /v1/clusters
  -> frontend receives visible cluster IDs
  -> GET /v1/clusters/pca-map?cluster_ids=...
  -> API checks Redis cache
  -> if cache miss: queue Celery task
  -> worker reads cluster assignments
  -> worker fetches article embeddings from Qdrant
  -> worker runs PCA
  -> worker writes map payload to Redis
  -> API returns cached map on next poll
```

## Backend Components

| File | Responsibility |
| --- | --- |
| `backend/app/api/v1/clusters/router.py` | Serves cached PCA map payloads and queues generation when missing. |
| `backend/app/services/cluster_pca_map_service.py` | Builds cache keys, fetches assignments/embeddings, runs PCA, and writes Redis cache entries. |
| `backend/app/workers/tasks/pca_map_tasks.py` | Celery task wrapper for PCA map generation. |
| `backend/app/workers/tasks/clustering_tasks.py` | Queues PCA map generation after clustering completes. |
| `backend/app/api/v1/clusters/schemas.py` | Response models for article points and cluster legend items. |

## API Contract

`GET /v1/clusters/pca-map`

Query parameters:

| Name | Type | Description |
| --- | --- | --- |
| `limit` | int | Maximum number of article nodes to project. Defaults to `250`; max `500`. |
| `cluster_ids` | repeated string | Optional cluster IDs. The frontend passes the visible clusters so the map matches the current list. |

Example:

```http
GET /v1/clusters/pca-map?limit=250&cluster_ids=cluster-1&cluster_ids=cluster-2
```

Response:

```json
{
  "status": "ready",
  "total_articles": 120,
  "total_clusters": 12,
  "points": [
    {
      "article_id": "article-id",
      "slug": "article-title-slug",
      "title": "Article title",
      "cluster_id": "cluster-id",
      "cluster_label": "AI Infrastructure",
      "x": -0.25,
      "y": 0.71,
      "confidence_score": 0.82
    }
  ],
  "clusters": [
    {
      "cluster_id": "cluster-id",
      "label": "AI Infrastructure",
      "color": "#3B82F6",
      "article_count": 14
    }
  ]
}
```

Status values:

| Status | Meaning |
| --- | --- |
| `ready` | Cached map is available. |
| `queued` | Cache miss; worker generation was queued. |
| `unavailable` | Cache or worker dispatch failed. The UI should keep the rest of the page usable. |

## Frontend Behavior

`frontend/src/app/topics/page.tsx` loads clusters first, then requests the PCA map for those cluster IDs.

When the response is `queued`, the UI:

1. shows a preparation state in the map panel;
2. polls `/clusters/pca-map` on an interval without requiring refresh;
3. renders the Neo4j-style node map when the cached payload is ready.

The map is intentionally node-only. Any future edge rendering should be backed by a real relationship source such as citation links, source co-occurrence, article similarity thresholds, or a graph database.

## Operational Notes

- Redis is the serving cache for PCA map payloads.
- Qdrant is the source of article embeddings.
- Celery workers perform the PCA work to keep API latency predictable.
- After clustering completes, the clustering task queues a default latest-cluster PCA map refresh.
- The frontend can still request a view-specific map for visible clusters; this creates a separate cache key.
