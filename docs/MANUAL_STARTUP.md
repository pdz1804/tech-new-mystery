# Tech News Mystery - Manual Startup Guide

**For local development with manual terminal control**

---

## Prerequisites

- Python 3.11+ installed
- Node.js 18+ installed
- Docker running (for Redis only)
- AWS credentials configured
- Git repository cloned

---

## Test Accounts (For Development/Testing)

**Admin Account:**
- Username: `admin`
- Email: `admin@example.com`
- Password: `admin123`
- Role: admin (can create/manage articles, search, manage users)

**User Account:**
- Username: `testuser`
- Email: `user@example.com`
- Password: `user123`
- Role: user (can create/manage own articles, engage)

These accounts will be created automatically when you run the backend initialization script.

---

## Step 1: Start Redis (Docker)

**Terminal 1 - Redis**

```bash
cd infra
docker-compose up redis
```

Wait for output: `Ready to accept connections`

Then keep this terminal open - do NOT close it.

---

## Step 2: Start Backend (Python venv)

**Terminal 2 - Backend**

```bash
cd backend

# Create venv if not exists
python -m venv venv

# Activate venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -e .

# Create DynamoDB tables (if not exists)
python scripts/create_tables_boto3.py

# Create test accounts (admin & testuser)
python scripts/create_test_accounts.py

# Run backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Wait for output: `Application startup complete`

Then keep this terminal open.

**Note:** Test accounts are created automatically if they don't exist. You can now login with:
- Admin: `admin` / `admin123`
- User: `testuser` / `user123`

---

## Step 3: Start Frontend (Node.js)

**Terminal 3 - Frontend**

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Run frontend
npm run dev
```

Wait for output: `▲ Next.js ... ready - started server on 0.0.0.0:3000`

Then keep this terminal open.

---

## Verify Everything Works

```bash
# In a new terminal, test backend health
curl http://localhost:8000/health

# Open frontend in browser
http://localhost:3000
```

---

## Environment Configuration

### Backend .env Setup

File: `backend/.env`

**Current configuration (for local dev):**
```env
# AWS / DynamoDB
AWS_REGION=us-west-2
DYNAMODB_TABLE_PREFIX=tech-news-
ENVIRONMENT=local

# Redis - Points to Docker Redis container
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# LLM
BEDROCK_REGION=us-west-2
BEDROCK_MODEL=anthropic.claude-3-5-haiku-20241022
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Search
TAVILY_API_KEY=tvly-...
```

**To switch to production (AWS ElastiCache):**
```env
ENVIRONMENT=production
REDIS_URL=redis://<elasticache-endpoint>:6379/0
CELERY_BROKER_URL=redis://<elasticache-endpoint>:6379/1
CELERY_RESULT_BACKEND=redis://<elasticache-endpoint>:6379/2
```

---

## Terminal Layout (Recommended)

```
┌─────────────────────────────────────────────────┐
│ Terminal 1: Redis                               │
│ $ docker-compose up redis                       │
├─────────────────────────────────────────────────┤
│ Terminal 2: Backend                             │
│ $ uvicorn app.main:app --reload                │
├─────────────────────────────────────────────────┤
│ Terminal 3: Frontend                            │
│ $ npm run dev                                   │
├─────────────────────────────────────────────────┤
│ Terminal 4: Commands & Testing                  │
│ $ curl http://localhost:8000/health             │
│ $ git status, npm test, pytest, etc.            │
└─────────────────────────────────────────────────┘
```

---

## Common Commands (Terminal 4)

### Test Backend

```bash
cd backend
set PYTHONPATH=.
python -m pytest tests/ -v
```

### Test Specific Module

```bash
python -m pytest tests/test_auth_service.py -v
```

### Check Backend Health

```bash
curl http://localhost:8000/health
```

### View API Documentation

```bash
# Swagger UI
http://localhost:8000/docs

# ReDoc
http://localhost:8000/redoc
```

### Restart Backend (if needed)

```bash
# Stop: Press Ctrl+C in Terminal 2
# Restart: Run same command again
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Troubleshooting

### Redis Connection Error

**Problem:** Backend can't connect to Redis
```
ConnectionError: Error 111 connecting to redis://redis:6379/0
```

**Solution:**
```bash
# Check Redis is running in Terminal 1
# If not, start it:
cd infra
docker-compose up redis

# Wait for "Ready to accept connections"
```

### Port Already in Use

**Problem:** "Address already in use"

**Solution:**
```bash
# Kill process using port 8000 (backend)
lsof -i :8000
kill -9 <PID>

# Kill process using port 3000 (frontend)
lsof -i :3000
kill -9 <PID>

# Kill process using port 6379 (Redis)
lsof -i :6379
kill -9 <PID>
```

### venv Activation Issues

**Problem:** venv not activating on Windows

**Solution:**
```bash
# Use relative path (from backend directory)
venv\Scripts\activate

# Or use python -m venv instead:
python -m venv venv
venv\Scripts\activate

# Verify activated (should see "(venv)" in prompt)
```

### Module Not Found Error

**Problem:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
```bash
# Make sure PYTHONPATH is set
set PYTHONPATH=.

# Or run from correct directory
cd backend

# Then try again
python -m pytest tests/
```

---

## Stopping Everything

**When you're done developing:**

```bash
# Terminal 1 (Redis): Press Ctrl+C
# Terminal 2 (Backend): Press Ctrl+C
# Terminal 3 (Frontend): Press Ctrl+C

# Clean up Docker
cd infra
docker-compose down
```

---

## Testing User Workflows

### Pre-Created Test Accounts

**Admin Account** (for testing admin features):
```bash
# Terminal 4
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**Regular User Account** (for testing user features):
```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"user123"}'
```

Both accounts are created automatically when backend starts.

### Get Access Token

```bash
# Login as admin
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

echo "Admin token: $ADMIN_TOKEN"

# Or login as user
USER_TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"user123"}' | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

echo "User token: $USER_TOKEN"
```

### Get Current User Info

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/v1/auth/me
```

### Create Article from URL (User Feature)

```bash
curl -X POST http://localhost:8000/v1/articles/from-url \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://techcrunch.com/2026/05/18/sample-article"}'
```

### List Articles

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/v1/articles?limit=10
```

### Admin Search (Tavily) - Admin Feature Only

```bash
curl -X POST http://localhost:8000/v1/admin/search/tavily \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"AI breakthroughs 2026","limit":5}'
```

### Like & Save Articles (User Feature)

```bash
# Like article (use article_id from list response)
curl -X POST http://localhost:8000/v1/articles/{article_id}/like \
  -H "Authorization: Bearer $USER_TOKEN"

# Save article
curl -X POST http://localhost:8000/v1/articles/{article_id}/save \
  -H "Authorization: Bearer $USER_TOKEN"

# Get saved articles
curl -H "Authorization: Bearer $USER_TOKEN" \
  http://localhost:8000/v1/user/saved-articles
```

### Test Role-Based Access Control

```bash
# Only admin can search (should work)
curl -X POST http://localhost:8000/v1/admin/search/tavily \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"test","limit":5}'

# Regular user trying admin search (should get 403 Forbidden)
curl -X POST http://localhost:8000/v1/admin/search/tavily \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"test","limit":5}'
```

---

## IDE Setup

### VS Code

**Recommended extensions:**
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- ES7+ React/Redux/React-Native snippets (dsznajder.es7-react-js-snippets)
- Prettier (esbenp.prettier-vscode)

**Python interpreter:**
```
Select Interpreter > Enter Interpreter Path
backend/venv/Scripts/python.exe (relative to project root)
```

### PyCharm

- Set Python interpreter: Settings → Project → Python Interpreter → Add → Existing Environment
- Select: `backend/venv/Scripts/python.exe` (relative to project root)

---

## Quick Reference

| Service | Port | Terminal | Command |
|---------|------|----------|---------|
| Redis | 6379 | 1 | `docker-compose up redis` |
| Backend API | 8000 | 2 | `uvicorn app.main:app --reload` |
| Frontend | 3000 | 3 | `npm run dev` |
| Testing | N/A | 4 | `pytest tests/` |

---

**Now you can run everything manually from your terminals!**

Save this guide for reference when developing locally.
