# Test Embeddings Pipeline - May 30, 2026

## ✅ What Was Fixed
- **Broken**: Fire-and-forget asyncio tasks → cancelled before completion
- **Fixed**: Celery worker tasks → guaranteed completion with auto-retry

## 🚀 Quick Start (5 Steps)

### 1. **Restart Celery Worker** (fresh import)
```bash
cd /mnt/d/FPT/Demo/Tech-News-Mystery/backend
source venv_wsl/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 --max-tasks-per-child=5
```

**Watch for**:
```
[tasks]
  . app.workers.tasks.embedding_tasks.index_article_task
  . app.workers.tasks.embedding_tasks.delete_embedding_task
  . app.workers.tasks.embedding_tasks.backfill_embeddings_task
```

### 2. **Backfill All Existing Articles**
```bash
curl -X POST http://localhost:8000/v1/admin/clustering/evaluations/backfill-embeddings \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected response**:
```json
{
  "task_id": "abc123...",
  "status": "queued",
  "message": "Backfill task queued. Check logs for progress."
}
```

**Check backend logs**:
```
[BACKFILL] Starting embeddings backfill for all articles
[BACKFILL] Found 97 articles in DynamoDB, indexing...
[EMBEDDING] Starting indexing for article <id>
[EMBEDDING] ✅ Article <id> indexed successfully to Qdrant
...
[BACKFILL] ✅ Completed: 97/97 articles indexed
```

⏱️ **Wait 2-5 minutes for backfill to complete**

### 3. **Test Create New Article**
```bash
# Create new article (queue approves it auto)
# Go to Topics → Queue → Find article with ✅

# Check backend logs for:
[EMBEDDING] Queued indexing task for article <new-id>
[EMBEDDING] ✅ Article <new-id> indexed successfully to Qdrant
```

### 4. **Test Update Article**
```bash
# Edit article (change title, summary, etc)
# Save changes

# Check backend logs for:
[EMBEDDING] Queued indexing task for article <id>
[EMBEDDING] ✅ Article <id> indexed successfully to Qdrant
```

### 5. **Test Delete Article**
```bash
# Delete article from Topics page or admin panel

# Check backend logs for:
[EMBEDDING] Queued deletion task for article <id>
[EMBEDDING] ✅ Embedding deleted for article <id>
```

---

## 📊 Verify Qdrant Collection

After backfill + tests, check collection size:
```
Before backfill: 13 points
After backfill: 97 points ✅
After +1 new article: 98 points ✅
After +1 delete: 97 points ✅
```

---

## 🎯 Retrigger Clustering

Once backfill is done and Qdrant has ~97 articles:

**Go to Topics page → Admin menu → Retrigger Clustering**

**Expected logs**:
```
Qdrant vector fetch: requested=97 found=97 ✅
K range: [5, 10] ✅
Silhouette scores: [0.65, 0.72, 0.68, ...]
Best K: 7 (silhouette=0.72) ✅
Clustering evaluation completed successfully
```

**PCA visualization** should now display all clusters with proper analysis.

---

## 🧪 Test Commands

### Monitor Task Queue
```bash
# Terminal with celery worker running:
celery -A app.workers.celery_app inspect active
```

### View Backfill Status
```bash
# Check task result (from Task ID above)
celery -A app.workers.celery_app inspect result <task_id>
```

### Test Single Article Indexing
```bash
# Curl create article endpoint
curl -X POST http://localhost:8000/v1/articles \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Article",
    "content": "Test content here",
    "category": "tech",
    "summary": "Test summary"
  }'

# Response: Article saved
# Watch logs for: [EMBEDDING] ✅ Article ... indexed successfully to Qdrant
```

---

## ✅ Checklist

- [ ] Celery worker started with embedding tasks registered
- [ ] Backfill endpoint called and task queued
- [ ] Wait 2-5 min, check logs for "Completed: 97/97"
- [ ] Create new article, verify embedding logged
- [ ] Update article, verify embedding re-indexed
- [ ] Delete article, verify embedding deleted
- [ ] Qdrant collection has ~97+ articles
- [ ] Retrigger clustering from Topics page
- [ ] Check logs: "requested=97 found=97 ✅"
- [ ] PCA visualization displays all clusters

---

## 🚨 Troubleshooting

**No embedding logs?**
- Celery worker not running → restart with fresh Python import
- Task not queued → check if embedding_tasks imported in celery_app.py

**Backfill shows "failed" items?**
- Check backend logs for specific error
- Rerun backfill endpoint to retry failed articles

**Qdrant still shows <97?**
- Wait for backfill to complete (check logs)
- Some articles may have empty content (skip during indexing)
- Check embedding_tasks.py for exception handling

**Clustering still fails?**
- Need >25 articles in Qdrant for K selection
- If <25, manually create more articles
- Check K range constraints: [5, 10]

---

**Status**: Ready to test 🚀
