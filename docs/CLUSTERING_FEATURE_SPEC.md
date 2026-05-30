# Clustering Feature Specification

**Version:** 1.0  
**Date:** May 28, 2026  
**Status:** Ready for Implementation  

---

## Executive Summary

The Clustering Feature automatically groups related articles into semantic topics, enabling users to browse news by thematic clusters rather than individual articles. This feature leverages **HDBSCAN** clustering on article embeddings to identify meaningful topic groups, with results available through a new `/v1/clusters` API endpoint and a dedicated **Topics** section in the frontend.

**What:** Semantic article clustering with automatic topic detection  
**Why:** Improve content discovery, reduce information redundancy, organize news by themes  
**How:** Embed articles using OpenAI text-embedding-3-small, cluster with HDBSCAN, generate cluster labels via Claude Haiku (Bedrock), cache results in DynamoDB, schedule daily batch processing at 6am & 6pm UTC  

---

## Algorithm Selection: HDBSCAN

**Why HDBSCAN over alternatives:**

| Aspect | HDBSCAN | K-Means | Hierarchical |
|--------|---------|---------|-------------|
| Noise detection | Native (outliers) | No | No |
| Dynamic clusters | Auto-sizes clusters | Fixed K | Requires threshold |
| Scalability | O(n log n) | O(n*k) | O(n²) |
| Production readiness | Mature, stable | Requires tuning | Expensive |

**Parameters:**
```python
hdbscan.HDBSCAN(
    min_cluster_size=5,           # At least 5 articles per cluster
    min_samples=3,                # At least 3 neighbors to form core point
    metric='cosine',              # Cosine distance for embeddings
    cluster_selection_epsilon=0.0 # Auto-select stable clusters
)
```

**Behavior:**
- Automatically determines optimal number of clusters
- Identifies and removes noise (articles that don't fit well into any cluster)
- Produces stable, human-interpretable topic groups

---

## Clustering Quality Evaluation & K-Value Selection

### Overview

While HDBSCAN automatically determines cluster count, evaluation metrics provide quantitative assessment of clustering quality and enable data-driven k-value selection. Three complementary metrics evaluate different aspects of cluster quality, with an admin-controlled weighted scoring system to select optimal k.

### 1. Three Clustering Quality Metrics

**a) Silhouette Score**
- **Measures:** How similar an article is to its own cluster vs other clusters
- **Range:** -1 to 1
- **Interpretation:** Higher is better
  - \> 0.7: Excellent cluster separation
  - 0.5 - 0.7: Good cluster structure
  - 0.25 - 0.5: Weak cluster structure
  - < 0.25: Overlapping clusters
- **Formula:** For each point i: s(i) = (b(i) - a(i)) / max(a(i), b(i))
  - a(i) = mean intra-cluster distance (distance to cluster members)
  - b(i) = mean inter-cluster distance (distance to nearest other cluster)
- **Use Case:** Overall cluster cohesion and separation quality; sensitive to cluster overlap
- **Computation:** O(n²) for n articles

**b) Davies-Bouldin Index**
- **Measures:** Average ratio of within-cluster to between-cluster distances
- **Range:** 0 to ∞
- **Interpretation:** Lower is better
  - < 1.0: Excellent cluster separation (compact, well-separated clusters)
  - 1.0 - 2.0: Good cluster separation
  - \> 2.0: Poor cluster separation (overlapping, diffuse clusters)
- **Formula:** DB = (1/k) × Σ max(R_ij) where R_ij = (σ_i + σ_j) / d(c_i, c_j)
  - σ_i = average distance of points in cluster i to centroid
  - d(c_i, c_j) = distance between cluster centroids i and j
  - max(R_ij) = largest ratio for cluster i with any other cluster j
- **Use Case:** Cluster tightness and separation quality; measures both compactness and isolation
- **Computation:** O(k²) for k clusters (efficient)

**c) Calinski-Harabasz Index**
- **Measures:** Ratio of between-cluster variance to within-cluster variance
- **Range:** 0 to ∞
- **Interpretation:** Higher is better
  - \> 100: Very dense, well-separated clusters
  - 50 - 100: Good cluster density and definition
  - 25 - 50: Moderate cluster quality
  - < 25: Poor cluster definition
- **Formula:** CH = (SS_between / (k-1)) / (SS_within / (n-k))
  - SS_between = sum of squared distances of cluster centroids from global centroid
  - SS_within = sum of squared distances within clusters
  - k = number of clusters
  - n = total number of articles
- **Use Case:** Cluster density and definition; captures global cluster structure
- **Computation:** O(n) (most efficient of the three)

### 2. Evaluation Process

**Step 1: Parameter Sweep**
1. Define k range (e.g., min_k=5 to max_k=100)
2. For each k value:
   - Run HDBSCAN with k-means-like clustering or fixed k parameter
   - Validate: Ensure min 5 articles per cluster (same as HDBSCAN default)
   - Handle edge cases: If k > available clusters, use auto HDBSCAN result

**Step 2: Metric Calculation**
For each k value:
1. Calculate Silhouette Score:
   - `from sklearn.metrics import silhouette_score`
   - Use cosine metric (same as HDBSCAN)
2. Calculate Davies-Bouldin Index:
   - `from sklearn.metrics import davies_bouldin_score`
3. Calculate Calinski-Harabasz Index:
   - `from sklearn.metrics import calinski_harabasz_score`

**Step 3: Ranking**
For each metric across all k values (1 = best, N = worst):
1. **Silhouette Score:** Rank by value descending (highest score = rank 1)
2. **Davies-Bouldin Index:** Rank by value ascending (lowest score = rank 1, better)
3. **Calinski-Harabasz Index:** Rank by value descending (highest score = rank 1, better)

**Step 4: Weighted Composite Scoring**
Using admin-configured weights, calculate composite score:
```
composite_score = Σ (weight_i / rank_i)

Example calculation:
- Silhouette: rank 5, weight 0.5 → contribution = 0.5 / 5 = 0.100
- Davies-Bouldin: rank 2, weight 0.3 → contribution = 0.3 / 2 = 0.150
- Calinski-Harabasz: rank 8, weight 0.2 → contribution = 0.2 / 8 = 0.025
- Composite Score = 0.100 + 0.150 + 0.025 = 0.275
```

**Key Design Principle:** Inverse ranking ensures rank 1 (best) contributes highest to score.

**Step 5: K-Value Selection**
- Select k with **highest composite_score** for display on homepage
- Document runner-up k values (±1 composite score) as alternatives
- Store all evaluation data for historical analysis

### 3. Admin Weighted Scoring System

**Admin Configuration (stored in user_preferences table):**

```json
{
  "user_id": "admin-123",
  "role": "admin",
  "clustering_config": {
    "evaluation_enabled": true,
    "auto_select_k": true,
    "k_range": {
      "min": 5,
      "max": 100
    },
    "metric_weights": {
      "silhouette_weight": 0.5,
      "davies_bouldin_weight": 0.3,
      "calinski_harabasz_weight": 0.2
    },
    "quality_score_threshold": 0.6
  }
}
```

**Default Weights (can be customized):**
- Silhouette Score: 0.5 (50%) — Most direct measure of cluster quality
- Davies-Bouldin Index: 0.3 (30%) — Evaluates cluster separation and compactness
- Calinski-Harabasz Index: 0.2 (20%) — Global structure assessment

**Example Weight Customization:**
- Admin prioritizes cohesion: Silhouette 0.7, Davies-Bouldin 0.2, Calinski-Harabasz 0.1
- Admin prioritizes separation: Davies-Bouldin 0.6, Silhouette 0.3, Calinski-Harabasz 0.1
- Admin balanced approach (default): 0.5, 0.3, 0.2

### 4. Evaluation Output

**Stored in DynamoDB (new `clustering_evaluation` table):**

```
Partition Key: evaluation_id (String, e.g., "eval-2026-05-28-18-00")
Sort Key: None

Attributes:
- evaluation_id (String, PK)
  └─ Format: "eval-{YYYY-MM-DD}-{HH}-{MM}"
- run_timestamp (Number, unix timestamp)
  └─ When evaluation started
- evaluation_type (String)
  └─ "scheduled" (automatic) or "manual" (admin-triggered)
- total_articles_evaluated (Number)
  └─ Articles used in this evaluation
- evaluation_results (List<Object>)
  └─ See structure below
- selected_k_value (Number)
  └─ k with highest weighted_composite_score
- best_composite_score (Number, 0-1)
  └─ Highest weighted score achieved
- admin_weights (Object)
  └─ Weights used for this evaluation
- quality_threshold_met (Boolean)
  └─ true if best_composite_score >= quality_score_threshold
- completed_at (Number, unix timestamp)
- metrics_summary (Object)
  └─ Statistical summary of all metrics

Evaluation Results Array (each k value):
[
  {
    "k_value": 5,
    "silhouette_score": 0.42,
    "davies_bouldin_index": 1.8,
    "calinski_harabasz_index": 285.3,
    "silhouette_rank": 25,
    "davies_bouldin_rank": 8,
    "calinski_harabasz_rank": 42,
    "weighted_composite_score": 0.285,
    "num_clusters_formed": 5,
    "avg_cluster_size": 18.4,
    "noise_percentage": 3.2,
    "evaluation_time_ms": 234
  },
  {
    "k_value": 6,
    "silhouette_score": 0.51,
    "davies_bouldin_index": 1.6,
    "calinski_harabasz_index": 312.8,
    "silhouette_rank": 8,
    "davies_bouldin_rank": 5,
    "calinski_harabasz_rank": 18,
    "weighted_composite_score": 0.542,  # BEST
    "num_clusters_formed": 6,
    "avg_cluster_size": 16.8,
    "noise_percentage": 2.1,
    "evaluation_time_ms": 241
  },
  ...
  {
    "k_value": 100,
    "silhouette_score": 0.15,
    "davies_bouldin_index": 4.2,
    "calinski_harabasz_index": 98.5,
    "silhouette_rank": 96,
    "davies_bouldin_rank": 96,
    "calinski_harabasz_rank": 96,
    "weighted_composite_score": 0.008,  # WORST
    "num_clusters_formed": 100,
    "avg_cluster_size": 0.92,
    "noise_percentage": 45.8,
    "evaluation_time_ms": 512
  }
]

Metrics Summary:
{
  "silhouette_score": {
    "min": 0.08,
    "max": 0.51,
    "mean": 0.32,
    "std_dev": 0.11
  },
  "davies_bouldin_index": {
    "min": 1.2,
    "max": 4.8,
    "mean": 2.1,
    "std_dev": 0.9
  },
  "calinski_harabasz_index": {
    "min": 85.2,
    "max": 425.6,
    "mean": 248.3,
    "std_dev": 92.1
  },
  "composite_score": {
    "min": 0.008,
    "max": 0.542,
    "mean": 0.185,
    "std_dev": 0.131
  }
}
```

**Visualization (3-Metric Plot):**
- **X-axis:** k values (5 to 100)
- **Y-axis 1 (left):** Silhouette Score (-1 to 1)
- **Y-axis 2 (right):** Davies-Bouldin Index (0 to max observed)
- **Y-axis 3 (right):** Calinski-Harabasz Index (0 to max observed)
- **3 Lines:** Each metric's evolution across k values
- **Vertical Line:** Selected k value (highest composite score)
- **Shaded Region:** "Good" range for each metric (optional)
- **Annotations:** Mark peak scores, optimal regions

### 5. Admin Settings API

**Endpoint: GET /v1/admin/clustering/evaluation**
Retrieve latest evaluation results.

```
GET /v1/admin/clustering/evaluation

Response:
{
  "latest_evaluation_id": "eval-2026-05-28-18-00",
  "selected_k_value": 6,
  "best_composite_score": 0.542,
  "evaluation_results": [...],
  "admin_weights": {
    "silhouette_weight": 0.5,
    "davies_bouldin_weight": 0.3,
    "calinski_harabasz_weight": 0.2
  },
  "quality_threshold_met": true,
  "run_timestamp": 1717008000,
  "completed_at": 1717008342
}
```

**Endpoint: PUT /v1/admin/clustering/weights**
Update metric weights and trigger re-evaluation.

```
PUT /v1/admin/clustering/weights

Request:
{
  "silhouette_weight": 0.6,
  "davies_bouldin_weight": 0.2,
  "calinski_harabasz_weight": 0.2,
  "trigger_re_evaluation": true
}

Response:
{
  "status": "weights_updated",
  "new_weights": {
    "silhouette_weight": 0.6,
    "davies_bouldin_weight": 0.2,
    "calinski_harabasz_weight": 0.2
  },
  "evaluation_task_id": "eval-task-abc123",
  "estimated_completion_time": 45
}
```

**Endpoint: POST /v1/admin/clustering/evaluate**
Manually trigger evaluation run (overrides scheduled evaluation).

```
POST /v1/admin/clustering/evaluate

Request:
{
  "k_min": 5,
  "k_max": 100,
  "use_current_articles": true,
  "force_embedding_refresh": false
}

Response:
{
  "evaluation_id": "eval-2026-05-28-19-30",
  "status": "started",
  "estimated_duration_seconds": 120,
  "callback_endpoint": "/v1/admin/clustering/evaluation/{evaluation_id}"
}
```

**Endpoint: GET /v1/admin/clustering/evaluation/{evaluation_id}**
Retrieve specific evaluation result by ID.

```
GET /v1/admin/clustering/evaluation/eval-2026-05-28-18-00

Response:
{
  "evaluation_id": "eval-2026-05-28-18-00",
  "status": "completed",
  "selected_k_value": 6,
  "evaluation_results": [...],
  ...
}
```

### 6. Scheduled Evaluation

**Automatic Evaluation Schedule:**
- Run after each clustering task (6am & 6pm UTC)
- Use latest articles for evaluation
- Store results in `clustering_evaluation` table
- Update homepage clusters if new k is selected

**Celery Task for Evaluation:**
```python
@celery_app.task(
    name='tasks.evaluate_clustering_quality',
    bind=True,
    max_retries=2
)
def evaluate_clustering_quality(self, articles=None):
    """
    Evaluate clustering quality across k values.
    Triggered after cluster_articles task completes.
    
    Inputs:
    - articles: list of article embeddings (from previous clustering run)
    
    Outputs:
    - Evaluation results stored in clustering_evaluation table
    - Updates selected_k_value in homepage config
    - Generates visualization plot
    """
    pass
```

### 7. Implementation Steps (Phase 3 Addition)

**Duration: 3-4 days**

1. **Metric Implementation** (0.5 days)
   - Implement Silhouette Score calculation
   - Implement Davies-Bouldin Index calculation
   - Implement Calinski-Harabasz Index calculation
   - Add unit tests for each metric

2. **Evaluation Pipeline** (1 day)
   - Create parameter sweep loop (k from 5 to 100)
   - Implement ranking system (rank each metric)
   - Implement weighted composite scoring
   - Handle edge cases (empty clusters, all noise)

3. **DynamoDB Storage** (0.5 days)
   - Create `clustering_evaluation` table schema
   - Implement evaluation result persistence
   - Add indexing for quick retrieval

4. **Admin API Endpoints** (1 day)
   - GET /v1/admin/clustering/evaluation
   - PUT /v1/admin/clustering/weights
   - POST /v1/admin/clustering/evaluate
   - GET /v1/admin/clustering/evaluation/{evaluation_id}

5. **Visualization** (1 day)
   - Generate 3-metric plot using matplotlib/plotly
   - Store plot as image in S3
   - Display in admin dashboard

6. **Integration & Testing** (0.5 days)
   - Integrate evaluation into clustering pipeline
   - End-to-end testing with real articles
   - Performance optimization (evaluation should complete in <2 minutes)

### 8. Success Criteria

- All 3 metrics calculated correctly for each k value
- Ranking system produces inverse ranking (rank 1 = best)
- Weighted composite score formula accurate
- K-value selection chooses highest composite score
- Admin can adjust weights and re-run evaluation
- Evaluation completes in < 2 minutes for 96 k values
- Visualization clearly shows metric trade-offs
- Results persisted and retrievable via API

---

## System Architecture

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Daily Celery Schedule (6am & 6pm)                           │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Fetch Recent Articles from DynamoDB (last 7 days)        │
│    - articles table                                          │
│    - Filter: created_at > now - 7 days                       │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Retrieve/Generate Embeddings                             │
│    - Check cached embeddings in article_embeddings table     │
│    - Generate missing via OpenAI text-embedding-3-small      │
│    - Batch API calls for efficiency                          │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Run HDBSCAN Clustering                                   │
│    - Input: N x 1536 embedding matrix                        │
│    - Output: cluster_id for each article                     │
│    - Mark noise articles as cluster_id = -1                  │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Generate Cluster Metadata                                │
│    - Extract top 5 keywords per cluster (TF-IDF)             │
│    - Compute centroid embeddings                             │
│    - Generate auto-labels via Claude Haiku (Bedrock)         │
│    - Calculate cluster size & diversity metrics              │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Store Results in DynamoDB                                │
│    - article_clusters table (article assignments)            │
│    - cluster_metadata table (labels, keywords, stats)        │
│    - Set TTL = now + 7 days (refresh cycle)                  │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Serve via FastAPI /v1/clusters Endpoint                  │
│    - List all clusters with metadata                         │
│    - Retrieve articles in a specific cluster                 │
│    - Support filtering & pagination                          │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Task |
|-----------|------|
| **Celery Task** | Orchestrate clustering pipeline, error handling, retries |
| **Embedding Service** | Batch embed articles via OpenAI text-embedding-3-small (1536 dims) |
| **Clustering Engine** | HDBSCAN algorithm, parameter tuning |
| **Metadata Generator** | Labels & descriptions (via Claude Haiku via Bedrock), keywords, diversity metrics |
| **DynamoDB Storage** | Persistence, TTL management, indexing |
| **FastAPI Endpoint** | Query clusters, cache responses (30 min), pagination |
| **Frontend Components** | Topics tab, cluster cards, liquid glass design |

---

## DynamoDB Schema

### Table 1: tech-news-article_clusters
```
Partition Key: cluster_id (String)
Sort Key: article_id (String)
GSI: article_id -> cluster_id (for reverse lookups)

Attributes:
- cluster_id (String, PK)
- article_id (String, SK)
- assigned_at (Number, unix timestamp)
- confidence_score (Number, 0-1)
  └─ Distance from article centroid (1 - normalized_distance)
- ttl (Number, unix timestamp)
  └─ Set to now + 7 days for automatic cleanup
```

### Table 2: tech-news-cluster_metadata
```
Partition Key: cluster_id (String)
No Sort Key

Attributes:
- cluster_id (String, PK)
- label (String) [auto-generated]
  └─ Example: "AI Breakthroughs & LLM Development"
- keywords (List<String>)
  └─ Top 5 keywords by TF-IDF: ["AI", "LLM", "GPT-5", "transformer", "training"]
- description (String) [auto-generated]
  └─ 1-2 sentence summary from Claude Haiku
- article_count (Number)
  └─ Total articles in cluster
- size_category (String)
  └─ "SMALL" (5-10), "MEDIUM" (11-50), "LARGE" (51+)
- diversity_score (Number, 0-1)
  └─ Average pairwise cosine distance within cluster
- centroid_embedding (List<Number>)
  └─ Avg of all article embeddings in cluster (1536 dims)
- top_articles (List<Object>)
  └─ [{ article_id, title, engagement_score }, ...]
  └─ Up to 10 articles, sorted by engagement_score desc
- created_at (Number, unix timestamp)
- updated_at (Number, unix timestamp)
- ttl (Number, unix timestamp)
  └─ Set to now + 7 days
```

### Table 3: tech-news-article_embeddings (existing, extend if needed)
```
Partition Key: article_id (String)
Attributes:
- article_id (String, PK)
- embedding (List<Number>)
  └─ 1536-dimensional vector
- embedding_model (String)
  └─ "text-embedding-3-small" (OpenAI)
- labeling_model (String)
  └─ "us.anthropic.claude-haiku-4-5-20251001-v1:0" (Bedrock, used for cluster label generation)
- generated_at (Number)
- ttl (Number)
```

### Table 4: tech-news-clustering_evaluation (new)
```
Partition Key: evaluation_id (String)
No Sort Key

Attributes:
- evaluation_id (String, PK)
  └─ Format: "eval-{YYYY-MM-DD}-{HH}-{MM}"
- run_timestamp (Number, unix timestamp)
  └─ When evaluation started
- evaluation_type (String)
  └─ "scheduled" or "manual"
- total_articles_evaluated (Number)
  └─ Count of articles used in evaluation
- evaluation_results (List<Object>)
  └─ Array of metric results for each k value (see Clustering Quality Evaluation section)
- selected_k_value (Number)
  └─ k with highest weighted_composite_score
- best_composite_score (Number, 0-1)
  └─ Highest weighted score achieved
- admin_weights (Object)
  └─ Weights used: {silhouette_weight, davies_bouldin_weight, calinski_harabasz_weight}
- quality_threshold_met (Boolean)
  └─ true if best_composite_score >= configured threshold
- metrics_summary (Object)
  └─ Statistical summary: min, max, mean, std_dev for each metric
- visualization_plot_url (String)
  └─ S3 URL to 3-metric plot image
- completed_at (Number, unix timestamp)
- ttl (Number, unix timestamp)
  └─ Set to now + 30 days (longer retention for evaluation history)
```

---

## Celery Scheduling

### Task Definition
```python
# backend/app/workers/tasks/clustering_tasks.py

@celery_app.task(
    name='tasks.cluster_articles',
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 min backoff
)
def cluster_articles(self):
    """
    Daily clustering job: 6am & 6pm UTC
    - Fetch articles from last 7 days
    - Generate/retrieve embeddings
    - Run HDBSCAN
    - Store results in DynamoDB
    """
    try:
        # Implementation details below
        pass
    except Exception as exc:
        self.retry(exc=exc)
```

### Cron Schedule
```python
# backend/app/workers/celery_app.py

from celery.schedules import crontab

app.conf.beat_schedule = {
    # ... existing tasks ...
    'cluster-articles-morning': {
        'task': 'tasks.cluster_articles',
        'schedule': crontab(hour=6, minute=0),  # 6:00 AM UTC
    },
    'cluster-articles-evening': {
        'task': 'tasks.cluster_articles',
        'schedule': crontab(hour=18, minute=0),  # 6:00 PM UTC
    },
}
```

### Error Handling
- Automatic retry with exponential backoff (300s, 600s, 1200s)
- Max 3 retries before failure
- Log failures to CloudWatch for monitoring
- Alert on repeated failures (SNS notification)

### Configuration & Setup

**Step 1: Add to Celery Beat Schedule**
```python
# backend/app/workers/celery_app.py

from celery.schedules import crontab
from .tasks.clustering_tasks import cluster_articles

# Add to app.conf.beat_schedule dict:
app.conf.beat_schedule = {
    # ... existing tasks ...
    'cluster-articles-morning': {
        'task': 'tasks.cluster_articles',
        'schedule': crontab(hour=6, minute=0),  # 6:00 AM UTC
    },
    'cluster-articles-evening': {
        'task': 'tasks.cluster_articles',
        'schedule': crontab(hour=18, minute=0),  # 6:00 PM UTC
    },
}
```

**Step 2: Environment Variables**
Add to `.env` and `config.py`:
```
# OpenAI Embeddings Configuration
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMS=1536

# Clustering Configuration
CLUSTERING_MIN_CLUSTER_SIZE=5
CLUSTERING_MIN_SAMPLES=3
CLUSTERING_BATCH_SIZE=100
CLUSTERING_TASK_TIMEOUT=600

# Clustering Evaluation Configuration
CLUSTERING_EVALUATION_ENABLED=true
CLUSTERING_K_MIN=5
CLUSTERING_K_MAX=100
CLUSTERING_EVALUATION_TIMEOUT=300  # seconds for evaluation pipeline
CLUSTERING_QUALITY_THRESHOLD=0.6

# Default Metric Weights (can be overridden by admin)
CLUSTERING_SILHOUETTE_WEIGHT=0.5
CLUSTERING_DAVIES_BOULDIN_WEIGHT=0.3
CLUSTERING_CALINSKI_HARABASZ_WEIGHT=0.2

# DynamoDB Clustering Tables
DYNAMODB_ARTICLE_CLUSTERS_TABLE=tech-news-article_clusters
DYNAMODB_CLUSTER_METADATA_TABLE=tech-news-cluster_metadata
DYNAMODB_CLUSTERING_EVALUATION_TABLE=tech-news-clustering_evaluation
CLUSTERING_TTL_DAYS=7
CLUSTERING_EVALUATION_TTL_DAYS=30
```

Update `backend/app/config.py`:
```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Clustering
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dims: int = 1536
    clustering_min_cluster_size: int = 5
    clustering_min_samples: int = 3
    clustering_batch_size: int = 100
    clustering_task_timeout: int = 600
    
    # Clustering Evaluation
    clustering_evaluation_enabled: bool = True
    clustering_k_min: int = 5
    clustering_k_max: int = 100
    clustering_evaluation_timeout: int = 300
    clustering_quality_threshold: float = 0.6
    clustering_silhouette_weight: float = 0.5
    clustering_davies_bouldin_weight: float = 0.3
    clustering_calinski_harabasz_weight: float = 0.2
    
    # DynamoDB Tables
    dynamodb_article_clusters_table: str = "tech-news-article_clusters"
    dynamodb_cluster_metadata_table: str = "tech-news-cluster_metadata"
    dynamodb_clustering_evaluation_table: str = "tech-news-clustering_evaluation"
    clustering_ttl_days: int = 7
    clustering_evaluation_ttl_days: int = 30
```

---

## API Endpoints

### 1. GET /v1/clusters
List all active clusters with metadata.

**Request:**
```
GET /v1/clusters?page=1&page_size=10&sort_by=size
```

**Query Parameters:**
- `page` (int, default=1)
- `page_size` (int, default=10, max=100)
- `sort_by` (string): "size", "recency", "diversity" (default="size")

**Response:**
```json
{
  "clusters": [
    {
      "id": "cluster-20260528-001",
      "label": "AI Breakthroughs & LLM Development",
      "description": "Recent advances in large language models and AI capabilities",
      "keywords": ["AI", "LLM", "GPT-5", "transformer", "training"],
      "article_count": 23,
      "size_category": "MEDIUM",
      "diversity_score": 0.42,
      "top_articles": [
        {
          "id": "article-xyz",
          "title": "GPT-5 Training Complete...",
          "engagement_score": 4.2
        }
      ],
      "created_at": 1717008000,
      "updated_at": 1717008000
    }
  ],
  "pagination": {
    "total_count": 45,
    "page": 1,
    "page_size": 10,
    "total_pages": 5
  }
}
```

### 2. GET /v1/clusters/{cluster_id}
Retrieve detailed cluster information with full article list.

**Request:**
```
GET /v1/clusters/cluster-20260528-001?page=1&page_size=20
```

**Response:**
```json
{
  "id": "cluster-20260528-001",
  "label": "AI Breakthroughs & LLM Development",
  "description": "...",
  "keywords": ["AI", "LLM", "GPT-5", "transformer", "training"],
  "article_count": 23,
  "size_category": "MEDIUM",
  "diversity_score": 0.42,
  "articles": [
    {
      "id": "article-xyz",
      "title": "GPT-5 Training Complete...",
      "summary": "...",
      "source": "techcrunch.com",
      "published_at": 1717005600,
      "engagement_score": 4.2,
      "confidence_score": 0.89,
      "url": "https://..."
    }
  ],
  "pagination": {
    "total_count": 23,
    "page": 1,
    "page_size": 20,
    "total_pages": 2
  }
}
```

### 3. GET /v1/clusters/trending
Return top trending clusters (sorted by engagement, updated hourly).

**Request:**
```
GET /v1/clusters/trending?limit=10
```

**Response:**
```json
{
  "trending_clusters": [
    {
      "id": "cluster-20260528-001",
      "label": "...",
      "trending_rank": 1,
      "momentum_score": 0.89,
      "article_count": 23,
      "engagement_trend": "UP",
      "articles_added_last_hour": 3
    }
  ]
}
```

**Note:** Cache responses for 30 minutes (ETag-based conditional requests supported).

---

## Frontend Components

### Topics Section Layout

**Location:** New tab in navbar + dedicated page `/topics`

**Components:**

#### 1. Topics Navigation Tab
```
Navbar: [Home] [Explore] [Topics] [Search] [Profile]
```

#### 2. Topics Page Structure
```
┌─────────────────────────────────────────────────────────┐
│ Topics                                    [Trending] [New] │
├─────────────────────────────────────────────────────────┤
│ [Filter: Size ▼] [Sort: Latest ▼]   [Search topics...]  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│ │ AI & LLMs    │  │ Climate      │  │ Crypto       │    │
│ │ 23 articles  │  │ 18 articles  │  │ 12 articles  │    │
│ │ #AI #LLM    │  │ #Climate     │  │ #Crypto      │    │
│ │ → 4.2★       │  │ → 3.8★       │  │ → 2.1★       │    │
│ └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                           │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│ │ ...          │  │ ...          │  │ ...          │    │
│ └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────┘
```

#### 3. Cluster Card Component (Liquid Glass Design)
```tsx
<ClusterCard>
  <CardHeader>
    <Title>AI Breakthroughs & LLM Development</Title>
    <Description>Recent advances in large language models...</Description>
  </CardHeader>
  
  <CardContent>
    <Keywords>
      {keywords.map(kw => <Badge>{kw}</Badge>)}
    </Keywords>
    
    <Stats>
      <Stat label="Articles" value={23} />
      <Stat label="Diversity" value="42%" />
    </Stats>
    
    <TopArticles>
      {topArticles.map(article => (
        <ArticleMini key={article.id}>
          <Title>{article.title}</Title>
          <Engagement>★ {article.engagement_score}</Engagement>
        </ArticleMini>
      ))}
    </TopArticles>
  </CardContent>
  
  <CardFooter>
    <Button>View All {article_count} Articles →</Button>
  </CardFooter>
</ClusterCard>
```

#### 4. Liquid Glass Styling
```css
.cluster-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  
  /* Hover effect */
  transition: all 0.3s ease;
  
  &:hover {
    background: rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.3);
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
  }
}
```

#### 5. Cluster Detail View
```
┌─────────────────────────────────────────────────────────┐
│ ← Back to Topics                                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│ AI Breakthroughs & LLM Development                      │
│ Recent advances in large language models and AI         │
│                                                           │
│ Keywords: AI, LLM, GPT-5, transformer, training         │
│ 23 articles | Diversity: 42% | Updated: 2h ago         │
│                                                           │
├─────────────────────────────────────────────────────────┤
│                                                           │
│ [Filter: Source ▼] [Sort: Latest ▼]                    │
│                                                           │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Title: GPT-5 Training Complete...                    │ │
│ │ Source: TechCrunch | 2h ago | ★ 4.2                 │ │
│ │ Summary: Leading AI lab announces...                 │ │
│ │ Confidence: 89%                                       │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                           │
│ [... pagination ...]                                     │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Phase 1: Backend Infrastructure (Weeks 1-2)

**Required Dependencies:** Add to `requirements.txt`:
```
hdbscan>=0.8.30
scikit-learn>=1.3.0
```

- [ ] **Database Schema**
  - [ ] Create `article_clusters` table in DynamoDB
  - [ ] Create `cluster_metadata` table in DynamoDB
  - [ ] Create GSI on `article_clusters` for article_id lookups
  - [ ] Enable TTL on both tables (7-day expiration)

- [ ] **Embedding Service Enhancement**
  - [ ] Batch embedding API using OpenAI text-embedding-3-small (1536 dims)
  - [ ] Caching layer for embeddings (check before calling OpenAI API)
  - [ ] Handle embedding failures gracefully (retry with exponential backoff)

- [ ] **HDBSCAN Implementation**
  - [ ] Install hdbscan & scikit-learn (added to requirements.txt)
  - [ ] Create `clustering_engine.py` module
  - [ ] Implement HDBSCAN clustering with parameter tuning
  - [ ] Handle edge cases (< 5 articles, all noise, empty clusters)
  - [ ] Unit tests for clustering logic

### Phase 2: Metadata Generation (Weeks 2-3)

- [ ] **Cluster Labeling**
  - [ ] TF-IDF keyword extraction per cluster
  - [ ] Claude Haiku integration (via Bedrock) for auto-label generation
  - [ ] Diversity score calculation (pairwise cosine distances)
  - [ ] Centroid embedding computation

- [ ] **Celery Task**
  - [ ] Create `backend/app/workers/tasks/clustering_tasks.py`
  - [ ] Register task in Celery app (add to task discovery)
  - [ ] Implement main clustering orchestration task
  - [ ] Add to Celery Beat schedule (see Configuration section below)
  - [ ] Error handling & retries (max 3 with exponential backoff)
  - [ ] Logging & monitoring hooks for CloudWatch

- [ ] **Data Persistence**
  - [ ] Write to `article_clusters` table
  - [ ] Write to `cluster_metadata` table
  - [ ] Set TTL fields correctly
  - [ ] Handle concurrent writes (idempotent updates)

### Phase 3: Clustering Quality Evaluation (Weeks 3-4)

- [ ] **Metric Calculation Functions**
  - [ ] Implement Silhouette Score calculation (sklearn.metrics.silhouette_score)
  - [ ] Implement Davies-Bouldin Index calculation (sklearn.metrics.davies_bouldin_score)
  - [ ] Implement Calinski-Harabasz Index calculation (sklearn.metrics.calinski_harabasz_score)
  - [ ] Unit tests for metric calculations with sample data

- [ ] **Evaluation Pipeline**
  - [ ] Parameter sweep loop (k from min to max)
  - [ ] Ranking system: rank each metric across all k values
  - [ ] Weighted composite score calculation
  - [ ] K-value selection based on highest composite score
  - [ ] Handle edge cases (< 5 articles, all noise, empty clusters)

- [ ] **DynamoDB Storage**
  - [ ] Create `clustering_evaluation` table schema
  - [ ] Implement evaluation result persistence
  - [ ] Add GSI for timestamp-based queries (for evaluation history)
  - [ ] Set TTL for automatic cleanup (30 days)

- [ ] **Admin Configuration**
  - [ ] Store metric weights in user_preferences table
  - [ ] Implement weight update logic
  - [ ] Validate weight values (sum to ~1.0, each 0-1)

- [ ] **Visualization**
  - [ ] Generate 3-metric plot (matplotlib or plotly)
  - [ ] X-axis: k values, Y-axes: metric scores
  - [ ] Mark selected k value with vertical line
  - [ ] Store plot as image in S3
  - [ ] Generate plot URL for API response

- [ ] **Integration Testing**
  - [ ] Test evaluation with real article embeddings
  - [ ] Test weight updates and re-ranking
  - [ ] Performance: evaluation should complete in < 2 minutes
  - [ ] Test API endpoints with sample data

### Phase 4: API Endpoints (Weeks 4-5)

- [ ] **FastAPI Router**
  - [ ] Create `backend/app/api/v1/clusters.py`
  - [ ] Register router in `backend/app/main.py`: `app.include_router(clusters_router, prefix="/v1")`
  - [ ] Implement `GET /v1/clusters` - list all clusters with pagination
  - [ ] Implement `GET /v1/clusters/{cluster_id}` - cluster details + articles
  - [ ] Implement `GET /v1/clusters/trending` - trending clusters (hourly cache)

- [ ] **Response Validation**
  - [ ] Pydantic schemas for request/response payloads (models in `backend/app/schemas/clusters.py`)
  - [ ] Input validation (page, page_size bounds)
  - [ ] Pagination logic (offset/limit or cursor-based)

- [ ] **Caching**
  - [ ] 30-minute cache on cluster list responses
  - [ ] ETag support for conditional requests
  - [ ] Cache invalidation on task completion

- [ ] **Testing**
  - [ ] Unit tests for each endpoint
  - [ ] Integration tests with mock DynamoDB
  - [ ] Performance tests (load 1000+ clusters)

### Phase 5: Frontend Components (Weeks 5-6)

- [ ] **Topics Navigation**
  - [ ] Add "Topics" tab to navbar
  - [ ] Create `/topics` route

- [ ] **Topics Page**
  - [ ] ClusterCard component with liquid glass styling
  - [ ] Cluster grid layout (responsive, 2-3 cols)
  - [ ] Filter by size, sort by trending/latest/diversity
  - [ ] Search topics feature

- [ ] **Cluster Detail View**
  - [ ] Display cluster metadata (label, keywords, stats)
  - [ ] Article list with pagination
  - [ ] Filter by source, engagement, date range
  - [ ] Back navigation to topics list

- [ ] **Design System**
  - [ ] Liquid glass CSS utilities (backdrop-filter, opacity)
  - [ ] Apple Design Language (spacing, typography, colors)
  - [ ] Dark mode support
  - [ ] Responsive design for mobile

- [ ] **Testing**
  - [ ] Component unit tests
  - [ ] Integration tests (API calls, pagination)
  - [ ] E2E tests (create cluster, view, navigate)

### Phase 6: Integration & Polish (Weeks 6-7)

- [ ] **End-to-End Testing**
  - [ ] Celery task runs and completes successfully
  - [ ] API endpoints return correct data
  - [ ] Frontend displays clusters properly
  - [ ] Pagination works across all views

- [ ] **Performance Optimization**
  - [ ] Profile clustering task (should complete in <5 min)
  - [ ] Optimize DynamoDB queries (use GSI efficiently)
  - [ ] Monitor API response times (< 500ms p95)

- [ ] **Monitoring & Observability**
  - [ ] CloudWatch logs for Celery tasks
  - [ ] X-Ray tracing for API calls
  - [ ] Alarms for task failures
  - [ ] Dashboard for cluster stats

- [ ] **Documentation**
  - [ ] API documentation (Swagger/OpenAPI)
  - [ ] Database schema diagrams
  - [ ] Deployment guide (Terraform)
  - [ ] Troubleshooting guide

- [ ] **Deployment**
  - [ ] Deploy to staging environment
  - [ ] Smoke tests in staging
  - [ ] Deploy to production
  - [ ] Monitor for 48 hours (task execution, API health)

---

## Success Metrics

### Performance KPIs
| Metric | Target | Monitoring |
|--------|--------|------------|
| Clustering Task Duration | < 5 minutes | CloudWatch logs |
| API Response Time (p95) | < 500ms | X-Ray traces |
| Cluster Stability | > 80% articles in same cluster across runs | Nightly comparison job |
| Cache Hit Rate | > 70% | CloudWatch metrics |

### Quality KPIs
| Metric | Target | Measurement |
|--------|--------|------------|
| Avg Cluster Size | 5-50 articles | Count in metadata |
| Diversity Score | 0.3-0.7 | Calculate per cluster |
| Auto-Label Accuracy | > 85% (manual review) | Sample 20 clusters, human evaluation |
| Article Assignment Confidence | > 0.7 average | Review confidence_score distribution |

### Clustering Evaluation KPIs
| Metric | Target | Measurement |
|--------|--------|------------|
| Metric Accuracy | 100% | All 3 metrics calculated correctly |
| K-Value Selection | Optimal | Selected k has highest composite score |
| Admin Weight Control | Functional | Weight changes update scores correctly |
| Evaluation Duration | < 2 minutes | End-to-end for 96 k values (5-100) |
| Visualization Clarity | High | 3-metric plot shows trade-offs clearly |
| Quality Threshold Met | > 60% | Best composite score exceeds threshold |

### User Engagement KPIs
| Metric | Target | Measurement |
|--------|--------|------------|
| Topics Tab Click Rate | > 5% of users | Frontend analytics |
| Cluster View Duration | > 30s average | User session tracking |
| Cluster Click-through | > 20% (cluster → articles) | Frontend analytics |
| User Sessions with Clusters | > 10% of daily active users | Session analytics |

---

## Deployment

### Infrastructure (Terraform)

**DynamoDB Tables:**
```hcl
# infra/terraform/dynamodb.tf (add to existing file)

locals {
  name_prefix = "${var.project_name}-${var.environment}-"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Service     = "clustering"
    ManagedBy   = "Terraform"
  }
}

resource "aws_dynamodb_table" "article_clusters" {
  name           = "${local.name_prefix}article_clusters"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "cluster_id"
  range_key      = "article_id"
  
  attribute {
    name = "cluster_id"
    type = "S"
  }
  
  attribute {
    name = "article_id"
    type = "S"
  }
  
  global_secondary_index {
    name            = "article_id-index"
    hash_key        = "article_id"
    projection_type = "ALL"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  point_in_time_recovery {
    enabled = true
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}article_clusters"
  })
}

resource "aws_dynamodb_table" "cluster_metadata" {
  name           = "${local.name_prefix}cluster_metadata"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "cluster_id"
  
  attribute {
    name = "cluster_id"
    type = "S"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  point_in_time_recovery {
    enabled = true
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}cluster_metadata"
  })
}

resource "aws_dynamodb_table" "clustering_evaluation" {
  name           = "${local.name_prefix}clustering_evaluation"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "evaluation_id"
  
  attribute {
    name = "evaluation_id"
    type = "S"
  }
  
  attribute {
    name = "run_timestamp"
    type = "N"
  }
  
  global_secondary_index {
    name            = "run_timestamp-index"
    hash_key        = "run_timestamp"
    projection_type = "ALL"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  point_in_time_recovery {
    enabled = true
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}clustering_evaluation"
  })
}
```

**IAM Policies for ECS Task:**
```hcl
# infra/terraform/iam.tf

resource "aws_iam_role_policy" "clustering_task_policy" {
  name = "${local.name_prefix}clustering-task-policy"
  role = aws_iam_role.ecs_task_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:UpdateItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:BatchGetItem"
        ]
        Resource = [
          aws_dynamodb_table.article_clusters.arn,
          "${aws_dynamodb_table.article_clusters.arn}/index/*",
          aws_dynamodb_table.cluster_metadata.arn,
          "${aws_dynamodb_table.cluster_metadata.arn}/index/*",
          aws_dynamodb_table.clustering_evaluation.arn,
          "${aws_dynamodb_table.clustering_evaluation.arn}/index/*"
        ]
      },
      {
        Sid    = "BedrockAccess"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-haiku-4-5-*"
      }
    ]
  })
}
```

**CloudWatch Monitoring:**
```hcl
# infra/terraform/cloudwatch.tf

resource "aws_cloudwatch_log_group" "clustering_tasks" {
  name              = "/aws/ecs/${local.name_prefix}clustering-tasks"
  retention_in_days = 30
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}clustering-task-logs"
  })
}

resource "aws_cloudwatch_metric_alarm" "clustering_task_failure" {
  alarm_name          = "${local.name_prefix}clustering-task-failure"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "TasksFailed"
  namespace           = "Celery/Clustering"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Alert when clustering task fails"
  alarm_actions       = [var.sns_alert_topic_arn]
  
  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "clustering_task_duration" {
  alarm_name          = "${local.name_prefix}clustering-task-duration-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "TaskDuration"
  namespace           = "Celery/Clustering"
  period              = "300"
  statistic           = "Average"
  threshold           = "300"  # 5 minutes in seconds
  alarm_description   = "Alert when clustering task exceeds 5 minutes"
  alarm_actions       = [var.sns_alert_topic_arn]
  
  tags = local.common_tags
}
```

**ECS Task Definition for Clustering:**
```hcl
# infra/terraform/ecs.tf (add to clustering section)

resource "aws_ecs_task_definition" "clustering_worker" {
  family                   = "${local.name_prefix}clustering-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  
  container_definitions = jsonencode([{
    name      = "clustering-worker"
    image     = "${var.ecr_repository_url}:latest"
    essential = true
    
    environment = [
      {
        name  = "CELERY_BROKER_URL"
        value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/0"
      },
      {
        name  = "CELERY_RESULT_BACKEND"
        value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/1"
      },
      {
        name  = "OPENAI_EMBEDDING_MODEL"
        value = "text-embedding-3-small"
      },
      {
        name  = "CLUSTERING_MIN_CLUSTER_SIZE"
        value = "5"
      }
    ]
    
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.clustering_tasks.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
  
  tags = local.common_tags
}
```

### Deployment Steps
1. **Add Dependencies:** Update `requirements.txt` with hdbscan and scikit-learn
2. **Apply Terraform:** `terraform apply` to create DynamoDB tables (article_clusters, cluster_metadata, clustering_evaluation), IAM policies, CloudWatch resources
3. **Verify Terraform:** Check DynamoDB console for all three tables, IAM role policy attached, GSI created
4. **Configure Environment:** Add clustering environment variables to `.env` and `config.py` (both clustering and evaluation config)
5. **Implement Evaluation:** Create evaluation module with metric calculation, ranking, and scoring
6. **Add Celery Schedule:** Update `backend/app/workers/celery_app.py` with beat_schedule entries for both clustering and evaluation
7. **Create API Router:** Implement `backend/app/api/v1/clusters.py` with cluster and evaluation endpoints, register in `backend/app/main.py`
8. **Create Celery Tasks:** Implement `backend/app/workers/tasks/clustering_tasks.py` (cluster_articles and evaluate_clustering_quality)
9. **Deploy Backend:** Restart Celery workers and FastAPI server
10. **Deploy Frontend:** Create `/topics` route and implement cluster UI components, add evaluation visualization
11. **Monitor:** Watch CloudWatch logs for first scheduled task execution (6am & 6pm UTC)
12. **Verify:** Call `/v1/clusters` and `/v1/admin/clustering/evaluation` endpoints in production, check response

### Rollback Plan
- If clustering task fails: Disable schedule in Celery Beat, revert code
- If API fails: Temporarily disable `/v1/clusters` route, return empty response
- If data corruption: Restore DynamoDB from backup, re-run clustering task
- Maintain 7-day TTL on all cluster data for automatic cleanup

---

## Model & Service Details

### Embedding Model: OpenAI text-embedding-3-small
- **Provider:** OpenAI
- **Dimensions:** 1536
- **Use:** Article embedding for clustering input
- **Cache:** Stored in `article_embeddings` table with `embedding_model` field set to "text-embedding-3-small"
- **Batching:** Batch up to 100 articles per API call for efficiency

### Labeling Model: Claude Haiku (via Bedrock)
- **Provider:** AWS Bedrock
- **Model:** `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- **Use:** Generate cluster labels and descriptions based on keywords and article content
- **Context:** Uses top 5 keywords and sample articles from each cluster
- **Field in DB:** `labeling_model` in article_embeddings table for clarity

### Clustering Algorithm: HDBSCAN
- **Library:** hdbscan >= 0.8.30
- **Dependencies:** scikit-learn >= 1.3.0
- **Min cluster size:** 5 articles
- **Min samples:** 3 neighbors
- **Metric:** Cosine distance (standard for embedding spaces)
- **Noise handling:** Automatic detection (articles with cluster_id = -1)

## Implementation Notes

- **No Lambda functions needed:** All clustering logic runs in Celery workers (existing infrastructure)
- **Reuses existing services:** DynamoDB, Bedrock API, CloudWatch logging
- **Two-API architecture:** OpenAI for embeddings, Bedrock for labeling (separation of concerns)
- **Backward compatible:** New features don't break existing article/search APIs
- **Scalable:** DynamoDB on-demand billing handles any volume
- **User-friendly:** Topics tab provides intuitive content discovery alternative
- **Monitoring:** CloudWatch logs, metrics, and alarms for task health and performance

