# Clustering Feature Guide

## Overview

The clustering feature automatically groups articles into semantic topics using HDBSCAN density-based clustering. The system runs on a daily schedule (6am & 6pm UTC) via Celery Beat, processes embeddings with quality metrics, and stores results in DynamoDB.

## Architecture

### Components

| Component | Purpose |
| --- | --- |
| **Embedding Service** | Generates and caches article embeddings via OpenAI (text-embedding-3-small) |
| **HDBSCAN Engine** | Performs density-based clustering with automatic noise detection |
| **Evaluation Metrics** | Calculates Silhouette, Davies-Bouldin, and Calinski-Harabasz scores |
| **Evaluation Pipeline** | Sweeps k-values, ranks results, selects optimal clustering |
| **Celery Task** | Orchestrates the full pipeline on schedule with retries |
| **DynamoDB Tables** | Stores clusters, assignments, evaluations, and embeddings |

### Data Flow

```
Article Fetch
    ↓
Embedding Generation (batch 100, cached)
    ↓
HDBSCAN Clustering (min_cluster_size=5)
    ↓
Quality Metrics Calculation
    ↓
Evaluation Pipeline & K-Selection
    ↓
Store Results (DynamoDB, 7-day TTL)
    ↓
CloudWatch Metrics & Alerts
```

## DynamoDB Tables

### `tech-news-article_clusters`
Maps articles to clusters with reverse lookups.

| Key | Type | Purpose |
| --- | --- | --- |
| `cluster_id` (PK) | String | Cluster identifier |
| `article_id` (SK) | String | Article in cluster |
| `relevance_score` | Number | Relevance to cluster (0-1) |
| `created_at` | Number | Timestamp |
| `expires_at` (TTL) | Number | Auto-expire after 7 days |

**GSI:** `article_id-index` → reverse lookup articles

### `tech-news-cluster_metadata`
Cluster information and quality metrics.

| Key | Type | Purpose |
| --- | --- | --- |
| `cluster_id` (PK) | String | Cluster identifier |
| `cluster_label` | String | Human-readable label (AI-generated) |
| `num_articles` | Number | Article count in cluster |
| `silhouette_score` | Number | Cohesion metric (higher better, -1 to 1) |
| `davies_bouldin_index` | Number | Separation metric (lower better, ≥0) |
| `calinski_harabasz_index` | Number | Density metric (higher better, ≥0) |
| `created_at` | Number | Timestamp |
| `expires_at` (TTL) | Number | Auto-expire after 7 days |

### `tech-news-article_embeddings`
Cached embeddings to avoid re-computing.

| Key | Type | Purpose |
| --- | --- | --- |
| `article_id` (PK) | String | Article identifier |
| `embedding_vector` | Binary | 1536-dim OpenAI embedding |
| `embedding_model` | String | Model version (text-embedding-3-small) |
| `created_at` | Number | Timestamp |
| `expires_at` (TTL) | Number | Auto-expire after 7 days |

### `tech-news-clustering_evaluations`
Evaluation results for analysis and optimization.

| Key | Type | Purpose |
| --- | --- | --- |
| `evaluation_id` (PK) | String | Unique evaluation ID |
| `run_timestamp` | Number | When clustering ran |
| `k_value` | Number | Cluster count tested |
| `metrics` | Map | Silhouette, Davies-Bouldin, Calinski-Harabasz scores |
| `composite_score` | Number | Weighted metric score |
| `rank` | Number | Rank among all k-values tested |
| `selected` | Boolean | True if this k was selected |
| `expires_at` (TTL) | Number | Auto-expire after 7 days |

## API Endpoints

### List Clusters
**GET** `/v1/clusters`

Query parameters:
- `page` (int, default 1): Page number
- `page_size` (int, default 20): Items per page
- `sort_by` (str, default "size"): "size", "score", "created"

Response:
```json
{
  "success": true,
  "data": [
    {
      "cluster_id": "c-uuid",
      "label": "AI/ML Breakthroughs",
      "num_articles": 42,
      "silhouette_score": 0.76,
      "davies_bouldin_index": 0.85,
      "calinski_harabasz_index": 156.3,
      "created_at": 1717000000,
      "top_articles": [
        {"article_id": "a1", "title": "...", "relevance_score": 0.98}
      ]
    }
  ],
  "meta": {"total": 127, "page": 1, "limit": 20}
}
```

### Get Cluster Detail
**GET** `/v1/clusters/{cluster_id}`

Response:
```json
{
  "success": true,
  "data": {
    "cluster_id": "c-uuid",
    "label": "AI/ML Breakthroughs",
    "num_articles": 42,
    "silhouette_score": 0.76,
    "davies_bouldin_index": 0.85,
    "calinski_harabasz_index": 156.3,
    "articles": [
      {
        "article_id": "a1",
        "title": "...",
        "summary": "...",
        "relevance_score": 0.98,
        "created_at": 1717000000
      }
    ]
  }
}
```

### Get Clustering Evaluation Results
**GET** `/v1/admin/clustering/evaluations`

Query parameters:
- `run_timestamp` (int, optional): Filter by specific run
- `limit` (int, default 50): Max results

Response:
```json
{
  "success": true,
  "data": [
    {
      "evaluation_id": "eval-uuid",
      "run_timestamp": 1717000000,
      "k_value": 32,
      "metrics": {
        "silhouette_score": 0.76,
        "davies_bouldin_index": 0.85,
        "calinski_harabasz_index": 156.3
      },
      "composite_score": 0.84,
      "rank": 1,
      "selected": true
    }
  ]
}
```

## Backend Implementation

### Embedding Service
```python
# backend/app/services/embedding_service.py
from app.services.embedding_service import EmbeddingService

service = EmbeddingService()
embeddings_dict = await service.batch_embed_articles(articles)
# Returns: {article_id: embedding_vector}
```

Features:
- Batch processing (max 100 per API call)
- DynamoDB caching before API calls
- Exponential backoff (3 retries, 100s max wait)
- Handles edge cases: empty list, rate limits, timeouts

### HDBSCAN Clustering
```python
# backend/app/services/clustering_engine.py
from app.services.clustering_engine import ClusteringEngine

engine = ClusteringEngine(min_cluster_size=5, min_samples=3, metric="cosine")
assignments, stats = engine.cluster_articles(embeddings, article_ids)
# Returns: {article_id: cluster_id}, {num_clusters, num_noise, ...}
```

Features:
- HDBSCAN with cosine distance
- Automatic noise detection (cluster_id = -1)
- Handles edge cases: < 5 articles, constant embeddings
- Detailed statistics for monitoring

### Quality Metrics
```python
# backend/app/services/evaluation/
from app.services.evaluation.silhouette import calculate_silhouette_score
from app.services.evaluation.davies_bouldin import calculate_davies_bouldin_index
from app.services.evaluation.calinski_harabasz import calculate_calinski_harabasz_index

silhouette = await calculate_silhouette_score(embeddings, labels)
davies_bouldin = await calculate_davies_bouldin_index(embeddings, labels)
calinski_harabasz = await calculate_calinski_harabasz_index(embeddings, labels)
```

### Evaluation Pipeline
```python
# backend/app/services/evaluation/evaluation_pipeline.py
from app.services.evaluation.evaluation_pipeline import EvaluationPipeline

pipeline = EvaluationPipeline(k_min=5, k_max=100, step=5)
results = await pipeline.evaluate_clustering(embeddings, articles)
# Returns: {selected_k, evaluations, composite_scores}
```

Features:
- Sweeps k-values (5-100, every 5)
- Ranks by composite score
- Weighted metrics (admin-configurable)
- Stores all results in DynamoDB for analysis

### Celery Task
```python
# backend/app/workers/tasks/clustering_tasks.py
from app.workers.celery_app import app

@app.task(bind=True, max_retries=3)
def cluster_articles(self):
    # Orchestrates: fetch → embed → cluster → evaluate → store
```

Scheduled via Celery Beat:
```python
# backend/app/workers/celery_app.py
app.conf.beat_schedule = {
    'cluster_morning': {
        'task': 'app.workers.tasks.clustering_tasks.cluster_articles',
        'schedule': crontab(hour=6, minute=0),  # 6am UTC
    },
    'cluster_evening': {
        'task': 'app.workers.tasks.clustering_tasks.cluster_articles',
        'schedule': crontab(hour=18, minute=0),  # 6pm UTC
    },
}
```

## Frontend Implementation

### Topics Page
**Route:** `/topics`

Features:
- Displays all active clusters as topic cards
- Filters by metric (cohesion, separation, density)
- Search clusters by label
- Pagination (20 per page)

### Cluster Detail View
**Route:** `/topics/[cluster_id]`

Features:
- Cluster metadata and metrics
- Top 50 articles in cluster
- Relevance scores
- Visual metrics display (bars, gauges)

### Visualization
- 3-metric plot showing cluster quality
- Time-series trends of metric values
- K-value sweep results chart

## Monitoring

### CloudWatch Metrics
```
clustering/run_duration_seconds (histogram)
clustering/num_articles_processed (count)
clustering/num_clusters_created (count)
clustering/noise_percentage (gauge)
clustering/silhouette_score (gauge)
clustering/davies_bouldin_index (gauge)
clustering/calinski_harabasz_index (gauge)
clustering/task_success (counter)
clustering/task_error (counter)
```

### CloudWatch Alarms
```
clustering_task_failure: task fails 2+ times
clustering_high_noise: noise > 20%
clustering_poor_quality: silhouette < 0.5
clustering_duration_exceeded: > 5 minutes
```

## Configuration

### Environment Variables
```bash
# Clustering
CLUSTERING_ENABLED=true
CLUSTERING_MIN_CLUSTER_SIZE=5
CLUSTERING_MIN_SAMPLES=3
CLUSTERING_MAX_SEARCH_RESULTS=5
CLUSTERING_K_MIN=5
CLUSTERING_K_MAX=100
CLUSTERING_K_STEP=5

# Evaluation weights (must sum to 1.0)
CLUSTERING_SILHOUETTE_WEIGHT=0.4
CLUSTERING_DAVIES_BOULDIN_WEIGHT=0.3
CLUSTERING_CALINSKI_HARABASZ_WEIGHT=0.3

# DynamoDB TTL
CLUSTERING_TTL_DAYS=7
```

### Admin Weights Configuration
Admin users can adjust metric weights via the settings API:
```
POST /v1/admin/clustering/config
{
  "silhouette_weight": 0.5,
  "davies_bouldin_weight": 0.3,
  "calinski_harabasz_weight": 0.2
}
```

## Troubleshooting

### Clustering Task Not Running
1. Check Celery Beat is running: `celery -A app.workers.celery_app beat --loglevel=debug`
2. Verify schedule in CloudWatch logs
3. Check DynamoDB tables exist (Terraform)
4. Verify IAM role has DynamoDB permissions

### Poor Clustering Quality (Low Silhouette Score)
1. Check article embeddings are diverse
2. Reduce `min_cluster_size` if too few clusters
3. Increase articles in corpus (need > 100 for good results)
4. Review evaluation results for optimal k-value

### Embedding API Rate Limits
1. Batch size is auto-limited to 100 per call
2. Cache is checked before API calls
3. Exponential backoff with max 3 retries
4. Check OpenAI quota and usage

### Missing or Stale Clusters
1. Verify scheduling: `SELECT * FROM celery.beat_schedule`
2. Check TTL expiration: DynamoDB auto-deletes after 7 days
3. Manually trigger: `celery -A app.workers.celery_app call app.workers.tasks.clustering_tasks.cluster_articles`

## Performance

| Operation | Time | Notes |
| --- | --- | --- |
| Fetch 500 articles | 100ms | DynamoDB query |
| Generate embeddings (100 articles) | 2s | OpenAI API |
| Cache lookup (1000 articles) | 50ms | DynamoDB batch |
| HDBSCAN clustering (500 articles) | 3s | Cosine distance |
| Metrics calculation | 1s | Scikit-learn |
| Evaluation pipeline (96 k-values) | 2m | Full sweep |
| Total end-to-end | < 5 min | For 500 articles |

## Testing

### Unit Tests
```bash
cd backend
pytest tests/test_clustering_engine.py
pytest tests/test_embedding_service.py
pytest tests/test_clustering_metrics.py
pytest tests/test_evaluation_pipeline.py
```

### Integration Tests
```bash
pytest tests/test_clustering_integration.py
pytest tests/test_clustering_tasks.py
```

### E2E Tests
```bash
pytest tests/test_clustering_e2e.py
# Or manually:
# 1. Create test articles
# 2. Trigger clustering task
# 3. Verify DynamoDB results
# 4. Check metrics and UI
```

## Cost Estimation

### Monthly (500 articles/day)

| Service | Cost | Notes |
| --- | --- | --- |
| DynamoDB (on-demand) | $5-10 | 15M writes/month at $1.25 per M |
| OpenAI Embeddings | $15-20 | 15K articles × $0.02 per 1K |
| Compute (Celery) | $5-10 | Included in ECS allocation |
| CloudWatch (logs, metrics) | $2-5 | 200GB logs at $0.50 per GB |
| **Total** | **$27-45** | Scales linearly |

## Future Enhancements

- [ ] Multi-language clustering
- [ ] Real-time clustering updates (instead of fixed schedule)
- [ ] Custom clustering algorithms (configurable)
- [ ] Hierarchical clustering visualization
- [ ] Topic name suggestions via LLM
- [ ] A/B testing framework for metrics
- [ ] Cluster drift detection

## References

- [HDBSCAN Documentation](https://hdbscan.readthedocs.io/)
- [Scikit-learn Clustering Metrics](https://scikit-learn.org/stable/modules/clustering.html#clustering-evaluation)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [Celery Documentation](https://docs.celeryproject.io/)
