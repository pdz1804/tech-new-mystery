# Tech News Mystery - System Architecture

**Version:** 1.0  
**Date:** May 18, 2026  
**Status:** Production Ready

---

## 1. System Overview

Tech News Mystery is a full-stack AI-powered news aggregation platform that intelligently crawls, summarizes, and curates technology news. The system combines modern web scraping, AI processing, and role-based access control to deliver a curated tech news experience.

### Key Components
- **Frontend:** Next.js 14 (TypeScript, Tailwind CSS)
- **Backend:** FastAPI (Python 3.11+)
- **Database:** DynamoDB (AWS)
- **Cache:** Redis (Docker/ElastiCache)
- **Task Queue:** Celery + Redis
- **AI/LLM:** Claude 3.5 Haiku (AWS Bedrock) + GPT-4o-mini (OpenAI fallback)
- **Web Scraping:** Crawl4AI (LLM-friendly HTML to markdown)
- **Search:** Tavily Search API

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Frontend (Next.js 14)                                    │   │
│  │ - User Pages: /articles, /profile, /bookmarks            │   │
│  │ - Admin Pages: /admin/search                             │   │
│  │ - Components: Article lists, modals, search bar          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTPS
┌─────────────────────────────────────────────────────────────────┐
│                    API GATEWAY LAYER                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ FastAPI Application                                      │   │
│  │ - JWT Authentication                                     │   │
│  │ - Role-Based Access Control (Admin/User)                 │   │
│  │ - Rate Limiting & CORS                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   BUSINESS LOGIC LAYER                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Services                                                 │   │
│  │ - ArticleService: CRUD, AI processing, engagement        │   │
│  │ - AuthService: JWT token generation & validation         │   │
│  │ - SearchService: Tavily API integration                  │   │
│  │ - ScrapingService: Crawl4AI web scraping                │   │
│  │ - ArticleProcessingService: LLM-powered content gen      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   DATA ACCESS LAYER                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Repositories (DynamoDB)                                  │   │
│  │ - ArticleRepository                                      │   │
│  │ - UserRepository                                         │   │
│  │ - UserLikesRepository                                    │   │
│  │ - UserSavesRepository                                    │   │
│  │ - CommentRepository                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────┬──────────────────────────┐
│         DATABASE LAYER               │     CACHE LAYER          │
│  ┌────────────────────────────────┐  │  ┌──────────────────────┐│
│  │ AWS DynamoDB (us-west-2)       │  │  │ Redis                ││
│  │ - articles                     │  │  │ - Session cache      ││
│  │ - users                        │  │  │ - Search results     ││
│  │ - user_likes                   │  │  │ - View counts        ││
│  │ - user_saves                   │  │  │ - Celery broker      ││
│  │ - comments                     │  │  └──────────────────────┘│
│  │ - news_sources                 │  │                          │
│  │ - news_articles (from crawlers)│  │                          │
│  └────────────────────────────────┘  │                          │
└──────────────────────────────────────┴──────────────────────────┘
```

---

## 3. Data Flow for Core Features

### Feature 1: Create Article from URL (User)
```
User Browser
    ↓ POST /v1/articles/from-url {url, title, author}
FastAPI Router (Authenticated)
    ↓
ArticleService.create_from_url()
    ↓ 1. Validate URL format
    ↓ 2. Check for duplicates
🔴 CRITICAL STEP: Crawl4AI extracts clean markdown
ScrapingService.scrape_url() (Crawl4AI)
    ↓ Returns markdown_content (LLM-ready)
ArticleProcessingService.process_url_content()
    ↓ Sends to AI (Bedrock/OpenAI)
AI Response: {title, summary, category, tags, author, markdown}
    ↓
ArticleRepository.create() → DynamoDB
    ↓
Return: Article with AI-generated metadata
```

### Feature 2: Admin Search & Approve (Tavily Workflow)
```
Admin Dashboard (/admin/search)
    ↓ POST /v1/admin/search/tavily {query, limit}
FastAPI Router (Admin only)
    ↓
SearchService.tavily_search()
    ↓ Call Tavily API
Tavily Returns: [{url, title, description, source, date}, ...]
    ↓
Frontend Displays: Result cards
    ↓ User clicks "Approve & Create"
    ↓ POST /v1/admin/search/approve-and-create {url, query}
    ↓
ArticleService.create_from_url() (same as Feature 1)
    ↓ Crawl4AI → AI Processing → DynamoDB
    ↓
Return: New article created
```

### Feature 3: User Engagement (Like/Save/View)
```
User Interactions:
  - Like: POST /v1/articles/{id}/like → UserLikesRepository → like_count++
  - Unlike: DELETE /v1/articles/{id}/like → UserLikesRepository → like_count--
  - Save: POST /v1/articles/{id}/save → UserSavesRepository
  - Unsave: DELETE /v1/articles/{id}/save → UserSavesRepository
  - View: GET /v1/articles/{slug} → increment_view_count()

Data Storage:
  - like_count: denormalized on articles table (for quick access)
  - user_likes: composite key (user_id, article_id)
  - user_saves: composite key (user_id, article_id)
  - view_count: incremented via ArticleService
```

---

## 4. Database Schema (DynamoDB)

### Table: articles
```
Primary Key: article_id (UUID)
Global Secondary Index: slug (for slug-based lookups)

Fields:
  - article_id: string (PK)
  - slug: string (GSI)
  - title: string (AI-generated)
  - summary: string (AI-generated)
  - content: string (raw text from Crawl4AI)
  - markdown_content: string (structured markdown from AI)
  - author: string | null
  - category: string (AI-generated)
  - tags: list[string] (AI-generated)
  - original_url: string
  - source_id: string (domain)
  - view_count: integer (default 0)
  - like_count: integer (default 0, denormalized for performance)
  - is_published: boolean
  - created_at: timestamp
  - published_at: timestamp
  - updated_at: timestamp
```

### Table: users
```
Primary Key: user_id (UUID)
Global Secondary Index: username (for lookups)

Fields:
  - user_id: string (PK)
  - username: string (GSI, unique)
  - email: string (unique)
  - password_hash: string (bcrypt)
  - role: enum[admin | user] (default: user)
  - is_active: boolean (default: true)
  - created_at: timestamp
  - updated_at: timestamp
```

### Table: user_likes
```
Primary Key: (user_id, article_id) - Composite
Global Secondary Index: user_id (for user's likes)

Fields:
  - user_id: string (PK)
  - article_id: string (PK)
  - created_at: timestamp
```

### Table: user_saves
```
Primary Key: (user_id, article_id) - Composite
Global Secondary Index: user_id (for user's saves)

Fields:
  - user_id: string (PK)
  - article_id: string (PK)
  - saved_at: timestamp
  - updated_at: timestamp
```

---

## 5. API Endpoint Architecture

### Authentication & Authorization
```
POST   /v1/auth/register              - Register user (public)
POST   /v1/auth/login                 - Login (public)
GET    /v1/auth/me                    - Current user (authenticated)

Middleware:
  - JWT validation on protected routes
  - Role checking (require_admin for admin endpoints)
```

### Article Endpoints
```
GET    /v1/articles                   - List articles (pagination, filters)
POST   /v1/articles                   - Create article (manual, auth required)
POST   /v1/articles/from-url          - Create from URL (auth required)
GET    /v1/articles/{slug}            - Get article detail + increment view
PUT    /v1/articles/{slug}            - Update article (admin/owner)
DELETE /v1/articles/{slug}            - Delete article (admin/owner)

GET    /v1/articles/{id}/likes        - Get like count
POST   /v1/articles/{id}/like         - Like article (auth required)
DELETE /v1/articles/{id}/like         - Unlike article (auth required)

POST   /v1/articles/{id}/save         - Save article (auth required)
DELETE /v1/articles/{id}/save         - Unsave article (auth required)
GET    /v1/user/saved-articles        - Get user's saved articles
```

### Admin Endpoints
```
POST   /v1/admin/search/tavily        - Search via Tavily (admin only)
POST   /v1/admin/search/approve-and-create - Approve & create (admin only)

Request:  {query: "AI breakthroughs", limit: 10}
Response: {results: [{url, title, description, source, date}, ...]}

Request:  {url: "https://...", query: "AI breakthroughs"}
Response: {article: {...AI-generated metadata...}}
```

---

## 6. Security Architecture

### Authentication
- **JWT Tokens:** 1-day expiration for access, 30-day for refresh
- **Password:** Bcrypt hashing with salt
- **Token Storage:** HTTP-only cookies (frontend)

### Authorization (RBAC)
- **Admin Role:** CRUD all articles, search/scrape, user management
- **User Role:** CRUD own articles, read all articles, like, save, comment
- **Access Control:** Middleware checks role before action

### Data Security
- **No AWS Credentials in Code:** IAM role-based auth only
- **HTTPS Only:** TLS encryption for all data in transit
- **Input Validation:** Pydantic schemas validate all requests
- **CORS:** Restricted to frontend domain

---

## 7. Performance & Scaling Strategy

### Caching Layer
```
Redis Cache:
  - Session tokens (TTL: 30 days)
  - Article listings (TTL: 5 min)
  - Search results (TTL: 10 min)
  - View count counters (persisted to DB hourly)

Benefits:
  - Fast API responses (sub-100ms p95)
  - Reduced database load
  - Real-time view count tracking
```

### Database Optimization
```
DynamoDB:
  - On-demand billing (auto-scale)
  - Global Secondary Indexes for common queries
  - Item TTL for temporary data
  - Batch operations for bulk writes

Denormalization:
  - like_count on articles (avoid joins)
  - source_id extraction (efficient filtering)
```

### Async Processing
```
Celery Worker Tasks:
  - Summarization (background)
  - Crawling (background)
  - Email digests (scheduled)
  - Trending calculation (periodic)

Benefits:
  - Non-blocking API responses
  - Scalable background processing
  - Retry logic for failed tasks
```

---

## 8. External Integrations

### AWS Services
- **DynamoDB:** Primary database (read/write)
- **Bedrock:** Claude 3.5 Haiku for AI processing
- **ElastiCache:** Redis for production caching

### Third-Party APIs
- **Crawl4AI:** Intelligent web scraping
- **OpenAI GPT-4o-mini:** LLM fallback (when Bedrock fails)
- **Tavily Search API:** Tech topic search

### Error Handling
```
LLM Processing:
  Primary: AWS Bedrock (Claude 3.5 Haiku)
  Fallback: OpenAI GPT-4o-mini
  
  If Bedrock fails → retry with OpenAI
  If both fail → user receives error notification

Web Scraping:
  Primary: Crawl4AI
  If fails → user notified, article not created
```

---

## 9. Crawl4AI - The Intelligent Content Parser

### Why Crawl4AI is Critical
- **NOT just HTML scraping** - Intelligent content extraction
- Removes ads, banners, navigation clutter
- Preserves document structure and formatting
- Outputs LLM-friendly markdown (not raw HTML)
- Enables high-quality AI-generated metadata

### How It Works
1. Takes raw URL as input
2. Extracts meaningful content with Crawl4AI
3. Converts to clean markdown
4. Passes to LLM for processing (Bedrock/OpenAI)

### Technology Stack
- **Library:** Crawl4AI (open-source, LLM-powered)
- **Browser:** Playwright (automated browser control)
- **Output:** Clean markdown (perfect for LLMs)
- **Async:** Full async/await support for non-blocking operations

### Code Location
- **Service:** `backend/app/services/scraping_service.py` - Main scraping logic
- **Client:** `backend/app/integrations/crawler_client.py` - Crawl4AI integration
- **Tests:** `backend/tests/test_scraping_service.py` - Comprehensive test suite

### Example Flow
```
Raw URL: https://techcrunch.com/article/ai-breakthrough
    ↓ (Crawl4AI extracts)
Clean Markdown:
  # Title
  Body text with structure
  [Links]
    ↓ (Pass to LLM)
AI Processing:
  - Generate title
  - Create summary
  - Detect category
  - Extract tags
    ↓
Final Article stored in DynamoDB
```

---

## 10. Deployment Architecture

### Local Development
```
docker-compose up
  - Backend: FastAPI at localhost:8000
  - Frontend: Next.js at localhost:3000
  - Redis: Docker container
  - DynamoDB: Real AWS (reads free tier)
  - Environment: ENVIRONMENT=local
```

### Production (AWS)
```
EC2/ECS Instance:
  - Backend: FastAPI via ASGI (Uvicorn)
  - Frontend: Next.js via Docker
  - IAM Role: Automatically provides AWS credentials
  
Services:
  - DynamoDB: us-west-2 (real)
  - ElastiCache: Redis cluster
  - Bedrock: Claude model access
  - CloudFront: Static asset CDN
```

---

## 11. Monitoring & Observability

### Logging
- **CloudWatch Logs:** Application, API, worker logs
- **Log Levels:** DEBUG (dev), INFO (prod)
- **Key Events:** Authentication, API calls, errors

### Metrics
- **API Response Times:** p50, p95, p99
- **Database Operations:** Read/write latency
- **Engagement:** View counts, likes, saves
- **Cache Hit Ratio:** Redis efficiency

### Error Tracking
- **Exceptions:** Logged with stack trace
- **Failed Tasks:** Celery retry logic
- **API Errors:** HTTP status codes + detail messages

---

## 12. Scalability Limits & Considerations

### Current Capacity
- **Articles:** 1M+ items (DynamoDB on-demand)
- **Users:** 100K+ (DynamoDB on-demand)
- **Concurrent Users:** 1000+ (based on API capacity)
- **QPS:** 10,000+ requests/second (DynamoDB on-demand scaling)

### Scaling Strategy
1. **Database:** DynamoDB auto-scales on-demand
2. **Cache:** ElastiCache cluster mode for horizontal scaling
3. **Workers:** Celery auto-scales with queue depth
4. **Frontend:** CloudFront CDN distributes content
5. **Compute:** ECS auto-scaling groups for load balancing

### Bottlenecks & Mitigation
```
Bottleneck 1: LLM Processing (AI generation)
  - Mitigate: Queue requests, batch processing, fallback models

Bottleneck 2: Web Scraping (Crawl4AI)
  - Mitigate: Rate limiting, retry logic, cache results

Bottleneck 3: Database Writes (user_likes, user_saves)
  - Mitigate: Batch updates, cache-aside pattern

Bottleneck 4: Search Index (Tavily)
  - Mitigate: Cache results, rate limit per user
```

---

## 13. Disaster Recovery & Business Continuity

### Backup Strategy
- **DynamoDB Point-in-Time Recovery:** Automatic (35-day retention)
- **Redis Persistence:** AOF persistence for data recovery
- **Backup Frequency:** Continuous with hourly snapshots

### Recovery Procedures
```
Scenario 1: Database Unavailable
  - Failover to read replica (if multi-region)
  - Return cached data from Redis
  - Queue writes for later

Scenario 2: Cache Layer Down
  - Continue with direct DB access (slower)
  - Automatically rebuild cache on recovery

Scenario 3: API Service Down
  - CloudFront serves cached HTML
  - Return cached API responses
  - Health checks trigger auto-restart
```

---

## 14. Development & Testing

### Test Coverage
- **Unit Tests:** 235+ tests, 66% coverage
- **Integration Tests:** 41 tests for end-to-end workflows
- **UAT Tests:** 20+ user scenarios validated

### Test Execution
```bash
# All tests
python -m pytest tests/ -v

# Integration tests only
python -m pytest tests/test_integration.py tests/test_rbac_engagement.py -v

# With coverage
python -m pytest --cov=app tests/
```

---

## 15. Known Limitations & Future Enhancements

### Current Limitations
- Single region (us-west-2)
- No multi-language support
- No article commenting yet
- No user recommendations
- No email digest feature

### Future Enhancements
- Multi-region DynamoDB (disaster recovery)
- Full-text search (OpenSearch/Elasticsearch)
- User recommendation engine (ML-based)
- Email digest notifications
- Mobile app (React Native)
- Advanced analytics dashboard

---

**Document Version:** 1.0  
**Last Updated:** May 18, 2026  
**Maintained By:** Development Team  
**Next Review:** June 30, 2026
