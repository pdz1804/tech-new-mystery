# Implementation Tasks - Clustering & Chatbot Features

**Created:** May 28, 2026  
**Status:** Ready for Sprint Planning  
**Total Estimated Effort:** 240-300 hours (8-10 weeks)

---

## Task Summary Table

| ID | Title | Category | Feature | Priority | Effort | Status |
|----|----|----|----|----|----|---|
| CLU-001 | DynamoDB Schema for Clustering | Infrastructure | Clustering | High | 4h | Not Started |
| CLU-002 | Embedding Service Enhancement | Backend | Clustering | High | 6h | Not Started |
| CLU-003 | HDBSCAN Clustering Engine | Backend | Clustering | High | 8h | Not Started |
| CLU-004 | Celery Task for Clustering | Backend | Clustering | High | 6h | Not Started |
| CLU-005 | Silhouette Score Metric | ML | Clustering | Medium | 4h | Not Started |
| CLU-006 | Davies-Bouldin Index Metric | ML | Clustering | Medium | 4h | Not Started |
| CLU-007 | Calinski-Harabasz Index Metric | ML | Clustering | Medium | 4h | Not Started |
| CLU-008 | Evaluation Pipeline & K-Value Selection | Backend | Clustering | High | 8h | Not Started |
| CLU-009 | Clustering Evaluation DynamoDB | Infrastructure | Clustering | High | 4h | Not Started |
| CLU-010 | Admin Weights Configuration | Backend | Clustering | Medium | 4h | Not Started |
| CLU-011 | Visualization 3-Metric Plot | Backend | Clustering | Medium | 6h | Not Started |
| CLU-012 | Cluster API Endpoints | Backend | Clustering | High | 8h | Not Started |
| CLU-013 | Admin Evaluation Endpoints | Backend | Clustering | Medium | 6h | Not Started |
| CLU-014 | Frontend Topics Page | Frontend | Clustering | High | 12h | Not Started |
| CLU-015 | Cluster Card Component | Frontend | Clustering | Medium | 8h | Not Started |
| CLU-016 | Cluster Detail View | Frontend | Clustering | Medium | 10h | Not Started |
| CLU-017 | Terraform Clustering Infrastructure | Infrastructure | Clustering | High | 8h | Not Started |
| CLU-018 | CloudWatch Monitoring Setup | Workflow | Clustering | Medium | 4h | Not Started |
| CLU-019 | End-to-End Testing Clustering | Workflow | Clustering | Medium | 8h | Not Started |
| CLU-020 | Clustering Documentation | Workflow | Clustering | Low | 4h | Not Started |
| CHT-001 | DynamoDB Tables for Chat | Infrastructure | Chatbot | High | 4h | Not Started |
| CHT-002 | Agent Core Runtime ECS Setup | Infrastructure | Chatbot | High | 8h | Not Started |
| CHT-003 | Agent Core IAM & Security | Infrastructure | Chatbot | High | 4h | Not Started |
| CHT-004 | Agent Core Memory Configuration | Backend | Chatbot | Medium | 4h | Not Started |
| CHT-005 | FastAPI Chat Router | Backend | Chatbot | High | 8h | Not Started |
| CHT-006 | Chat Service CRUD | Backend | Chatbot | High | 6h | Not Started |
| CHT-007 | Agent Core Client (HTTP API) | Backend | Chatbot | High | 8h | Not Started |
| CHT-008 | Semantic Search Tool | Backend | Chatbot | High | 10h | Not Started |
| CHT-009 | Tool Registration & Orchestration | Backend | Chatbot | High | 6h | Not Started |
| CHT-010 | SSE Streaming Implementation | Backend | Chatbot | High | 8h | Not Started |
| CHT-011 | Per-Request Agent Isolation | Backend | Chatbot | High | 6h | Not Started |
| CHT-012 | Chatbot Page Component | Frontend | Chatbot | High | 10h | Not Started |
| CHT-013 | Chat Interface Component | Frontend | Chatbot | High | 12h | Not Started |
| CHT-014 | Session Management UI | Frontend | Chatbot | Medium | 8h | Not Started |
| CHT-015 | SSE Event Listener Hook | Frontend | Chatbot | High | 6h | Not Started |
| CHT-016 | Liquid Glass Styling | Frontend | Chatbot | Medium | 8h | Not Started |
| CHT-017 | Auth & Session Validation | Backend | Chatbot | High | 6h | Not Started |
| CHT-018 | Error Handling & Recovery | Backend | Chatbot | Medium | 6h | Not Started |
| CHT-019 | End-to-End Testing Chatbot | Workflow | Chatbot | Medium | 10h | Not Started |
| CHT-020 | Performance & Load Testing | Workflow | Chatbot | Medium | 8h | Not Started |
| CHT-021 | Chatbot Documentation | Workflow | Chatbot | Low | 4h | Not Started |

---

## Implementation Roadmap

### Week 1-2: Foundation (56 hours)
**Goal:** Core infrastructure and data layer ready

- **Clustering:**
  - CLU-001: DynamoDB Schema (4h)
  - CLU-002: Embedding Service Enhancement (6h)
  
- **Chatbot:**
  - CHT-001: DynamoDB Tables (4h)
  - CHT-002: Agent Core ECS Setup (8h)
  - CHT-003: IAM & Security (4h)

**Blockers:** None  
**Dependencies:** AWS credentials, Terraform setup

---

### Week 2-3: Core Features (68 hours)
**Goal:** Clustering and agent orchestration working

- **Clustering:**
  - CLU-003: HDBSCAN Engine (8h)
  - CLU-004: Celery Task (6h)
  - CLU-005: Silhouette Score (4h)
  - CLU-006: Davies-Bouldin (4h)
  - CLU-007: Calinski-Harabasz (4h)

- **Chatbot:**
  - CHT-004: Agent Core Memory (4h)
  - CHT-005: FastAPI Router (8h)
  - CHT-006: Chat Service (6h)
  - CHT-007: Agent Core Client (8h)
  - CHT-008: Semantic Search Tool (10h)

**Blockers:** CLU-001, CLU-002, CHT-001, CHT-002, CHT-003  
**Dependencies:** Week 1 infrastructure complete

---

### Week 3-4: Integration & APIs (60 hours)
**Goal:** APIs functional, tools integrated, evaluation complete

- **Clustering:**
  - CLU-008: Evaluation Pipeline (8h)
  - CLU-009: Evaluation DynamoDB (4h)
  - CLU-010: Admin Weights (4h)
  - CLU-011: Visualization (6h)
  - CLU-012: Cluster Endpoints (8h)
  - CLU-013: Admin Endpoints (6h)

- **Chatbot:**
  - CHT-009: Tool Registration (6h)
  - CHT-010: SSE Streaming (8h)
  - CHT-011: Per-Request Isolation (6h)
  - CHT-017: Auth & Validation (6h)

**Blockers:** CLU-003, CLU-004, CHT-007, CHT-008

---

### Week 4-5: Frontend (52 hours)
**Goal:** User-facing UI complete and functional

- **Clustering:**
  - CLU-014: Topics Page (12h)
  - CLU-015: Cluster Card (8h)
  - CLU-016: Detail View (10h)

- **Chatbot:**
  - CHT-012: Chatbot Page (10h)
  - CHT-013: Chat Interface (12h)
  - CHT-014: Session Management (8h)
  - CHT-015: SSE Hook (6h)
  - CHT-016: Styling (6h)

**Blockers:** CLU-012, CLU-013, CHT-005, CHT-010

---

### Week 5-6: Testing & Deployment (48 hours)
**Goal:** Production-ready, tested, deployed

- **Clustering:**
  - CLU-017: Terraform Infrastructure (8h)
  - CLU-018: CloudWatch Monitoring (4h)
  - CLU-019: End-to-End Testing (8h)
  - CLU-020: Documentation (4h)

- **Chatbot:**
  - CHT-018: Error Handling (6h)
  - CHT-019: E2E Testing (10h)
  - CHT-020: Load Testing (8h)
  - CHT-021: Documentation (4h)

**Blockers:** All previous tasks

---

## Backend Tasks

### TASK-CLU-001: DynamoDB Schema for Clustering
**Category:** Infrastructure  
**Feature:** Clustering  
**Priority:** High  
**Effort:** 4 hours  
**Complexity:** Low  

**Description:**
Create three DynamoDB tables for clustering: article_clusters (article-to-cluster mapping), cluster_metadata (cluster information and labels), and article_embeddings (cached embeddings). Set up global secondary indexes for reverse lookups and enable TTL for automatic cleanup.

**Implementation Details:**
- Create `tech-news-article_clusters` table with cluster_id PK, article_id SK
- Create GSI: article_id-index for reverse lookups
- Create `tech-news-cluster_metadata` table with cluster_id PK
- Create `tech-news-article_embeddings` table (extend existing if present)
- Enable TTL on article_clusters and cluster_metadata (7-day expiration)
- Enable point-in-time recovery on all tables
- Set billing mode to PAY_PER_REQUEST

**Files to Create/Modify:**
- `infra/terraform/dynamodb.tf` (add clustering tables)
- `backend/app/models/clustering.py` (Pydantic schemas)

**Acceptance Criteria:**
- [ ] All three tables created in DynamoDB
- [ ] GSI created and working (article_id reverse lookup)
- [ ] TTL enabled (7 days)
- [ ] PITR enabled
- [ ] Schemas validated with test data
- [ ] Terraform plan shows correct resources

**Dependencies:**
- None (foundational)

**Testing:**
- Unit: Verify table schema matches specification
- Integration: Write and read test items to each table
- Manual: AWS console validation of GSI and TTL

**Success Metrics:**
- All tables accessible via DynamoDB console
- TTL set correctly (verified in console)
- GSI returns correct results for article_id queries

---

### TASK-CLU-002: Embedding Service Enhancement
**Category:** Backend  
**Feature:** Clustering  
**Priority:** High  
**Effort:** 6 hours  
**Complexity:** Medium  

**Description:**
Enhance existing embedding service to support batch embeddings, caching, and error handling. Implement OpenAI text-embedding-3-small API calls with up to 100 articles per batch for efficiency.

**Implementation Details:**
- Create `backend/app/services/embedding_service.py`
- Implement `batch_embed_articles(articles: List[Article]) -> Dict[article_id, embedding]`
- Check article_embeddings table for cached embeddings before calling API
- Batch API calls (max 100 articles per call)
- Implement exponential backoff for API failures (3 retries)
- Store generated embeddings in article_embeddings table
- Handle edge cases: empty list, API rate limits, timeout

**Files to Create/Modify:**
- `backend/app/services/embedding_service.py` (new)
- `backend/app/models/embedding.py` (schemas)
- `backend/app/config.py` (OpenAI API key config)

**Acceptance Criteria:**
- [ ] Batch embedding API implemented
- [ ] Caching logic reduces API calls by 80%+
- [ ] Handles API failures with exponential backoff
- [ ] Stores embeddings in DynamoDB
- [ ] Unit tests pass (mocked API calls)
- [ ] Integration tests with real OpenAI API (staging only)

**Dependencies:**
- CLU-001 (DynamoDB tables)

**Testing:**
- Unit: Mock OpenAI API, test batching logic
- Integration: Test with real API (staging), verify caching
- Performance: Benchmark 1000 article embedding cost

**Success Metrics:**
- Embedding generation < 2 seconds per batch (100 articles)
- Cache hit rate > 80% on second run
- API errors handled gracefully with retries

---

### TASK-CLU-003: HDBSCAN Clustering Engine
**Category:** Backend  
**Feature:** Clustering  
**Priority:** High  
**Effort:** 8 hours  
**Complexity:** High  

**Description:**
Implement HDBSCAN clustering algorithm with parameter tuning. Process article embeddings to identify semantic topic clusters with automatic noise detection.

**Implementation Details:**
- Create `backend/app/services/clustering_engine.py`
- Implement `cluster_articles(embeddings: np.ndarray) -> Dict[article_id, cluster_id]`
- Use min_cluster_size=5, min_samples=3, metric='cosine'
- Handle edge cases: < 5 articles, all noise, empty embeddings
- Return cluster assignments and noise detection (cluster_id=-1 for noise)
- Log clustering statistics (num_clusters, noise_percent, avg_cluster_size)

**Files to Create/Modify:**
- `backend/app/services/clustering_engine.py` (new)
- `backend/app/models/cluster.py` (schemas)
- `requirements.txt` (add hdbscan>=0.8.30, scikit-learn>=1.3.0)

**Acceptance Criteria:**
- [ ] HDBSCAN clustering produces stable results
- [ ] Handles edge cases without crashes
- [ ] Noise articles identified (cluster_id=-1)
- [ ] Unit tests for clustering logic
- [ ] Integration tests with real embeddings
- [ ] Performance: < 5 minutes for 500 articles

**Dependencies:**
- CLU-002 (embeddings generated)

**Testing:**
- Unit: Test with synthetic embeddings, verify cluster counts
- Integration: Real embeddings, check noise detection
- Edge case: Test with 1 article, 4 articles, 5+ articles

**Success Metrics:**
- Clustering stable across runs (same articles → same clusters)
- Avg cluster size 5-50 articles (healthy distribution)
- Noise detection accurate (< 5% false positives)

---

### TASK-CLU-004: Celery Task for Clustering
**Category:** Backend  
**Feature:** Clustering  
**Priority:** High  
**Effort:** 6 hours  
**Complexity:** Medium  

**Description:**
Create Celery task to orchestrate the complete clustering pipeline. Run daily at 6am and 6pm UTC, fetching articles, generating embeddings, clustering, and storing results.

**Implementation Details:**
- Create `backend/app/workers/tasks/clustering_tasks.py`
- Implement `cluster_articles(self)` task with bind=True, max_retries=3
- Fetch articles from last 7 days
- Generate/retrieve embeddings
- Run HDBSCAN clustering
- Store results in article_clusters and cluster_metadata tables
- Set TTL to now + 7 days
- Add to Celery Beat schedule (6am & 6pm UTC)
- Error handling with exponential backoff (300s, 600s, 1200s)

**Files to Create/Modify:**
- `backend/app/workers/tasks/clustering_tasks.py` (new)
- `backend/app/workers/celery_app.py` (register task + beat schedule)
- `.env` (clustering config variables)
- `backend/app/config.py` (Settings class for clustering)

**Acceptance Criteria:**
- [ ] Task defined and registered with Celery
- [ ] Beat schedule configured (6am & 6pm UTC)
- [ ] Task fetches articles correctly
- [ ] Embeddings generated and cached
- [ ] Clustering runs without errors
- [ ] Results stored in DynamoDB
- [ ] TTL set correctly
- [ ] Retry logic works (max 3 attempts)
- [ ] CloudWatch logs populated

**Dependencies:**
- CLU-001, CLU-002, CLU-003 (core components)

**Testing:**
- Unit: Mock all external calls, verify task logic
- Integration: Run full task with test data
- Manual: Trigger task via Celery, check DynamoDB results

**Success Metrics:**
- Task completes in < 5 minutes for 500 articles
- All articles assigned to clusters (or marked as noise)
- TTL persisted correctly in DynamoDB
- CloudWatch shows successful executions

---

### TASK-CLU-005: Silhouette Score Metric
**Category:** ML  
**Feature:** Clustering  
**Priority:** Medium  
**Effort:** 4 hours  
**Complexity:** Medium  

**Description:**
Implement Silhouette Score calculation for evaluating cluster cohesion and separation. Measures how similar articles are to their own cluster vs other clusters.

**Implementation Details:**
- Create `backend/app/services/evaluation/silhouette.py`
- Implement `calculate_silhouette_score(embeddings, labels) -> float`
- Use sklearn.metrics.silhouette_score with cosine metric
- Handle edge cases: single cluster, all noise, < 5 articles
- Return score in range [-1, 1] (higher is better)
- Include unit tests with sample data

**Files to Create/Modify:**
- `backend/app/services/evaluation/silhouette.py` (new)
- `backend/app/services/evaluation/__init__.py`

**Acceptance Criteria:**
- [ ] Silhouette score calculated correctly
- [ ] Uses cosine metric (matching HDBSCAN)
- [ ] Handles edge cases gracefully
- [ ] Unit tests with sample embeddings
- [ ] Integration test with real clusters
- [ ] Performance: < 30s for 500 articles

**Dependencies:**
- CLU-003 (clustering produces labels)

**Testing:**
- Unit: Synthetic embeddings with known separation
- Integration: Real clusters, verify score interpretation
- Validation: Compare with sklearn reference implementation

**Success Metrics:**
- Score range [-1, 1] for all test cases
- Well-separated clusters: score > 0.7
- Overlapping clusters: score < 0.5

---

### TASK-CLU-006: Davies-Bouldin Index Metric
**Category:** ML  
**Feature:** Clustering  
**Priority:** Medium  
**Effort:** 4 hours  
**Complexity:** Medium  

**Description:**
Implement Davies-Bouldin Index for evaluating cluster tightness and separation. Measures average ratio of within-cluster to between-cluster distances. Lower is better.

**Implementation Details:**
- Create `backend/app/services/evaluation/davies_bouldin.py`
- Implement `calculate_davies_bouldin_index(embeddings, labels) -> float`
- Use sklearn.metrics.davies_bouldin_score
- Handle edge cases: single cluster, all noise
- Return score >= 0 (lower is better)
- Include unit tests

**Files to Create/Modify:**
- `backend/app/services/evaluation/davies_bouldin.py` (new)

**Acceptance Criteria:**
- [ ] Davies-Bouldin index calculated correctly
- [ ] Returns values >= 0
- [ ] Lower values indicate better clustering
- [ ] Handles edge cases
- [ ] Unit tests pass
- [ ] Integration test with real clusters

**Dependencies:**
- CLU-003 (clustering)

**Testing:**
- Unit: Synthetic embeddings with various separations
- Integration: Real clusters, verify score interpretation
- Validation: Compare with sklearn implementation

**Success Metrics:**
- Well-separated clusters: score < 1.0
- Overlapping clusters: score > 2.0

---

### TASK-CLU-007: Calinski-Harabasz Index Metric
**Category:** ML  
**Feature:** Clustering  
**Priority:** Medium  
**Effort:** 4 hours  
**Complexity:** Medium  

**Description:**
Implement Calinski-Harabasz Index for evaluating cluster density and definition. Measures ratio of between-cluster to within-cluster variance. Higher is better.

**Implementation Details:**
- Create `backend/app/services/evaluation/calinski_harabasz.py`
- Implement `calculate_calinski_harabasz_index(embeddings, labels) -> float`
- Use sklearn.metrics.calinski_harabasz_score
- Handle edge cases: single cluster, all noise
- Return score >= 0 (higher is better)
- Include unit tests

**Files to Create/Modify:**
- `backend/app/services/evaluation/calinski_harabasz.py` (new)

**Acceptance Criteria:**
- [ ] Calinski-Harabasz index calculated correctly
- [ ] Returns values >= 0
- [ ] Higher values indicate better clustering
- [ ] Handles edge cases
- [ ] Unit tests pass
- [ ] Integration test with real clusters

**Dependencies:**
- CLU-003 (clustering)

**Testing:**
- Unit: Synthetic embeddings
- Integration: Real clusters
- Validation: Compare with sklearn

**Success Metrics:**
- Dense clusters: score > 100
- Sparse clusters: score < 25

---

### TASK-CLU-008: Evaluation Pipeline & K-Value Selection
**Category:** Backend  
**Feature:** Clustering  
**Priority:** High  
**Effort:** 8 hours  
**Complexity:** High  

**Description:**
Implement complete clustering quality evaluation pipeline. Sweep k values from 5 to 100, calculate all three metrics, rank them, compute weighted composite scores, and select optimal k based on highest score.

**Implementation Details:**
- Create `backend/app/services/evaluation/evaluation_pipeline.py`
- Implement `evaluate_clustering_quality(embeddings, articles)`
- Parameter sweep: k from 5 to 100
- For each k: calculate silhouette, davies_bouldin, calinski_harabasz
- Implement ranking system: inverse ranking (rank 1 = best gets highest score)
- Calculate weighted composite score using admin weights
- Select k with highest composite_score
- Store all results in clustering_evaluation table
- Handle edge cases: < 5 articles, single cluster, all noise

**Files to Create/Modify:**
- `backend/app/services/evaluation/evaluation_pipeline.py` (new)
- `backend/app/services/evaluation/ranking.py` (ranking logic)

**Acceptance Criteria:**
- [ ] Parameter sweep covers k=5 to k=100 (96 values)
- [ ] All three metrics calculated for each k
- [ ] Ranking system produces correct inverse ranking
- [ ] Weighted composite score formula correct
- [ ] K-value selection accurate (highest score)
- [ ] Results stored in DynamoDB
- [ ] Performance: < 2 minutes for evaluation
- [ ] Unit tests for ranking and scoring logic

**Dependencies:**
- CLU-005, CLU-006, CLU-007 (metric functions)
- CLU-009 (DynamoDB evaluation table)

**Testing:**
- Unit: Test ranking with synthetic metrics
- Unit: Test weighted scoring formula
- Integration: Full evaluation with real embeddings
- Performance: Time 96 k-values, verify < 2 minutes

**Success Metrics:**
- All 96 k values evaluated
- Ranking system produces ranks 1-96 per metric
- Composite scores sum correctly
- Selected k has highest score

---

### TASK-CLU-009: Clustering Evaluation DynamoDB
**Category:** Infrastructure  
**Feature:** Clustering  
**Priority:** High  
**Effort:** 4 hours  
**Complexity:** Low  

**Description:**
Create DynamoDB table for storing clustering evaluation results. Store evaluation_id, metric scores, ranking data, selected k value, admin weights, and 3-metric plot URL.

**Implementation Details:**
- Create `tech-news-clustering_evaluation` table
- PK: evaluation_id (format: "eval-{YYYY-MM-DD}-{HH}-{MM}")
- GSI: run_timestamp (for historical queries)
- Attributes: all specified in clustering spec
- evaluation_results array with per-k metrics
- metrics_summary with statistical summaries
- TTL: 30 days (longer retention for history)
- Enable PITR

**Files to Create/Modify:**
- `infra/terraform/dynamodb.tf` (add evaluation table)

**Acceptance Criteria:**
- [ ] Table created with correct PK and GSI
- [ ] TTL enabled (30 days)
- [ ] PITR enabled
- [ ] Test write/read of evaluation result
- [ ] GSI queries work (timestamp range)
- [ ] Terraform plan correct

**Dependencies:**
- None (foundational)

**Testing:**
- Unit: Verify schema matches specification
- Integration: Write evaluation result, query by timestamp
- Manual: AWS console validation

**Success Metrics:**
- Table accessible via DynamoDB console
- TTL set to 30 days
- GSI returns results sorted by timestamp

---

### TASK-CLU-010: Admin Weights Configuration
**Category:** Backend  
**Feature:** Clustering  
**Priority:** Medium  
**Effort:** 4 hours  
**Complexity:** Low  

**Description:**
Implement admin configuration for metric weights in clustering evaluation. Store and retrieve weights from user_preferences table, validate weight values, and apply during evaluation.

**Implementation Details:**
- Create `backend/app/services/evaluation/admin_config.py`
- Implement `get_metric_weights(user_id)` - fetch from user_preferences
- Implement `update_metric_weights(user_id, weights)` - store with validation
- Validation: each weight 0-1, sum ≈ 1.0 (allow 0.99-1.01)
- Default weights: silhouette=0.5, davies_bouldin=0.3, calinski_harabasz=0.2
- Store in user_preferences table with "clustering_config" prefix

**Files to Create/Modify:**
- `backend/app/services/evaluation/admin_config.py` (new)
- `backend/app/models/user_preferences.py` (extend)

**Acceptance Criteria:**
- [ ] Weights stored in user_preferences table
- [ ] Weights retrieved correctly
- [ ] Validation rejects invalid weights
- [ ] Default weights applied if none set
- [ ] Weights can be updated without errors
- [ ] Unit tests for validation logic

**Dependencies:**
- CLU-008 (uses weights in evaluation)

**Testing:**
- Unit: Test weight validation
- Unit: Test default weights
- Integration: Store and retrieve weights from DynamoDB

**Success Metrics:**
- Invalid weights rejected (negative, > 1.0, sum != ~1.0)
- Default weights returned for new admins
- Updated weights persist in DynamoDB

---

### TASK-CLU-011: Visualization 3-Metric Plot
**Category:** Backend  
**Feature:** Clustering  
**Priority:** Medium  
**Effort:** 6 hours  
**Complexity:** Medium  

**Description:**
Generate 3-metric plot showing how silhouette, davies-bouldin, and calinski-harabasz scores vary across k values. Mark selected k with vertical line. Store plot as image in S3 for API response.

**Implementation Details:**
- Create `backend/app/services/evaluation/visualization.py`
- Implement `generate_metrics_plot(evaluation_results, selected_k) -> s3_url`
- X-axis: k values (5 to 100)
- Y-axes: 3 different axes for 3 metrics (scaled appropriately)
- Lines: silhouette_score, davies_bouldin_index, calinski_harabasz_index
- Vertical line: mark selected k
- Annotations: peak scores, optimal regions
- Use matplotlib or plotly
- Save to S3 bucket: s3://tech-news-{env}/clustering-plots/{evaluation_id}.png
- Return presigned URL (24hr validity)

**Files to Create/Modify:**
- `backend/app/services/evaluation/visualization.py` (new)
- `backend/app/integrations/s3_client.py` (upload and presign)

**Acceptance Criteria:**
- [ ] Plot generated with all three metrics visible
- [ ] K-axis spans 5-100
- [ ] Selected k marked clearly
- [ ] Plot saved to S3
- [ ] Presigned URL returned
- [ ] URL expires in 24 hours
- [ ] Plot readable and informative
- [ ] Unit tests (mock S3)

**Dependencies:**
- CLU-008 (evaluation results)

**Testing:**
- Unit: Mock S3, verify plot generation
- Integration: Real S3, verify upload and URL
- Visual: Manual inspection of plot

**Success Metrics:**
- Plot shows all three metrics clearly
- Selected k visually marked
- URL works for 24 hours

---

### TASK-CLU-012: Cluster API Endpoints
**Category:** Backend  
**Feature:** Clustering  
**Priority:** High  
**Effort:** 8 hours  
**Complexity:** Medium  

**Description:**
Implement FastAPI endpoints for cluster queries: list clusters, get cluster details, view trending clusters. Support filtering, sorting, and pagination.

**Implementation Details:**
- Create `backend/app/api/v1/clusters.py` router
- Implement `GET /v1/clusters` - list all clusters with pagination
  - Query params: page, page_size, sort_by (size|recency|diversity)
  - Return cluster metadata, top articles, pagination info
- Implement `GET /v1/clusters/{cluster_id}` - detailed cluster view
  - Return all articles in cluster with pagination
  - Include confidence scores
- Implement `GET /v1/clusters/trending` - trending clusters
  - Sort by engagement, updated hourly
  - Limit configurable
- Caching: 30-minute cache on list responses
- Response validation with Pydantic schemas
- Error handling: 404 for missing clusters, 400 for invalid params

**Files to Create/Modify:**
- `backend/app/api/v1/clusters.py` (new)
- `backend/app/schemas/clusters.py` (Pydantic models)
- `backend/app/main.py` (register router)
- `backend/app/services/cluster_service.py` (business logic)

**Acceptance Criteria:**
- [ ] All three endpoints implemented
- [ ] Pagination works correctly
- [ ] Sorting by size, recency, diversity
- [ ] 30-minute caching working
- [ ] Response schemas validated
- [ ] Error handling for edge cases
- [ ] Unit tests for each endpoint
- [ ] Integration tests with mock data
- [ ] Performance: < 500ms p95 response time

**Dependencies:**
- CLU-004 (clusters in DynamoDB)

**Testing:**
- Unit: Mock DynamoDB, test endpoint logic
- Integration: Real DynamoDB queries
- Performance: Load test with 1000+ clusters
- E2E: API calls via postman/curl

**Success Metrics:**
- All endpoints return correct data
- Pagination limits per page (max 100)
- Trending clusters update hourly
- Cache hit rate > 70%
- p95 response time < 500ms

---

### TASK-CLU-013: Admin Evaluation Endpoints
**Category:** Backend  
**Feature:** Clustering  
**Priority:** Medium  
**Effort:** 6 hours  
**Complexity:** Medium  

**Description:**
Implement admin-only FastAPI endpoints for clustering evaluation management. Retrieve results, update weights, trigger manual evaluation, get historical results.

**Implementation Details:**
- Create endpoints in `backend/app/api/v1/admin/clustering.py`
- Implement `GET /v1/admin/clustering/evaluation` - latest evaluation
- Implement `PUT /v1/admin/clustering/weights` - update metric weights
  - Body: silhouette_weight, davies_bouldin_weight, calinski_harabasz_weight
  - Optional: trigger_re_evaluation (bool)
  - Returns: new weights, evaluation_task_id if triggered
- Implement `POST /v1/admin/clustering/evaluate` - manual evaluation
  - Body: k_min, k_max, use_current_articles, force_embedding_refresh
  - Returns: evaluation_id, status, estimated_duration
- Implement `GET /v1/admin/clustering/evaluation/{evaluation_id}` - specific result
- Admin auth required on all endpoints
- Return 403 for non-admin users

**Files to Create/Modify:**
- `backend/app/api/v1/admin/clustering.py` (new)
- `backend/app/services/evaluation/admin_service.py` (business logic)

**Acceptance Criteria:**
- [ ] All four endpoints implemented
- [ ] Admin auth enforced (403 for non-admin)
- [ ] Weight update triggers re-evaluation if requested
- [ ] Manual evaluation task created and tracked
- [ ] Historical results retrievable by ID
- [ ] Response schemas correct
- [ ] Unit tests with auth mocking
- [ ] Integration tests for happy path

**Dependencies:**
- CLU-008, CLU-010, CLU-013 (evaluation components)

**Testing:**
- Unit: Mock auth, test endpoint logic
- Unit: Test admin check (403 response)
- Integration: Weight update → re-evaluation trigger
- Manual: Verify endpoints accessible only to admin

**Success Metrics:**
- Non-admin requests return 403
- Weight updates persist
- Manual evaluation creates task
- Historical results retrieved correctly

---

### TASK-CLU-014: Frontend Topics Page
**Category:** Frontend  
**Feature:** Clustering  
**Priority:** High  
**Effort:** 12 hours  
**Complexity:** Medium  

**Description:**
Create /topics page with cluster listing, filtering, sorting, and search. Responsive grid layout with cluster cards. Integrate with backend cluster APIs.

**Implementation Details:**
- Create `frontend/src/pages/TopicsPage.tsx`
- Fetch clusters from `GET /v1/clusters` with pagination
- Implement filtering: size (small/medium/large), date range
- Implement sorting: by size, recency, diversity
- Search topics by name or keywords
- Responsive grid layout: 3 cols desktop, 2 cols tablet, 1 col mobile
- Handle loading and error states
- Implement infinite scroll or pagination
- Add "Trending" tab variant

**Files to Create/Modify:**
- `frontend/src/pages/TopicsPage.tsx` (new)
- `frontend/src/hooks/useClusters.ts` (API hook)
- `frontend/src/components/ClusterGrid.tsx` (grid layout)
- `frontend/src/styles/topics.css`

**Acceptance Criteria:**
- [ ] Topics page renders with cluster data
- [ ] Filtering works for all criteria
- [ ] Sorting produces correct order
- [ ] Search filters clusters by name
- [ ] Responsive design on all breakpoints
- [ ] Loading and error states handled
- [ ] Pagination works (or infinite scroll)
- [ ] Unit tests for components
- [ ] Integration tests with mock API

**Dependencies:**
- CLU-012 (cluster APIs)

**Testing:**
- Component: Unit tests for filtering/sorting logic
- Integration: Mock API responses
- E2E: Navigate to /topics, interact with controls
- Visual: Screenshot testing for responsive design

**Success Metrics:**
- Topics page loads and displays clusters
- Filter/sort/search work correctly
- Responsive on mobile (375px), tablet (768px), desktop (1920px)
- Performance: page load < 2 seconds

---

### TASK-CLU-015: Cluster Card Component
**Category:** Frontend  
**Feature:** Clustering  
**Priority:** Medium  
**Effort:** 8 hours  
**Complexity:** Low  

**Description:**
Create reusable ClusterCard component with liquid glass design. Display cluster label, keywords, article count, diversity score, top articles, and engagement metrics.

**Implementation Details:**
- Create `frontend/src/components/ClusterCard.tsx`
- Props: cluster object, onClick handler
- Display: label, description, keywords (badges), stats
- Stats: article_count, diversity_score, engagement_score
- Top articles: show up to 3 with titles and scores
- Liquid glass styling: 20px blur, rgba(255, 255, 255, 0.1), border
- Hover effect: slight elevation, increased blur opacity
- Click opens cluster detail view
- Mobile: stack layout (no side-by-side)

**Files to Create/Modify:**
- `frontend/src/components/ClusterCard.tsx` (new)
- `frontend/src/components/KeywordBadge.tsx` (reusable badge)
- `frontend/src/styles/liquid-glass.css` (shared styling)

**Acceptance Criteria:**
- [ ] Component renders cluster data correctly
- [ ] Liquid glass styling applied
- [ ] Hover effects smooth and visible
- [ ] Keywords displayed as badges
- [ ] Top articles shown with engagement scores
- [ ] Responsive on mobile (full width, no hover)
- [ ] Keyboard accessible (Tab, Enter)
- [ ] Unit tests for rendering
- [ ] Storybook stories created

**Dependencies:**
- Design system (color palette, typography)

**Testing:**
- Component: Snapshot tests for rendering
- Visual: Storybook with various cluster sizes
- Interaction: Click handler called on click
- Accessibility: Keyboard navigation

**Success Metrics:**
- Component renders all cluster properties
- Liquid glass effect visible
- Hover animations smooth
- Mobile layout responsive

---

### TASK-CLU-016: Cluster Detail View
**Category:** Frontend  
**Feature:** Clustering  
**Priority:** Medium  
**Effort:** 10 hours  
**Complexity:** Medium  

**Description:**
Create detailed cluster view showing all articles in cluster with filtering, sorting, and pagination. Display cluster metadata, keywords, diversity metrics, and article list.

**Implementation Details:**
- Create `frontend/src/pages/ClusterDetailPage.tsx`
- Fetch cluster from `GET /v1/clusters/{cluster_id}`
- Display: cluster label, description, keywords, stats
- Article list with pagination (20 per page)
- Filter by: source, date range, engagement
- Sort by: latest, engagement, relevance
- Back button to return to topics list
- Show confidence_score for each article
- Responsive layout (sidebar on desktop, stacked on mobile)

**Files to Create/Modify:**
- `frontend/src/pages/ClusterDetailPage.tsx` (new)
- `frontend/src/components/ArticleListView.tsx` (reusable)
- `frontend/src/hooks/useClusterDetail.ts` (API hook)
- `frontend/src/styles/cluster-detail.css`

**Acceptance Criteria:**
- [ ] Cluster metadata displays correctly
- [ ] Articles paginated (20 per page)
- [ ] Filtering works for source, date, engagement
- [ ] Sorting produces correct order
- [ ] Back navigation works
- [ ] Responsive on all breakpoints
- [ ] Confidence scores shown
- [ ] Loading and error states handled
- [ ] Unit tests for components
- [ ] Integration tests with mock API

**Dependencies:**
- CLU-012 (cluster detail API)

**Testing:**
- Component: Unit tests for filters/sort
- Integration: Mock API responses
- E2E: Navigate to cluster, interact with filters
- Visual: Responsive layout testing

**Success Metrics:**
- Cluster detail loads and displays articles
- Pagination and filtering work
- Responsive design on all sizes
- Performance: page load < 2 seconds

---

### TASK-CLU-017: Terraform Clustering Infrastructure
**Category:** Infrastructure  
**Feature:** Clustering  
**Priority:** High  
**Effort:** 8 hours  
**Complexity:** Medium  

**Description:**
Complete Terraform configuration for clustering infrastructure. DynamoDB tables (with all attributes), IAM policies, CloudWatch logs, alarms, and ECS task definition for clustering worker.

**Implementation Details:**
- Add DynamoDB table resources (from CLU-001)
- Create IAM role: clustering-task-role
  - Permissions: DynamoDB (read/write/batch), Bedrock (InvokeModel), CloudWatch (logs)
- Create IAM role: clustering-task-execution-role
  - Standard ECS task execution permissions
- CloudWatch log group: `/ecs/clustering-worker`
- CloudWatch alarms:
  - Task failure alarm (threshold: 1)
  - Task duration alarm (threshold: 5 minutes)
- ECS task definition for clustering
  - CPU: 1024, Memory: 2048
  - Environment variables: all clustering config
  - Log driver: awslogs (CloudWatch)

**Files to Create/Modify:**
- `infra/terraform/dynamodb.tf` (reviewed/extended)
- `infra/terraform/iam.tf` (clustering role and policy)
- `infra/terraform/cloudwatch.tf` (logs and alarms)
- `infra/terraform/ecs.tf` (task definition)
- `infra/terraform/variables.tf` (if needed)

**Acceptance Criteria:**
- [ ] All Terraform resources defined
- [ ] IAM role has minimum required permissions
- [ ] CloudWatch logs configured
- [ ] Alarms configured for failure and duration
- [ ] ECS task definition correct
- [ ] Variables parameterized (no hardcoded values)
- [ ] `terraform plan` shows all resources
- [ ] `terraform apply` succeeds
- [ ] Resources visible in AWS console

**Dependencies:**
- CLU-001 (DynamoDB schemas)

**Testing:**
- Terraform: `terraform plan` and `terraform apply`
- Manual: Verify resources in AWS console
- Validation: Check IAM permissions are minimal

**Success Metrics:**
- All resources created successfully
- No hard-coded values in Terraform
- IAM policy follows least privilege
- CloudWatch alarms functional

---

### TASK-CLU-018: CloudWatch Monitoring Setup
**Category:** Workflow  
**Feature:** Clustering  
**Priority:** Medium  
**Effort:** 4 hours  
**Complexity:** Low  

**Description:**
Set up CloudWatch metrics, dashboards, and alarms for clustering tasks. Monitor task duration, success rate, article processing, and data quality metrics.

**Implementation Details:**
- Create CloudWatch dashboard: "Clustering Overview"
  - Graph 1: Task execution count (daily)
  - Graph 2: Task duration (avg, p95)
  - Graph 3: Success rate (%)
  - Graph 4: Articles processed (daily)
  - Graph 5: Cluster count (current)
- Custom metrics from Celery task:
  - TaskDuration (milliseconds)
  - ArticlesProcessed (count)
  - ClustersCreated (count)
  - NoisePercentage (%)
- Alarms:
  - Task failure (SNS to ops)
  - Duration exceeds 5 minutes (SNS alert)
  - Success rate < 90% (SNS alert)
- Log insights queries for troubleshooting

**Files to Create/Modify:**
- `infra/terraform/cloudwatch.tf` (dashboard and alarms)
- `backend/app/workers/tasks/clustering_tasks.py` (emit metrics)

**Acceptance Criteria:**
- [ ] CloudWatch dashboard created
- [ ] All metrics visible on dashboard
- [ ] Alarms configured and tested
- [ ] SNS notifications working
- [ ] Log Insights queries documented
- [ ] Metrics published from Celery task
- [ ] Dashboard readable and informative

**Dependencies:**
- CLU-004 (Celery task)
- CLU-017 (Terraform infrastructure)

**Testing:**
- Manual: Trigger task, verify metrics appear
- Alarm: Simulate failure, check SNS notification
- Dashboard: Verify all graphs render

**Success Metrics:**
- Dashboard displays real-time metrics
- Alarms trigger correctly on failures
- SNS notifications received
- Metrics retained for 7 days

---

### TASK-CLU-019: End-to-End Testing Clustering
**Category:** Workflow  
**Feature:** Clustering  
**Priority:** Medium  
**Effort:** 8 hours  
**Complexity:** Medium  

**Description:**
Comprehensive end-to-end testing of clustering feature. Test full pipeline from article ingestion to cluster API queries. Verify data consistency and performance.

**Implementation Details:**
- Create `backend/tests/e2e/test_clustering_pipeline.py`
- Test scenario 1: New articles → embedding → clustering → API query
  - Insert 100 test articles
  - Trigger clustering task
  - Verify clusters created in DynamoDB
  - Query /v1/clusters endpoint
  - Verify response contains all clusters
- Test scenario 2: Evaluation pipeline
  - Trigger evaluation manually
  - Verify all 96 k-values evaluated
  - Check results in clustering_evaluation table
  - Verify selected k-value is optimal
- Test scenario 3: Admin weight update
  - Update metric weights
  - Trigger re-evaluation
  - Verify new weights applied
  - Check selected k changes appropriately
- Test scenario 4: Pagination and filtering
  - Query /v1/clusters with various filters
  - Verify pagination works correctly
  - Check sorting by size, recency, diversity

**Files to Create/Modify:**
- `backend/tests/e2e/test_clustering_pipeline.py` (new)
- `backend/tests/fixtures/clustering_data.py` (test data)

**Acceptance Criteria:**
- [ ] All test scenarios pass
- [ ] Data consistency verified across pipeline
- [ ] API responses match schema
- [ ] Performance within SLAs (< 5 min for clustering)
- [ ] Error cases handled (missing articles, invalid k)
- [ ] Test data cleaned up after execution

**Dependencies:**
- All clustering tasks (CLU-001 through CLU-013)

**Testing:**
- End-to-end: Run all scenarios sequentially
- Data validation: Verify DynamoDB state after each step
- API validation: Verify responses match schema

**Success Metrics:**
- All test scenarios pass
- 100% data consistency
- API performance within SLAs
- No orphaned test data

---

### TASK-CLU-020: Clustering Documentation
**Category:** Workflow  
**Feature:** Clustering  
**Priority:** Low  
**Effort:** 4 hours  
**Complexity:** Low  

**Description:**
Write comprehensive documentation for clustering feature. API docs, architecture overview, deployment guide, troubleshooting guide, and user guide.

**Implementation Details:**
- Create `docs/clustering/API.md` - OpenAPI spec with examples
- Create `docs/clustering/ARCHITECTURE.md` - system design, data flow
- Create `docs/clustering/DEPLOYMENT.md` - step-by-step deployment
- Create `docs/clustering/TROUBLESHOOTING.md` - common issues and fixes
- Create `docs/clustering/USER_GUIDE.md` - how to use topics page
- Update main README.md with clustering feature overview
- Generate Swagger UI from FastAPI decorators

**Files to Create/Modify:**
- `docs/clustering/API.md` (new)
- `docs/clustering/ARCHITECTURE.md` (new)
- `docs/clustering/DEPLOYMENT.md` (new)
- `docs/clustering/TROUBLESHOOTING.md` (new)
- `docs/clustering/USER_GUIDE.md` (new)
- `README.md` (update with clustering section)

**Acceptance Criteria:**
- [ ] All docs created and reviewed
- [ ] API docs include all endpoints with examples
- [ ] Architecture docs explain data flow
- [ ] Deployment guide step-by-step and tested
- [ ] Troubleshooting covers 10+ common issues
- [ ] User guide explains UI features
- [ ] Swagger UI generated and functional
- [ ] README updated

**Dependencies:**
- All clustering tasks complete

**Testing:**
- Review: Technical review by team
- Validation: Follow deployment guide, verify it works
- Completeness: Checklist of all features documented

**Success Metrics:**
- Docs complete and accurate
- Deployment guide tested successfully
- No broken links or incomplete sections

---

## Chatbot Tasks

### TASK-CHT-001: DynamoDB Tables for Chat
**Category:** Infrastructure  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 4 hours  
**Complexity:** Low  

**Description:**
Create three DynamoDB tables for chatbot: conversation_sessions (session metadata), conversation_messages (message history), chat_user_preferences (user settings).

**Implementation Details:**
- Create `tech-news-conversation_sessions` table
  - PK: user_id, SK: session_id
  - GSI: user_id-last_message_at-index
  - TTL: 90 days
- Create `tech-news-conversation_messages` table
  - PK: session_id, SK: message_id
  - GSI: session_id-timestamp-index
  - TTL: 90 days
- Create `tech-news-chat_user_preferences` table
  - PK: user_id
  - No TTL (permanent user settings)
- Enable PITR on all tables
- Enable billing mode: PAY_PER_REQUEST

**Files to Create/Modify:**
- `infra/terraform/dynamodb.tf` (add chat tables)
- `backend/app/models/chat.py` (Pydantic schemas)

**Acceptance Criteria:**
- [ ] All three tables created
- [ ] PK/SK and GSI configured correctly
- [ ] TTL enabled (90 days on sessions/messages)
- [ ] PITR enabled
- [ ] Test write/read operations
- [ ] Terraform plan correct

**Dependencies:**
- None (foundational)

**Testing:**
- Unit: Verify schemas match spec
- Integration: Write/read test data
- Manual: AWS console validation

**Success Metrics:**
- All tables visible in DynamoDB console
- TTL and PITR enabled
- Test items persist correctly

---

### TASK-CHT-002: Agent Core Runtime ECS Setup
**Category:** Infrastructure  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 8 hours  
**Complexity:** Medium  

**Description:**
Deploy AWS Agent Core Runtime as ECS service. Set up cluster, task definition, load balancer, auto-scaling, and health checks. Agent Core handles LangChain/LangGraph workflows and tool orchestration.

**Implementation Details:**
- Create ECS cluster: `tech-news-agent-core`
- Create task definition: `tech-news-agent-core-task`
  - Image: AWS Agent Core runtime image
  - CPU: 2048, Memory: 4096
  - Environment: AGENT_MODEL, MEMORY_TYPE, TOOL_TIMEOUT
  - Log driver: CloudWatch
- Create ALB: internal load balancer (VPC-only)
- Target group: 8080 port, health check: `/health`
- Auto-scaling: min 2, max 10 replicas
- Security group: allow 8080 from backend VPC
- CloudWatch logs: `/ecs/agent-core`

**Files to Create/Modify:**
- `infra/terraform/ecs.tf` (agent-core cluster and service)
- `infra/terraform/load_balancer.tf` (internal ALB)
- `infra/terraform/security_groups.tf` (agent-core SG)
- `infra/terraform/cloudwatch.tf` (logs and alarms)

**Acceptance Criteria:**
- [ ] ECS cluster created
- [ ] Task definition registered
- [ ] Service running (2 replicas)
- [ ] Load balancer health checks passing
- [ ] Service accessible from backend VPC
- [ ] Auto-scaling policies configured
- [ ] CloudWatch logs working
- [ ] Terraform plan correct

**Dependencies:**
- VPC setup (existing)

**Testing:**
- Manual: Check ECS console for running tasks
- Manual: Verify health checks passing
- Manual: Test API endpoint from backend VPC
- Load: Scale up to 10 replicas, verify auto-scaling

**Success Metrics:**
- 2 Agent Core tasks running
- Health checks passing
- Load balancer routing traffic
- Auto-scaling responding to load

---

### TASK-CHT-003: Agent Core IAM & Security
**Category:** Infrastructure  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 4 hours  
**Complexity:** Low  

**Description:**
Create IAM roles and policies for Agent Core Runtime. Allow access to Bedrock (Claude Haiku), DynamoDB (sessions), CloudWatch (logs), and semantic search integration.

**Implementation Details:**
- Create IAM execution role: `agent-core-execution-role`
  - Policy: AmazonECSTaskExecutionRolePolicy (standard)
- Create IAM task role: `agent-core-task-role`
  - Permissions: bedrock:InvokeModel, bedrock:InvokeModelWithResponseStream
  - Permissions: dynamodb:GetItem, dynamodb:Query (sessions/messages)
  - Permissions: logs:* (CloudWatch)
  - Permissions: qdrant:query (for semantic search)
- Security group: allow 8080 from backend SG only
- No internet access needed (internal VPC)

**Files to Create/Modify:**
- `infra/terraform/iam.tf` (agent-core roles)
- `infra/terraform/security_groups.tf` (agent-core SG)

**Acceptance Criteria:**
- [ ] Execution role created with standard policy
- [ ] Task role created with minimal permissions
- [ ] Bedrock permissions included
- [ ] DynamoDB permissions for sessions/messages
- [ ] CloudWatch logs permission
- [ ] Security group restricts to backend VPC
- [ ] No internet access allowed
- [ ] Terraform plan correct

**Dependencies:**
- CHT-002 (ECS setup)

**Testing:**
- Policy review: Verify least privilege
- Manual: Check roles in IAM console
- Test: Verify Agent Core can invoke Bedrock

**Success Metrics:**
- IAM roles follow least privilege principle
- No overly permissive policies
- Security group restricts access correctly

---

### TASK-CHT-004: Agent Core Memory Configuration
**Category:** Backend  
**Feature:** Chatbot  
**Priority:** Medium  
**Effort:** 4 hours  
**Complexity:** Low  

**Description:**
Configure Agent Core Memory service for short-term conversation context. Set up memory hooks for agent initialization and event logging.

**Implementation Details:**
- Configure Agent Core Memory type: SHORT_TERM
- Set memory hooks: agent_initialized event
- Load recent conversation events on init
- Log user/assistant messages during conversation
- Session-scoped memory (90-day TTL matching DynamoDB)
- No long-term extraction (focus on immediate context)
- Event structure: role, content, timestamp

**Files to Create/Modify:**
- `backend/app/integrations/agent_core_memory.py` (new)
- `backend/app/config.py` (memory configuration)

**Acceptance Criteria:**
- [ ] Memory configuration set to SHORT_TERM
- [ ] Agent initialization loads recent events
- [ ] Events logged during conversation
- [ ] Memory persists for session duration
- [ ] TTL matches DynamoDB (90 days)
- [ ] Unit tests for memory operations

**Dependencies:**
- CHT-002 (Agent Core Runtime)

**Testing:**
- Unit: Mock memory service, test event logging
- Integration: Real Agent Core, verify event retrieval
- Session: Start session, send message, verify in memory

**Success Metrics:**
- Memory loads on agent init
- Events persist during session
- Memory expires after 90 days

---

### TASK-CHT-005: FastAPI Chat Router
**Category:** Backend  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 8 hours  
**Complexity:** Medium  

**Description:**
Create FastAPI router with chat endpoints. Handle message streaming, session creation/listing, authentication, and session validation. Integrate with Agent Core Runtime.

**Implementation Details:**
- Create `backend/app/api/v1/chat/router.py`
- Implement `POST /api/v1/chat/message` (streaming via SSE)
  - Auth required, session validation
  - Save user message to DynamoDB
  - Stream response from Agent Core
  - Save assistant message after streaming
- Implement `GET /api/v1/chat/sessions` (list sessions)
  - Pagination, sorting by recency
  - Return session metadata (title, preview, message_count)
- Implement `POST /api/v1/chat/sessions` (create session)
  - Generate session_id
  - Store in DynamoDB
  - Return session object
- Implement `GET /api/v1/chat/sessions/{session_id}` (session details)
  - Message history with pagination
  - Auth check (user_id validation)
- Error handling: 404, 403, 500 with descriptive messages

**Files to Create/Modify:**
- `backend/app/api/v1/chat/router.py` (new)
- `backend/app/schemas/chat.py` (request/response models)
- `backend/app/main.py` (register router)

**Acceptance Criteria:**
- [ ] All endpoints implemented
- [ ] Auth required on all endpoints
- [ ] Streaming works via SSE
- [ ] Session validation enforced
- [ ] Error handling for all cases
- [ ] Request/response schemas validated
- [ ] Unit tests for each endpoint
- [ ] Integration tests with mock Agent Core

**Dependencies:**
- CHT-001 (DynamoDB tables)

**Testing:**
- Unit: Mock auth and Agent Core
- Integration: Mock DynamoDB and Agent Core
- E2E: Test endpoint with curl/postman

**Success Metrics:**
- All endpoints respond correctly
- Auth enforced (403 for invalid users)
- SSE streaming works
- Data persisted to DynamoDB

---

### TASK-CHT-006: Chat Service CRUD
**Category:** Backend  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 6 hours  
**Complexity:** Medium  

**Description:**
Implement ChatService class with CRUD operations for sessions and messages. Handle DynamoDB interactions, pagination, and business logic.

**Implementation Details:**
- Create `backend/app/services/chat_service.py`
- Implement `create_session(user_id, title) -> Session`
- Implement `get_session(session_id, user_id) -> Session or None`
- Implement `list_sessions(user_id, page, page_size, sort_by) -> List[Session]`
- Implement `add_message(session_id, user_id, role, content) -> Message`
- Implement `get_messages(session_id, page, page_size) -> List[Message]`
- Implement `archive_session(session_id, user_id) -> bool`
- Session TTL: 90 days
- Message TTL: 90 days
- Handle pagination: offset/limit
- Validate user ownership (access control)

**Files to Create/Modify:**
- `backend/app/services/chat_service.py` (new)
- `backend/app/models/chat.py` (domain models)

**Acceptance Criteria:**
- [ ] All CRUD operations implemented
- [ ] Pagination working correctly
- [ ] User ownership validated
- [ ] TTL set on all records
- [ ] Unit tests for all methods
- [ ] Integration tests with DynamoDB
- [ ] Error handling for invalid data

**Dependencies:**
- CHT-001 (DynamoDB tables)

**Testing:**
- Unit: Mock DynamoDB, test business logic
- Integration: Real DynamoDB, test CRUD ops
- Access: Verify user can only access own sessions

**Success Metrics:**
- CRUD operations work correctly
- Pagination limits enforced
- User isolation working
- TTL persisted to DynamoDB

---

### TASK-CHT-007: Agent Core Client (HTTP API)
**Category:** Backend  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 8 hours  
**Complexity:** High  

**Description:**
Create HTTP client for Agent Core Runtime API. Handle authentication, streaming responses, tool invocation, and error handling. Support async streaming for real-time token delivery.

**Implementation Details:**
- Create `backend/app/integrations/agent_core_client.py`
- Implement `AgentCoreClient` class with async support
- Method: `invoke_agent(session_id, user_message, context, user_id)`
  - Returns: AsyncGenerator[Dict] (streaming events)
- Streaming events: token, tool_invocation, tool_result, done, error
- HTTP client: httpx.AsyncClient with connection pooling
- Authentication: X-API-Key header
- Base URL: internal load balancer (VPC)
- Timeout: 60 seconds per request
- Retry logic: exponential backoff for 5xx errors (max 3 retries)
- Tool registration: register semantic_search tool with Agent Core

**Files to Create/Modify:**
- `backend/app/integrations/agent_core_client.py` (new)
- `backend/app/config.py` (Agent Core URL, API key)

**Acceptance Criteria:**
- [ ] HTTP client created with async support
- [ ] Streaming responses work correctly
- [ ] Tool invocations parsed and forwarded
- [ ] Error handling for network failures
- [ ] Retry logic with exponential backoff
- [ ] Authentication header included
- [ ] Unit tests with mocked responses
- [ ] Integration tests with real Agent Core

**Dependencies:**
- CHT-002 (Agent Core Runtime)

**Testing:**
- Unit: Mock HTTP responses, test streaming parsing
- Integration: Real Agent Core, test end-to-end
- Error: Simulate network failures, verify retries
- Performance: Test streaming speed

**Success Metrics:**
- Streaming responses parsed correctly
- Tool calls forwarded to correct handlers
- Error handling robust
- Retry logic working

---

### TASK-CHT-008: Semantic Search Tool
**Category:** Backend  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 10 hours  
**Complexity:** High  

**Description:**
Implement semantic search tool for Agent Core. Search article embeddings in Qdrant for similarity to user queries. Enrich results with article metadata from DynamoDB.

**Implementation Details:**
- Create `backend/app/tools/semantic_search_tool.py`
- Class: `SemanticSearchTool` with:
  - `execute(query, top_k, min_score, filters) -> List[ArticleResult]`
  - Embed query using Bedrock (same service as articles)
  - Search Qdrant by vector similarity
  - Fetch article metadata from DynamoDB
  - Enrich with engagement score
  - Filter by source, date range if provided
  - Return top_k results (default 10)
- Tool definition schema for Agent Core registration
- Result structure: article_id, title, summary, relevance_score, source, url, published_at

**Files to Create/Modify:**
- `backend/app/tools/semantic_search_tool.py` (new)
- `backend/app/models/search_result.py` (result schemas)
- `backend/app/services/embedding_service.py` (query embedding)

**Acceptance Criteria:**
- [ ] Tool embedded and searches Qdrant
- [ ] Results enriched with DynamoDB metadata
- [ ] Filtering by source/date working
- [ ] Relevance scores included
- [ ] Tool definition schema correct
- [ ] Unit tests for search logic
- [ ] Integration tests with Qdrant and DynamoDB
- [ ] Performance: < 500ms for search

**Dependencies:**
- Qdrant vector database (existing)
- DynamoDB articles table (existing)

**Testing:**
- Unit: Mock Qdrant and DynamoDB
- Integration: Real Qdrant and DynamoDB
- Performance: Benchmark search latency
- Accuracy: Verify relevant articles returned

**Success Metrics:**
- Search returns relevant articles
- Scores reflect relevance correctly
- Performance < 500ms
- Results enriched with all fields

---

### TASK-CHT-009: Tool Registration & Orchestration
**Category:** Backend  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 6 hours  
**Complexity:** Medium  

**Description:**
Register custom semantic search tool with Agent Core Runtime. Set up tool handlers and orchestration for all three tools (browser, code interpreter, semantic search).

**Implementation Details:**
- Register semantic_search tool with Agent Core on startup
- Tool definition: schema, input/output types, description
- Tool handler: routes invocations to SemanticSearchTool.execute()
- Built-in tools (browser, code_interpreter): already provided by AWS
- Startup hook in FastAPI: register tools during initialization
- Tool invocation tracking: log all tool calls with args and results
- Error handling: tool failures don't crash agent

**Files to Create/Modify:**
- `backend/app/integrations/agent_core_client.py` (register_custom_tools)
- `backend/app/main.py` (startup hook)
- `backend/app/config.py` (tool configuration)

**Acceptance Criteria:**
- [ ] Semantic search tool registered with Agent Core
- [ ] Tool schema matches specification
- [ ] Tool invocations routed correctly
- [ ] Tool failures handled gracefully
- [ ] Built-in tools available (browser, code interpreter)
- [ ] Tool call logging working
- [ ] Unit tests for registration
- [ ] Integration tests with Agent Core

**Dependencies:**
- CHT-007 (Agent Core Client)
- CHT-008 (Semantic Search Tool)

**Testing:**
- Unit: Mock Agent Core, test registration
- Integration: Real Agent Core, verify tool invocation
- Error: Trigger tool failure, verify handling
- Logging: Check CloudWatch for tool call logs

**Success Metrics:**
- Tools registered successfully
- Tool invocations work correctly
- All three tools available in agent

---

### TASK-CHT-010: SSE Streaming Implementation
**Category:** Backend  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 8 hours  
**Complexity:** Medium  

**Description:**
Implement Server-Sent Events (SSE) for streaming chat responses. Parse Agent Core events (tokens, tool calls, results) and emit to frontend in real-time.

**Implementation Details:**
- Create event generator in `/api/v1/chat/message` endpoint
- Streaming events:
  - `token`: single token from response
  - `tool_invocation`: agent is calling a tool
  - `tool_result`: tool execution complete
  - `done`: conversation complete
  - `error`: error occurred
- SSE headers: Cache-Control: no-cache, Connection: keep-alive
- No proxy buffering: X-Accel-Buffering: no
- Event format: `event: {type}\ndata: {json}\n\n`
- Save full response to DynamoDB after streaming completes
- Handle connection drops gracefully

**Files to Create/Modify:**
- `backend/app/api/v1/chat/router.py` (streaming implementation)
- `backend/app/integrations/agent_core_client.py` (event parsing)

**Acceptance Criteria:**
- [ ] SSE endpoint returns streaming response
- [ ] Token events streamed in real-time
- [ ] Tool invocation/result events emitted
- [ ] Done event marks completion
- [ ] Error events for failures
- [ ] Response saved to DynamoDB after stream
- [ ] Headers prevent buffering
- [ ] Unit tests for event generation
- [ ] Integration tests with client

**Dependencies:**
- CHT-005 (FastAPI router)
- CHT-007 (Agent Core Client)

**Testing:**
- Unit: Mock Agent Core events, test generation
- Integration: Real Agent Core, verify streaming
- Frontend: Test with EventSource API (React hook)
- Performance: Verify tokens arrive < 100ms after generation

**Success Metrics:**
- SSE streaming works end-to-end
- Tokens arrive in real-time
- Tool invocations visible during execution
- Response persisted to DynamoDB

---

### TASK-CHT-011: Per-Request Agent Isolation
**Category:** Backend  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 6 hours  
**Complexity:** Medium  

**Description:**
Implement per-request agent instance isolation using FastAPI dependency injection. Prevent deadlocks and state corruption from concurrent requests by creating fresh agent instances.

**Implementation Details:**
- Use FastAPI Depends() pattern for fresh agent creation
- Dependency: `get_agent_for_request() -> AgentExecutor`
  - Creates fresh LangGraph workflow
  - Fresh tools list per request
  - Fresh state management
- Shared resources: Bedrock client (stateless), DynamoDB client
- Per-request: Agent workflow, message history, tool handlers
- Concurrency: Support 100+ simultaneous users without deadlock
- Document architecture decision and concurrency model

**Files to Create/Modify:**
- `backend/app/dependencies.py` (get_agent_for_request)
- `backend/app/api/v1/chat/router.py` (use dependency)
- `backend/app/integrations/agent_core_client.py` (review for statelessness)

**Acceptance Criteria:**
- [ ] Per-request agent dependency created
- [ ] Shared resources identified and reused
- [ ] Fresh instances created per request
- [ ] No global state in agent
- [ ] Unit tests for isolation
- [ ] Concurrency tests (100 concurrent requests)
- [ ] Architecture documented

**Dependencies:**
- CHT-005 (FastAPI router)
- CHT-007 (Agent Core Client)

**Testing:**
- Unit: Verify dependency creates fresh instances
- Concurrency: 100 simultaneous requests, verify no interference
- Isolation: User A's message doesn't appear in User B's response
- Load: Test with realistic load patterns

**Success Metrics:**
- No deadlocks under concurrent load
- Zero cross-user message contamination
- Performance stable (< 1-2ms per instance creation)
- Horizontal scaling works (no sticky sessions)

---

### TASK-CHT-012: Chatbot Page Component
**Category:** Frontend  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 10 hours  
**Complexity:** Medium  

**Description:**
Create main Chatbot page with split layout: session list sidebar and chat interface. Manage session creation, selection, and display.

**Implementation Details:**
- Create `frontend/src/pages/ChatbotPage.tsx`
- Layout: two-column (sidebar + main)
  - Left sidebar: session list (280px)
  - Right main: chat interface (flex 1)
- Sidebar features:
  - "New Chat" button
  - Session list with preview
  - Active session highlight
  - Recent/All sort toggle
- Main area:
  - ChatInterface component (or welcome)
  - Handles message streaming
- State management: React hooks + API calls
- Responsive: Single column on mobile (sidebar collapses)

**Files to Create/Modify:**
- `frontend/src/pages/ChatbotPage.tsx` (new)
- `frontend/src/hooks/useChatSessions.ts` (sessions API hook)
- `frontend/src/components/SessionSidebar.tsx` (new)
- `frontend/src/components/ChatInterface.tsx` (reuse/create)

**Acceptance Criteria:**
- [ ] Page layout renders correctly
- [ ] Session list fetches and displays
- [ ] "New Chat" creates session
- [ ] Session selection works
- [ ] Chat interface loads with selected session
- [ ] Responsive on mobile/tablet/desktop
- [ ] Loading and error states handled
- [ ] Unit tests for components
- [ ] Integration tests with mock API

**Dependencies:**
- Design system (colors, fonts)
- CHT-005 (chat endpoints)

**Testing:**
- Component: Unit tests for layout and state
- Integration: Mock API responses
- E2E: Create session, send message, receive response
- Responsive: Test on mobile (375px), tablet (768px), desktop (1920px)

**Success Metrics:**
- Chatbot page loads and displays sessions
- New chat creation works
- Chat interface accessible from session list
- Responsive on all screen sizes

---

### TASK-CHT-013: Chat Interface Component
**Category:** Frontend  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 12 hours  
**Complexity:** Medium  

**Description:**
Create reusable ChatInterface component for message display, user input, and streaming response handling. Integrate SSE listener and real-time token rendering.

**Implementation Details:**
- Create `frontend/src/components/ChatInterface.tsx`
- Features:
  - Messages container (scrollable, auto-scroll to bottom)
  - Individual message rendering (user/assistant/tool/error)
  - Input textarea with auto-resize
  - Send button (disabled while loading)
  - Cancel button (during streaming)
  - Tool invocation indicators
- Message components:
  - User message: right-aligned, blue bubble
  - Assistant message: left-aligned, translucent bubble
  - Tool message: special styling with tool name/status
  - Error message: red styling with error text
- Streaming handling:
  - SSE listener from useStreamChat hook
  - Append tokens to current message in real-time
  - Show tool invocations as they happen
- Markdown rendering for assistant messages
- Copy message to clipboard functionality

**Files to Create/Modify:**
- `frontend/src/components/ChatInterface.tsx` (new)
- `frontend/src/components/ChatMessage.tsx` (message renderer)
- `frontend/src/hooks/useStreamChat.ts` (SSE streaming hook)
- `frontend/src/styles/chat-interface.css`

**Acceptance Criteria:**
- [ ] Messages display correctly (user/assistant/tool/error)
- [ ] Streaming tokens append in real-time
- [ ] Tool invocations shown during execution
- [ ] Auto-scroll to bottom working
- [ ] Markdown rendering in messages
- [ ] Copy to clipboard working
- [ ] Responsive layout on mobile
- [ ] Keyboard accessible (Tab, Enter to send)
- [ ] Unit tests for message rendering
- [ ] Integration tests with mock streaming

**Dependencies:**
- CHT-010 (SSE streaming)
- Design system (colors, fonts)

**Testing:**
- Component: Unit tests for rendering logic
- Streaming: Mock SSE events, verify display
- Accessibility: Keyboard navigation testing
- Responsive: Mobile/tablet/desktop testing

**Success Metrics:**
- Messages render correctly
- Streaming tokens appear in real-time
- Tool invocations visible
- Mobile layout functional

---

### TASK-CHT-014: Session Management UI
**Category:** Frontend  
**Feature:** Chatbot  
**Priority:** Medium  
**Effort:** 8 hours  
**Complexity:** Low  

**Description:**
Implement session management features: create/list/delete/archive sessions, rename sessions, export conversations, and search sessions.

**Implementation Details:**
- SessionList component: list sessions with pagination
  - Sort: recent, oldest, title (A-Z)
  - Search: filter by title/preview text
  - Session actions: archive, delete, export
- SessionCard component: individual session display
  - Title, preview, last message time
  - Hover: show action buttons (archive, export, delete)
- CreateSessionModal: form to create new session
  - Title input (optional, auto-generate from first message)
  - Submit/Cancel buttons
- ExportDialog: export conversation as JSON/PDF
  - Format selector
  - Download button
- DeleteConfirmation: confirm before deleting session
- API integration: call chat endpoints

**Files to Create/Modify:**
- `frontend/src/components/SessionList.tsx` (extend)
- `frontend/src/components/SessionCard.tsx` (new)
- `frontend/src/components/CreateSessionModal.tsx` (new)
- `frontend/src/components/ExportDialog.tsx` (new)
- `frontend/src/hooks/useChatSessions.ts` (extend)

**Acceptance Criteria:**
- [ ] Sessions list with sorting/search
- [ ] Create session dialog working
- [ ] Archive session functionality
- [ ] Delete with confirmation
- [ ] Export as JSON working
- [ ] Export as PDF working
- [ ] Responsive design
- [ ] Unit tests for components
- [ ] Integration tests with API

**Dependencies:**
- CHT-005 (session endpoints)

**Testing:**
- Component: Unit tests for list/create/delete
- Integration: Test with mock API
- E2E: Create session, export, archive, delete

**Success Metrics:**
- All session management features working
- Export creates downloadable files
- Delete requires confirmation
- Search filters sessions correctly

---

### TASK-CHT-015: SSE Event Listener Hook
**Category:** Frontend  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 6 hours  
**Complexity:** Medium  

**Description:**
Create custom React hook for SSE (Server-Sent Events) streaming. Handle connection, event parsing, disconnection, and error recovery. Provide messages state and send function.

**Implementation Details:**
- Create `frontend/src/hooks/useStreamChat.ts`
- Hook interface:
  - `messages`: ChatMessage[]
  - `isLoading`: boolean
  - `error`: string | null
  - `sendMessage(sessionId, userMessage)`: async
  - `cancelMessage()`: abort current stream
- Event parsing:
  - token: append to current message
  - tool_invocation: add tool message
  - tool_result: update tool status
  - done: mark complete
  - error: set error state
- Error handling:
  - Network errors: show to user
  - Timeout: auto-retry with backoff
  - AbortError: cancel button handling
- Connection management:
  - AbortController for cancellation
  - Cleanup on unmount
  - Reconnection on failure

**Files to Create/Modify:**
- `frontend/src/hooks/useStreamChat.ts` (new)
- `frontend/src/types/chat.ts` (message types)

**Acceptance Criteria:**
- [ ] Hook parses all SSE event types
- [ ] Messages state updates correctly
- [ ] Streaming tokens append in real-time
- [ ] Tool invocations and results tracked
- [ ] Error handling for network issues
- [ ] Cancel functionality working
- [ ] Memory cleanup on unmount
- [ ] Unit tests for event parsing
- [ ] Integration tests with real API

**Dependencies:**
- CHT-010 (SSE endpoint)

**Testing:**
- Unit: Mock fetch/EventSource, test parsing
- Integration: Real API, verify streaming
- Error: Simulate connection failures
- Cleanup: Verify no memory leaks

**Success Metrics:**
- Hook parses all event types correctly
- Messages update in real-time
- Errors handled gracefully
- No memory leaks

---

### TASK-CHT-016: Liquid Glass Styling
**Category:** Frontend  
**Feature:** Chatbot  
**Priority:** Medium  
**Effort:** 8 hours  
**Complexity:** Low  

**Description:**
Apply liquid glass design to chatbot UI. Create CSS styles for cards, containers, and interactive elements with blur effects, transparency, and hover animations.

**Implementation Details:**
- Create `frontend/src/styles/liquid-glass.css`
- Base liquid glass style:
  - `background: rgba(255, 255, 255, 0.1)`
  - `backdrop-filter: blur(20px)`
  - `border: 1px solid rgba(255, 255, 255, 0.2)`
  - `border-radius: 20px`
  - `box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1)`
- Component variations:
  - `.chatbot-sidebar`: sidebar with blur
  - `.chat-message`: message bubbles with glass effect
  - `.chat-input`: input area with glass effect
  - `.tool-indicator`: tool status badges
- Hover effects:
  - `.message-content:hover`: slight elevation, increased blur
  - `.session-item:hover`: background brighten
- Dark mode support:
  - Darker colors for dark mode
  - Adjusted opacity for readability
- Animations:
  - Slide in: messages appear with animation
  - Fade in: typing indicator
  - Pulse: tool executing indicator

**Files to Create/Modify:**
- `frontend/src/styles/liquid-glass.css` (new)
- `frontend/src/styles/chatbot.css` (overall theme)
- Component CSS files (integrate liquid-glass)

**Acceptance Criteria:**
- [ ] Liquid glass effects applied to all components
- [ ] Blur effect visible and smooth
- [ ] Hover effects working
- [ ] Dark mode supported
- [ ] Animations smooth (60 FPS)
- [ ] Cross-browser compatible
- [ ] Mobile optimized (reduced blur if needed)
- [ ] Visual review by design team

**Dependencies:**
- Design system (colors)

**Testing:**
- Visual: Screenshot comparison desktop/mobile/dark
- Performance: Verify 60 FPS animations
- Browser: Test on Chrome, Firefox, Safari, Edge

**Success Metrics:**
- Liquid glass effect visible and polished
- All animations smooth
- Dark mode matches light mode aesthetic
- Cross-browser compatible

---

### TASK-CHT-017: Auth & Session Validation
**Category:** Backend  
**Feature:** Chatbot  
**Priority:** High  
**Effort:** 6 hours  
**Complexity:** Medium  

**Description:**
Implement authentication and session validation for chat endpoints. Verify JWT tokens, validate user ownership of sessions, prevent unauthorized access.

**Implementation Details:**
- Use existing JWT auth from project
- Add `get_current_user` dependency to chat endpoints
- Session validation: verify user_id matches session owner
- Message validation: verify user_id matches session owner
- Error responses:
  - 401: Missing/invalid auth token
  - 403: User not authorized to access session
  - 404: Session not found (or doesn't belong to user)
- Add auth checks to all endpoints:
  - POST /api/v1/chat/message
  - GET /api/v1/chat/sessions
  - POST /api/v1/chat/sessions
  - GET /api/v1/chat/sessions/{session_id}
- Logging: log auth failures for security monitoring

**Files to Create/Modify:**
- `backend/app/api/v1/chat/router.py` (add auth checks)
- `backend/app/dependencies.py` (extend get_current_user)
- `backend/app/services/chat_service.py` (add auth validation)

**Acceptance Criteria:**
- [ ] JWT tokens validated on all endpoints
- [ ] User ownership validated for sessions
- [ ] Correct error responses (401, 403, 404)
- [ ] Logging for security events
- [ ] Unit tests for auth logic
- [ ] Integration tests with valid/invalid tokens
- [ ] Cross-user access prevented

**Dependencies:**
- Existing JWT auth system

**Testing:**
- Unit: Mock auth, test validation logic
- Unit: Test 401/403/404 responses
- Integration: Real JWT tokens, test access control
- Security: Try to access other user's session (should fail)

**Success Metrics:**
- Unauthorized requests return 401
- Cross-user access blocked (403)
- Valid users access own sessions
- Auth failures logged

---

### TASK-CHT-018: Error Handling & Recovery
**Category:** Backend  
**Feature:** Chatbot  
**Priority:** Medium  
**Effort:** 6 hours  
**Complexity:** Medium  

**Description:**
Implement comprehensive error handling and recovery strategies for chat operations. Handle network failures, timeouts, invalid inputs, and resource constraints gracefully.

**Implementation Details:**
- Error categories:
  - Input validation: invalid session_id, empty message
  - Auth errors: unauthorized user, invalid token
  - Network errors: Agent Core unreachable
  - Timeout: response takes > 60 seconds
  - Resource errors: DynamoDB throttling, rate limits
- Error responses:
  - 400: Bad request (validation)
  - 401: Unauthorized
  - 403: Forbidden
  - 408: Request timeout
  - 429: Too many requests (rate limit)
  - 500: Server error
  - 503: Service unavailable
- Recovery strategies:
  - Retry with exponential backoff (max 3 retries)
  - Circuit breaker for Agent Core failures
  - Graceful degradation (partial response if tool fails)
  - Logging all errors for monitoring
- SSE error events: send error event to client before closing

**Files to Create/Modify:**
- `backend/app/api/v1/chat/router.py` (error handling)
- `backend/app/integrations/agent_core_client.py` (retry logic)
- `backend/app/utils/error_handlers.py` (error utilities)

**Acceptance Criteria:**
- [ ] All error types handled
- [ ] Correct HTTP status codes returned
- [ ] Error messages descriptive (no stack traces to client)
- [ ] Retry logic working (exponential backoff)
- [ ] Circuit breaker functional
- [ ] Error logging for monitoring
- [ ] Unit tests for error scenarios
- [ ] Integration tests with real failures

**Dependencies:**
- CHT-005, CHT-007 (endpoints and client)

**Testing:**
- Unit: Mock failures, test error responses
- Integration: Real failures (stop Agent Core, throttle DynamoDB)
- Recovery: Verify retries work and succeed

**Success Metrics:**
- All errors handled gracefully
- Correct status codes returned
- No unhandled exceptions in logs
- Retry logic successful on transient failures

---

### TASK-CHT-019: End-to-End Testing Chatbot
**Category:** Workflow  
**Feature:** Chatbot  
**Priority:** Medium  
**Effort:** 10 hours  
**Complexity:** Medium  

**Description:**
Comprehensive end-to-end testing of chatbot feature. Test full flows from session creation to message streaming to session archival.

**Implementation Details:**
- Test scenario 1: Create session → send message → receive response
  - Create session via API
  - Send message with SSE
  - Verify tokens stream in real-time
  - Verify message saved to DynamoDB
  - Verify response complete event received
- Test scenario 2: Tool invocation end-to-end
  - Send message triggering semantic search
  - Verify tool_invocation event emitted
  - Verify tool executes and returns results
  - Verify tool_result event with results
  - Verify agent synthesizes response with tool data
- Test scenario 3: Multi-turn conversation
  - Create session
  - Send 5 messages sequentially
  - Verify message history retrieved correctly
  - Verify context flows between turns
- Test scenario 4: Session management
  - Create multiple sessions
  - List sessions (pagination, sorting)
  - Archive session
  - Export conversation
- Test scenario 5: Error recovery
  - Send message, simulate Agent Core failure
  - Verify error event sent to client
  - Verify retry logic kicks in
  - Verify eventual success or graceful failure

**Files to Create/Modify:**
- `backend/tests/e2e/test_chatbot_flow.py` (new)
- `backend/tests/fixtures/chat_data.py` (test data)

**Acceptance Criteria:**
- [ ] All test scenarios pass
- [ ] Streaming tokens verified in real-time
- [ ] Tool invocations work end-to-end
- [ ] Multi-turn conversations work
- [ ] Session management operations work
- [ ] Error recovery tested
- [ ] Data consistency verified
- [ ] Performance within SLAs

**Dependencies:**
- All chatbot tasks complete

**Testing:**
- End-to-end: Run all scenarios sequentially
- Data validation: Verify DynamoDB and Qdrant state
- Performance: Measure streaming latency, response time
- Concurrency: Run multiple concurrent scenarios

**Success Metrics:**
- All test scenarios pass
- Streaming latency < 100ms per token
- Tool invocation latency < 500ms
- Zero data inconsistencies

---

### TASK-CHT-020: Performance & Load Testing
**Category:** Workflow  
**Feature:** Chatbot  
**Priority:** Medium  
**Effort:** 8 hours  
**Complexity:** Medium  

**Description:**
Performance and load testing for chatbot. Verify response times, throughput, and stability under realistic load (100+ concurrent users).

**Implementation Details:**
- Load test scenarios:
  - Scenario 1: 10 concurrent users, 1 message per user
    - Measure: response time p50, p95, p99
    - Target: p95 < 3 seconds
  - Scenario 2: 50 concurrent users, sustained 1 msg/second
    - Measure: throughput, error rate, tail latency
    - Target: < 0.1% errors, p99 < 5 seconds
  - Scenario 3: 100 concurrent users, ramp-up over 5 minutes
    - Measure: auto-scaling response, stability
    - Target: maintain p95 < 5 seconds
  - Scenario 4: 10 users with multi-turn conversations (5 messages each)
    - Measure: memory usage, connection stability
- Tools: Apache JMeter or Locust
- Metrics to track:
  - Response time (min, max, avg, p50, p95, p99)
  - Throughput (req/sec)
  - Error rate (%)
  - CPU/memory usage
  - Agent Core task queue depth

**Files to Create/Modify:**
- `backend/tests/load/chatbot_load_test.py` (load test script)
- `backend/tests/load/locustfile.py` (Locust config)

**Acceptance Criteria:**
- [ ] Load test script created
- [ ] All scenarios executed
- [ ] Metrics collected and documented
- [ ] Performance targets met (p95 < 3-5 seconds)
- [ ] Error rate < 0.1%
- [ ] Auto-scaling works correctly
- [ ] No memory leaks detected
- [ ] Results documented in report

**Dependencies:**
- CHT-019 (E2E testing)

**Testing:**
- Load: Run scenarios with increasing concurrency
- Monitoring: Watch CloudWatch during load test
- Analysis: Compare p95/p99 percentiles

**Success Metrics:**
- p95 response time < 3 seconds (100 users)
- Error rate < 0.1%
- Auto-scaling scales correctly
- No timeouts or connection drops

---

### TASK-CHT-021: Chatbot Documentation
**Category:** Workflow  
**Feature:** Chatbot  
**Priority:** Low  
**Effort:** 4 hours  
**Complexity:** Low  

**Description:**
Comprehensive documentation for chatbot feature. API docs, architecture guide, deployment guide, troubleshooting, and user guide.

**Implementation Details:**
- Create `docs/chatbot/API.md` - OpenAPI with examples
- Create `docs/chatbot/ARCHITECTURE.md` - system design, LangChain/LangGraph overview
- Create `docs/chatbot/DEPLOYMENT.md` - step-by-step deployment
- Create `docs/chatbot/TROUBLESHOOTING.md` - 15+ common issues
- Create `docs/chatbot/USER_GUIDE.md` - how to use chatbot
- Generate Swagger UI from FastAPI
- Update main README.md with chatbot section
- Add architecture diagrams (Mermaid)

**Files to Create/Modify:**
- `docs/chatbot/API.md` (new)
- `docs/chatbot/ARCHITECTURE.md` (new)
- `docs/chatbot/DEPLOYMENT.md` (new)
- `docs/chatbot/TROUBLESHOOTING.md` (new)
- `docs/chatbot/USER_GUIDE.md` (new)
- `README.md` (update)

**Acceptance Criteria:**
- [ ] All docs created and reviewed
- [ ] API docs include all endpoints
- [ ] Architecture explains LangChain/LangGraph
- [ ] Deployment guide tested
- [ ] Troubleshooting covers 15+ issues
- [ ] User guide explains features
- [ ] Swagger UI generated
- [ ] Diagrams included

**Dependencies:**
- All chatbot tasks complete

**Testing:**
- Review: Technical review
- Validation: Follow deployment guide, it works
- Completeness: All features documented

**Success Metrics:**
- Docs complete and accurate
- Deployment guide tested successfully
- No broken links or incomplete sections

---

## Task Dependencies & Critical Path

**Critical Path (must complete in order):**

1. **Week 1-2 Infrastructure (Foundational)**
   - CLU-001 → CLU-002 (embeddings need table)
   - CHT-001 → CHT-006 (DynamoDB needed for service)
   - CHT-002 → CHT-003 (ECS before IAM)

2. **Week 2-3 Core Features (Blocking)**
   - CLU-003 ← CLU-002 (clustering needs embeddings)
   - CLU-004 ← CLU-003 (task needs clustering logic)
   - CHT-007 ← CHT-002 (client needs Agent Core)
   - CHT-008 ← CHT-007 (tool needs client)

3. **Week 3-4 APIs & Integration (Serial)**
   - CLU-012 ← CLU-004 (API needs data)
   - CLU-013 ← CLU-008 (admin endpoints need evaluation)
   - CHT-009 ← CHT-008 (registration needs tool)
   - CHT-010 ← CHT-007 (streaming needs client)

4. **Week 4-5 Frontend**
   - CLU-014 ← CLU-012 (page needs API)
   - CHT-012 ← CHT-005 (page needs endpoints)
   - CHT-013 ← CHT-010 (interface needs streaming)

5. **Week 5-6 Testing & Deployment**
   - CLU-019 ← All CLU tasks (E2E needs everything)
   - CHT-019 ← All CHT tasks (E2E needs everything)
   - CLU-020, CHT-021 (docs after testing)

**Non-blocking Parallel Work:**
- CLU-005, CLU-006, CLU-007 (metrics) can run in parallel
- CHT-004 (memory) while building core features
- CLU-017, CHT-002, CHT-003 (infrastructure) in parallel
- Frontend styling (CHT-016, CLU-015) while APIs build

**Dependency Graph (simplified):**
```
CLU-001 → CLU-002 → CLU-003 → CLU-004 → CLU-012 → CLU-014
   ↓
CLU-005, CLU-006, CLU-007 ↘
                             CLU-008 → CLU-009 → CLU-013
                                        ↓
                                      CLU-010, CLU-011

CHT-001 → CHT-006 → CHT-005 → CHT-012 ← CHT-013 ← CHT-010 ← CHT-007
   ↓                                                           ↑
CHT-002 → CHT-003 → CHT-004 ────→ CHT-009 ↗                  CHT-008
                                                               ↑
                                                            CHT-001
```

---

## Effort Summary by Category

| Category | Clustering | Chatbot | Total | % of Total |
|----------|-----------|---------|-------|-----------|
| **Backend** | 50h | 68h | 118h | 39% |
| **Frontend** | 30h | 46h | 76h | 25% |
| **ML** | 16h | 0h | 16h | 5% |
| **Infrastructure** | 20h | 16h | 36h | 12% |
| **Workflow** | 24h | 22h | 46h | 15% |
| **TOTAL** | 140h | 152h | **292h** | 100% |

**Total Effort: 240-300 hours (8-10 weeks)**

**Team Recommendation:**
- 2 backend engineers (full-time): 4-5 weeks
- 1-2 frontend engineers (full-time): 4-5 weeks
- 1 ML/data engineer: 2 weeks (clustering metrics)
- 1 infrastructure/DevOps: 2 weeks (Terraform, monitoring)
- Overlap parallelization: compress to 6-8 weeks with 4-5 people

---

## Sprint Planning Guide

### Sprint 1 (Week 1-2): 56 hours
**Backend Foundation**
- CLU-001, CLU-002 (clustering tables, embeddings)
- CHT-001, CHT-002, CHT-003 (chat tables, Agent Core, IAM)

**Infrastructure**
- CLU-017 (Terraform for clustering)
- CHT-002, CHT-003 (verified working)

**Goal:** All data stores and infrastructure ready

### Sprint 2 (Week 2-3): 68 hours
**Clustering Core**
- CLU-003, CLU-004 (HDBSCAN, Celery task)
- CLU-005, CLU-006, CLU-007 (metrics)

**Chatbot Core**
- CHT-005, CHT-006, CHT-007 (FastAPI, service, client)
- CHT-004 (Agent Core Memory)

**Goal:** Clustering pipeline and chat endpoints working

### Sprint 3 (Week 3-4): 60 hours
**Evaluation & Admin**
- CLU-008, CLU-009, CLU-010, CLU-011 (evaluation pipeline, weights, viz)
- CLU-012, CLU-013 (cluster APIs, admin endpoints)

**Tool Integration**
- CHT-008, CHT-009 (semantic search tool, registration)
- CHT-010, CHT-011 (SSE streaming, agent isolation)

**Goal:** APIs functional, tools integrated, evaluation working

### Sprint 4 (Week 4-5): 52 hours
**Frontend**
- CLU-014, CLU-015, CLU-016 (topics page, cards, detail view)
- CHT-012, CHT-013, CHT-014, CHT-015, CHT-016 (UI components, styling)

**Supporting**
- CHT-017 (auth/validation)

**Goal:** User-facing UI complete

### Sprint 5 (Week 5-6): 48 hours
**Testing & Polish**
- CLU-018, CLU-019, CLU-020 (monitoring, E2E, docs)
- CHT-018, CHT-019, CHT-020, CHT-021 (error handling, E2E, load test, docs)

**Goal:** Production-ready, tested, documented

---

## Quick Reference: Status & Blockers

| Task | Owner | Status | Blocked By | Blocks |
|------|-------|--------|-----------|--------|
| CLU-001 | Backend | Not Started | None | CLU-002, CLU-017 |
| CLU-002 | Backend | Not Started | CLU-001 | CLU-003, CLU-004 |
| CLU-003 | Backend | Not Started | CLU-002 | CLU-004, CLU-005/6/7 |
| CLU-004 | Backend | Not Started | CLU-003 | CLU-012 |
| CLU-005 | ML | Not Started | None | CLU-008 |
| CLU-006 | ML | Not Started | None | CLU-008 |
| CLU-007 | ML | Not Started | None | CLU-008 |
| CLU-008 | Backend | Not Started | CLU-005/6/7, CLU-009 | CLU-010/11/13 |
| CLU-009 | Infra | Not Started | None | CLU-008 |
| CLU-010 | Backend | Not Started | None | CLU-008 |
| CLU-011 | Backend | Not Started | CLU-008 | CLU-013 |
| CLU-012 | Backend | Not Started | CLU-004 | CLU-014, CLU-013 |
| CLU-013 | Backend | Not Started | CLU-012, CLU-008 | CLU-020 |
| CLU-014 | Frontend | Not Started | CLU-012 | CLU-019 |
| CLU-015 | Frontend | Not Started | None | CLU-014 |
| CLU-016 | Frontend | Not Started | CLU-012 | CLU-019 |
| CLU-017 | Infra | Not Started | None | CLU-004, CLU-018 |
| CLU-018 | DevOps | Not Started | CLU-017, CLU-004 | CLU-019 |
| CLU-019 | QA | Not Started | All CLU | CLU-020 |
| CLU-020 | Docs | Not Started | CLU-019 | None |
| CHT-001 | Backend | Not Started | None | CHT-006 |
| CHT-002 | Infra | Not Started | None | CHT-003, CHT-007 |
| CHT-003 | Infra | Not Started | CHT-002 | CHT-007 |
| CHT-004 | Backend | Not Started | None | CHT-007 |
| CHT-005 | Backend | Not Started | CHT-001 | CHT-012 |
| CHT-006 | Backend | Not Started | CHT-001 | CHT-005 |
| CHT-007 | Backend | Not Started | CHT-002/3, CHT-004 | CHT-008/10/11 |
| CHT-008 | Backend | Not Started | None | CHT-009 |
| CHT-009 | Backend | Not Started | CHT-007, CHT-008 | CHT-019 |
| CHT-010 | Backend | Not Started | CHT-007 | CHT-013, CHT-015 |
| CHT-011 | Backend | Not Started | CHT-007 | CHT-019 |
| CHT-012 | Frontend | Not Started | CHT-005 | CHT-019 |
| CHT-013 | Frontend | Not Started | CHT-010 | CHT-019 |
| CHT-014 | Frontend | Not Started | CHT-005 | None |
| CHT-015 | Frontend | Not Started | CHT-010 | CHT-013 |
| CHT-016 | Frontend | Not Started | None | CHT-013 |
| CHT-017 | Backend | Not Started | CHT-005 | CHT-019 |
| CHT-018 | Backend | Not Started | None | CHT-019 |
| CHT-019 | QA | Not Started | All CHT | CHT-021 |
| CHT-020 | QA | Not Started | CHT-019 | None |
| CHT-021 | Docs | Not Started | CHT-019 | None |

---

## Hand-Off Checklist for Developers

When picking up a task, verify:

- [ ] Read task description completely
- [ ] Check all dependencies (blockers) are complete
- [ ] Review Acceptance Criteria before starting
- [ ] Check Success Metrics to understand quality bar
- [ ] Read implementation details for approach
- [ ] Create feature branch from main
- [ ] Write unit tests first (TDD)
- [ ] Implement feature
- [ ] Update acceptance criteria checklist
- [ ] Test with provided test cases
- [ ] Get code review
- [ ] Merge to main
- [ ] Update task status to "Complete"

---

This consolidated TASKS.md file provides a complete, detailed roadmap for implementing both clustering and chatbot features. Each task is self-contained with clear success criteria, enabling developers to pick up any task and run with it.
