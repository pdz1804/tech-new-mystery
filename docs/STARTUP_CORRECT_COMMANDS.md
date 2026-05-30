# Tech News Mystery - Correct Startup Commands

## 🚀 5 Services - Exact Commands You Used Before

---

## **Terminal 1: Backend (Uvicorn)**
```bash
cd /mnt/d/FPT/Demo/Tech-News-Mystery/backend
source venv_wsl/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## **Terminal 2: Agent Core Server**
```bash
cd /mnt/d/FPT/Demo/Tech-News-Mystery/backend
source venv_wsl/bin/activate
python -m agent_core.server
```

**Expected**:
```
Agent Core server running on port 8080
```

---

## **Terminal 3: Celery Worker**
```bash
cd /mnt/d/FPT/Demo/Tech-News-Mystery/backend
source venv_wsl/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 --max-tasks-per-child=5
```

**Expected**:
```
celery@ubuntu-hostname ready.
[tasks]
  . app.workers.tasks.clustering_tasks.cluster_articles
  ...
```

---

## **Terminal 4: Celery Beat (Scheduler)**
```bash
cd /mnt/d/FPT/Demo/Tech-News-Mystery/backend
source venv_wsl/bin/activate
celery -A app.workers.celery_app beat --loglevel=info
```

**Expected**:
```
celery beat v5.x.x is starting.
```

---

## **Terminal 5: Frontend (Next.js)**
```bash
cd /mnt/d/FPT/Demo/Tech-News-Mystery/frontend
npm run dev
```

**Expected**:
```
ready - started server on 0.0.0.0:3000, url: http://localhost:3000
```

---

## ✅ All 5 Commands Together (Copy-Paste)

### **Terminal 1 - Backend:**
```bash
cd /mnt/d/FPT/Demo/Tech-News-Mystery/backend && source venv_wsl/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### **Terminal 2 - Agent Core:**
```bash
cd /mnt/d/FPT/Demo/Tech-News-Mystery/backend && source venv_wsl/bin/activate && python -m agent_core.server
```

### **Terminal 3 - Celery Worker:**
```bash
cd /mnt/d/FPT/Demo/Tech-News-Mystery/backend && source venv_wsl/bin/activate && celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 --max-tasks-per-child=5
```

### **Terminal 4 - Celery Beat:**
```bash
cd /mnt/d/FPT/Demo/Tech-News-Mystery/backend && source venv_wsl/bin/activate && celery -A app.workers.celery_app beat --loglevel=info
```

### **Terminal 5 - Frontend:**
```bash
cd /mnt/d/FPT/Demo/Tech-News-Mystery/frontend && npm run dev
```

---

## 🚀 One-Command Concurrent Startup (All 5 Services)

```bash
cd /mnt/d/FPT/Demo/Tech-News-Mystery && \
source backend/venv_wsl/bin/activate && \
(cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | sed 's/^/[BACKEND] /') & \
(cd backend && python -m agent_core.server 2>&1 | sed 's/^/[AGENT] /') & \
(cd backend && celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 --max-tasks-per-child=5 2>&1 | sed 's/^/[WORKER] /') & \
(cd backend && celery -A app.workers.celery_app beat --loglevel=info 2>&1 | sed 's/^/[BEAT] /') & \
(cd frontend && npm run dev 2>&1 | sed 's/^/[FRONTEND] /') & \
echo "" && \
echo "✅ All 5 services started!" && \
echo "" && \
echo "🌐 Open: http://localhost:3000" && \
echo "" && \
echo "📊 Services:" && \
echo "   [BACKEND]   Backend API (port 8000)" && \
echo "   [AGENT]     Agent Core (port 8080)" && \
echo "   [WORKER]    Celery Worker (concurrency=2)" && \
echo "   [BEAT]      Celery Beat Scheduler" && \
echo "   [FRONTEND]  Frontend (port 3000)" && \
echo "" && \
echo "🛑 Press Ctrl+C to stop all services" && \
echo "" && \
wait
```

---

## 📊 Service Ports & URLs

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| Backend Docs | 8000 | http://localhost:8000/docs |
| Agent Core | 8080 | http://localhost:8080 |
| Frontend | 3000 | http://localhost:3000 |
| Chat | 3000 | http://localhost:3000/chat |
| Topics | 3000 | http://localhost:3000/topics |

---

## 🛑 Stop All Services

**Press Ctrl+C** in the terminal where you ran the one-command startup

Or in separate terminal:
```bash
pkill -f uvicorn
pkill -f agent_core
pkill -f "celery worker"
pkill -f "celery beat"
pkill -f "npm run dev"
```

---

## 🧹 Memory Cleanup Before Starting

```bash
# Free up memory
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# Check memory
free -h
```

---

## ✅ Health Checks

```bash
# Check Backend
curl http://localhost:8000/v1/articles

# Check Agent Core
curl http://localhost:8080

# Check Frontend
curl http://localhost:3000

# Check Celery Worker
celery -A app.workers.celery_app inspect active
```

---

## 📝 Notes

- **0.0.0.0** instead of 127.0.0.1 = accessible from other machines on network
- **--concurrency=2** = 2 parallel workers (adjust based on memory)
- **--max-tasks-per-child=5** = worker recycles after 5 tasks (prevents memory leaks)
- **beat** = scheduler for running tasks at scheduled times
- **agent_core.server** = local Agent Core (not Docker)

---

## 🚨 If Worker Crashes

If you see `SIGKILL` errors with `--concurrency=2`, reduce to 1:

```bash
celery -A app.workers.celery_app worker --loglevel=info --concurrency=1 --max-tasks-per-child=5
```

Or use solo pool:
```bash
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

---

**Last Updated**: May 30, 2026  
**Commands Verified**: User-provided exact commands
