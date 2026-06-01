# Clustering Guide

The clustering system groups published articles into semantic topics and powers `/topics`, cluster detail pages, admin evaluation screens, and the article embedding map.

## Pipeline Overview

```text
published articles
  -> embeddings from Qdrant or OpenAI
  -> clustering/evaluation in Celery
  -> cluster metadata + article assignments in DynamoDB
  -> worker-precomputed PCA map in Redis
  -> topic UI and APIs
```

## Components

| Component | Responsibility |
| --- | --- |
| `EmbeddingService` | Builds embedding text and generates OpenAI `text-embedding-3-small` vectors when missing. |
| `QdrantService` | Stores and retrieves article vectors for semantic search and PCA map generation. |
| `ClusteringEngine` | Runs HDBSCAN clustering for scheduled clustering jobs. |
| `EvaluationPipeline` | Evaluates k-values with Silhouette, Davies-Bouldin, and Calinski-Harabasz metrics. |
| `clustering_tasks.py` | Celery orchestration for clustering, evaluation handoff, metadata persistence, and PCA map refresh. |
| `cluster_pca_map_service.py` | Builds article-level PCA payloads from cluster assignments and embeddings. |
| `pca_map_tasks.py` | Celery task for cacheable PCA map generation. |

## Data Model

| Table / Store | Purpose |
| --- | --- |
| DynamoDB `article_clusters` | Maps `cluster_id -> article_id` with assignment confidence. |
| DynamoDB `cluster_metadata` | Cluster labels, descriptions, keywords, top articles, counts, and evaluation ID. |
| DynamoDB `clustering_evaluation` | Historical evaluation results and selected k-values. |
| Qdrant article collection | Article embeddings and searchable article metadata. |
| Redis | Celery broker/backend plus cached PCA map payloads. |

## Latest Evaluation Filtering

`GET /v1/clusters` scans cluster metadata, filters to the latest `evaluation_id`, sorts the filtered result, and paginates in memory. That means UI copy like `12 visible / 14 topics in latest clustering set` is page size versus latest-evaluation total.

## PCA Map

The map is article-level, not cluster-level:

- each point is one article;
- coordinates come from PCA over article embeddings;
- colors represent cluster assignments;
- no edges are drawn because the system does not store graph relationships;
- frontend nodes are draggable and clickable for inspection.

The API does not run PCA inline. `GET /v1/clusters/pca-map` serves Redis-cached payloads and queues `tasks.generate_cluster_pca_map` on cache miss. See [CLUSTERING_PCA_MAP.md](CLUSTERING_PCA_MAP.md).

## Main Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/v1/clusters` | List latest-evaluation clusters with pagination and sorting. |
| `GET` | `/v1/clusters/pca-map` | Cached article embedding map; queues worker generation when missing. |
| `GET` | `/v1/clusters/trending` | Top trending clusters. |
| `GET` | `/v1/clusters/{cluster_id}` | Cluster detail with paginated articles. |
| `GET` | `/v1/clusters/{cluster_id}/articles` | Articles in one cluster. |
| `GET` | `/v1/admin/clustering/evaluations` | Evaluation history. |
| `POST` | `/v1/admin/clustering/evaluations/trigger` | Queue manual clustering evaluation. |

## Worker Flow

Scheduled clustering runs from Celery Beat at 06:00 and 18:00 UTC.

```text
tasks.cluster_articles
  -> fetch articles
  -> get/generate embeddings
  -> cluster or apply selected k
  -> save assignments and metadata
  -> optionally queue evaluation
  -> queue PCA map refresh
```

Manual evaluation can also queue clustering with the selected k-value. After the cluster metadata is saved, PCA map refresh is queued so the UI can serve a fresh cached visualization.

## Configuration

Important environment variables:

```bash
CLUSTERING_ENABLED=true
CLUSTERING_MIN_CLUSTER_SIZE=5
CLUSTERING_MIN_SAMPLES=3
CLUSTERING_K_MIN=5
CLUSTERING_K_MAX=100
CLUSTERING_SILHOUETTE_WEIGHT=0.4
CLUSTERING_DAVIES_BOULDIN_WEIGHT=0.3
CLUSTERING_CALINSKI_HARABASZ_WEIGHT=0.3
CLUSTERING_TTL_DAYS=7
```

## Troubleshooting

### Topic count looks wrong

Check whether you are comparing visible page count to latest-evaluation total. The first page may show 12 visible topics while the API reports 14 total latest topics.

### PCA map stays queued

1. Confirm Celery worker is running.
2. Confirm Redis is reachable from API and worker.
3. Check worker logs for `tasks.generate_cluster_pca_map`.
4. Confirm Qdrant has embeddings for the article IDs in the selected clusters.

### Missing article nodes

The PCA map only includes articles that have embeddings in Qdrant. Missing embeddings are skipped rather than blocking the map.

### Avoid fake graph edges

Do not draw edges unless the backend provides a real relationship source. Similarity edges, citation edges, source co-occurrence, or explicit article relationships can be added later as a separate feature.

## Tests And Checks

```powershell
cd backend
pytest tests/test_clustering_engine.py
pytest tests/test_clustering_tasks.py
python -m py_compile app/api/v1/clusters/router.py app/services/cluster_pca_map_service.py

cd ../frontend
npm run type-check
```
