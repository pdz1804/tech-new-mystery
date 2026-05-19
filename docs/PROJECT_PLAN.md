# Tech News Mystery - Project Plan & Architecture
**Last Updated:** May 18, 2026  
**Status:** Phase 3 Complete → Phase 4 In Progress  
**Type:** Full-stack AI News Aggregation Platform

---

## 1. Project Overview

**Vision:** A modern tech news aggregation platform that intelligently crawls, summarizes, and curates technology news daily, with AI-powered content processing, multi-role access control, and personalized user experiences.

**Key Differentiators:**
- AI-powered content generation (titles, summaries, categorization)
- LLM-friendly web scraping (Crawl4AI)
- Topic-based search via Tavily (admin feature)
- Role-based access control (admin/user)
- User engagement tracking (likes, saves, views)
- Beautiful, modern tech news browsing experience
- Real AWS infrastructure (DynamoDB, ElastiCache)

---

## 2. Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **Database:** DynamoDB (NoSQL, AWS)
- **Cache:** Redis (Docker for dev, ElastiCache for prod)
- **Task Queue:** Celery with Redis backend
- **Web Scraping:** **CRITICAL:** Crawl4AI (LLM-friendly HTML to markdown)
- **Search:** Tavily Search API
- **LLM:** Claude 3.5 Haiku via AWS Bedrock
- **Authentication:** JWT + Role-Based Access Control
- **Async:** AsyncIO, httpx

### Frontend
- **Framework:** Next.js 14+ (TypeScript)
- **Styling:** Tailwind CSS
- **State Management:** Zustand + React Query
- **UI Components:** Lucide icons, Framer Motion animations
- **Deployment:** Docker/AWS

### AWS Services
- **Compute:** EC2 or ECS (backend), CloudFront (frontend)
- **Database:** DynamoDB (articles, users, comments, saves, likes)
- **Cache:** ElastiCache (Redis)
- **Authentication:** IAM roles (EC2/ECS instance profile)
- **Monitoring:** CloudWatch
- **Bedrock:** Claude LLM access

---

## 3. Database Schema (DynamoDB)

### Core Tables

#### 1. articles
```json
{
  "article_id": "uuid (PK)",
  "slug": "string (GSI1)",
  "title": "string",
  "summary": "string",
  "content": "string (raw HTML)",
  "markdown_content": "string (formatted)",
  "author": "string | null",
  "category": "string (AI, Web Development, DevOps, ...)",
  "tags": ["string"],
  "original_url": "string",
  "source_id": "string",
  "view_count": 0,
  "like_count": 0,
  "is_published": true,
  "created_at": "timestamp",
  "published_at": "timestamp",
  "updated_at": "timestamp"
}
```

#### 2. users
```json
{
  "user_id": "uuid (PK)",
  "username": "string (GSI1)",
  "email": "string",
  "password_hash": "string",
  "role": "admin | user",
  "is_active": true,
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

#### 3. user_saves
```json
{
  "user_id": "uuid (PK, GSI1)",
  "article_id": "uuid (PK)",
  "saved_at": "timestamp",
  "updated_at": "timestamp"
}
```

#### 4. user_likes
```json
{
  "user_id": "uuid (PK, GSI1)",
  "article_id": "uuid (PK)",
  "reaction_type": "like | love | useful",
  "created_at": "timestamp"
}
```

#### 5. comments
```json
{
  "comment_id": "uuid (PK)",
  "article_id": "uuid (GSI1)",
  "user_id": "uuid (GSI2)",
  "content": "string",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

#### 6. news_sources
```json
{
  "source_id": "string (PK)",
  "name": "string",
  "url": "string",
  "category": "string",
  "is_active": true,
  "created_at": "timestamp"
}
```

#### 7. user_preferences
```json
{
  "user_id": "uuid (PK)",
  "preferred_categories": ["string"],
  "preferred_sources": ["string"],
  "notification_enabled": true,
  "email_digest": "daily | weekly | none",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

---

## 4. Core Features & Implementation Status

### Phase 1: MVP (✅ Complete)
- [x] User authentication (JWT)
- [x] Article creation from URL
- [x] Article display with markdown formatting
- [x] Article search and filtering
- [x] Category-based organization
- [x] Basic pagination

### Phase 2: Enhanced (✅ Complete)
- [x] CRUD operations on articles
- [x] Modern UI with gradients and animations
- [x] AI-powered summarization
- [x] AI category detection
- [x] AI tag generation
- [x] LLM-powered markdown formatting
- [x] Delete article with confirmation
- [x] Edit article form
- [x] Share article (Web Share API)

### Phase 3: Role-Based & Engagement (🔄 In Progress)
- [ ] Role-based access control (admin/user)
  - [ ] Admin can CRUD all articles
  - [ ] User can only CRUD own articles
  - [ ] Admin can trigger scraping/search
- [ ] User engagement tracking
  - [ ] Like articles
  - [ ] Save articles to reading list
  - [ ] View count tracking
- [ ] Web scraping integration (Crawl4AI)
  - [ ] Intelligent content extraction
  - [ ] LLM-friendly markdown conversion
- [ ] Topic-based search (Tavily)
  - [ ] Admin can search by topic
  - [ ] One-click article import from search results

### Phase 4: Production & Polish (🚀 Next)
- [ ] AWS infrastructure migration
  - [ ] Real DynamoDB (no LocalStack)
  - [ ] IAM role-based authentication
  - [ ] ElastiCache for Redis
- [ ] UI polish and accessibility
  - [ ] Fix search bar overlap
  - [ ] Improve parsing feedback
  - [ ] Add article from articles list
- [ ] Admin dashboard
  - [ ] Scraping controls
  - [ ] Topic search interface
  - [ ] User management
- [ ] Documentation cleanup

### Phase 5: Advanced (Future)
- [ ] Personalized news feed
- [ ] Email digest notifications
- [ ] Trending topics analytics
- [ ] User recommendations
- [ ] Mobile app
- [ ] API for third-party integration

---

## 5. API Endpoints

### Authentication
```
POST   /v1/auth/register       - Register new user
POST   /v1/auth/login          - Login and get JWT
POST   /v1/auth/refresh        - Refresh token
GET    /v1/auth/me             - Get current user
POST   /v1/auth/logout         - Logout
```

### Articles
```
GET    /v1/articles            - List articles with filters
POST   /v1/articles            - Create article (manual)
POST   /v1/articles/from-url   - Create article from URL
GET    /v1/articles/{slug}     - Get article details
PUT    /v1/articles/{slug}     - Update article (owner/admin)
DELETE /v1/articles/{slug}     - Delete article (owner/admin)

POST   /v1/articles/{id}/like  - Like article
DELETE /v1/articles/{id}/like  - Unlike article
GET    /v1/articles/{id}/likes - Get like count

POST   /v1/articles/{id}/save  - Save article
DELETE /v1/articles/{id}/save  - Unsave article
GET    /v1/user/saved-articles - Get saved articles
```

### Search
```
GET    /v1/search                      - Search articles
```

### Admin - Topic Search & Curation
```
POST   /v1/admin/search/tavily         - Search via Tavily API (admin only)
       Input: {query, limit}
       Returns: {results with url, title, description, source, date}
       
POST   /v1/admin/search/approve-and-create - Approve result & create article
       Input: {url, query}
       Returns: {new article with AI-generated metadata}
```

**Tavily Search Workflow:**
1. Admin enters search topic (e.g., "AI breakthroughs")
2. Admin clicks "Search" button
3. Backend calls Tavily API with query
4. Returns 10 results with URLs and snippets
5. Admin reviews each result
6. Admin clicks "Approve & Create Article" on selected results
7. Backend scrapes URL with Crawl4AI
8. AI generates title, summary, category, tags, markdown
9. New article created and appears in articles list

### Comments
```
GET    /v1/articles/{id}/comments     - Get comments
POST   /v1/articles/{id}/comments     - Add comment
DELETE /v1/comments/{id}              - Delete comment
```

### User
```
GET    /v1/user/profile        - Get user profile
PUT    /v1/user/profile        - Update profile
GET    /v1/user/preferences    - Get preferences
PUT    /v1/user/preferences    - Update preferences
```

### Admin - User Management
```
GET    /v1/admin/users         - List users (admin only)
PUT    /v1/admin/users/{id}    - Update user role
DELETE /v1/admin/users/{id}    - Delete user
```

---

## 6. Frontend Pages & Components

### Public Pages
- **Home** (`/`) - Hero, featured articles, add article modal
- **Articles List** (`/articles`) - Browse all articles with filters
- **Article Detail** (`/articles/[slug]`) - Full article with comments
- **Search** (`/search`) - Search and filter articles
- **Login** (`/login`) - Authentication
- **Register** (`/register`) - User registration

### Authenticated Pages
- **Saved Articles** (`/bookmarks`) - User's saved articles
- **User Profile** (`/profile`) - User settings and preferences

### Admin Pages
- **Admin Dashboard** (`/admin`) - Admin controls
- **Search & Import** (`/admin/search`) - Tavily search interface
- **User Management** (`/admin/users`) - User administration

---

## 7. Configuration & Deployment

### Environment Variables

**Development (Local Docker):**
```env
ENVIRONMENT=local
AWS_REGION=us-west-2
BEDROCK_REGION=us-west-2
BEDROCK_MODEL=anthropic.claude-3-5-haiku-20241022
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
TAVILY_API_KEY=tvly-...
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

**Production (AWS):**
```env
ENVIRONMENT=production
AWS_REGION=us-west-2
BEDROCK_REGION=us-west-2
BEDROCK_MODEL=anthropic.claude-3-5-haiku-20241022
ELASTICACHE_ENDPOINT=redis://...cache.amazonaws.com:6379
CELERY_BROKER_URL=$ELASTICACHE_ENDPOINT/1
CELERY_RESULT_BACKEND=$ELASTICACHE_ENDPOINT/2
TAVILY_API_KEY=tvly-...
```

**AWS Setup (us-west-2):**
- **NO hardcoded AWS credentials** - Uses IAM role only
- **IAM Role** (EC2 instance profile or ECS task role):
  - Permissions: DynamoDB (read/write), Bedrock (invoke), ElastiCache (connect)
  - Boto3 auto-detects credentials from instance role
- **DynamoDB** (Real AWS, not LocalStack):
  - On-demand billing (auto-scales)
  - Tables: articles, users, user_likes, user_saves, comments, news_sources
- **ElastiCache** (Production only):
  - Redis cluster in us-west-2
- **Bedrock** (us-west-2):
  - Claude 3.5 Haiku for AI processing
  - OpenAI GPT-4o-mini as fallback
- **Region:** us-west-2 (all AWS services)

---

## 8. Security & Access Control

### Authentication
- JWT tokens with 1-day expiration
- Refresh tokens with 30-day expiration
- Password hashing with bcrypt
- HTTPS only (in production)

### Authorization (RBAC)
- **Admin Role:**
  - Create, read, update, delete any article
  - Search via Tavily
  - Trigger web scraping
  - Manage users
  - View all analytics
  
- **User Role:**
  - Create, read, update, delete own articles
  - Read all articles
  - Like and save articles
  - Leave comments
  - View own profile and preferences

---

## 9. Performance & Scaling

### Caching Strategy
- **Redis:** Article listing, search results, user sessions
- **DynamoDB:** On-demand billing for auto-scaling
- **CloudFront:** Frontend assets

### Optimization
- Pagination (20 items per page default)
- Database indexing (GSI for common queries)
- Image optimization (Crawl4AI markdown)
- Lazy loading on frontend

---

## 10. Monitoring & Analytics

### Logging
- CloudWatch Logs for application logs
- Separate logs for API, workers, errors

### Metrics
- Article view counts
- User engagement (likes, saves)
- Search popularity
- API response times
- Error rates

---

## 11. Development Workflow

### Local Development
```bash
cd infra
docker-compose up  # Starts all services locally
# Redis runs in Docker
# DynamoDB uses real AWS (reads are free)
# Backend at http://localhost:8000
# Frontend at http://localhost:3000
```

### Testing
```bash
pytest backend/tests/
# Unit tests for services
# Integration tests with DynamoDB
# API endpoint tests
```

### Deployment
```bash
# Push to main branch
# GitHub Actions runs tests
# CodeDeploy pushes to EC2/ECS
# CloudFront invalidates cache
```

---

## 12. File Organization

```
D:\FPT\Demo\Tech-News-Mystery
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── articles/
│   │   │       ├── search/
│   │   │       ├── comments/
│   │   │       └── auth/
│   │   ├── services/
│   │   │   ├── article_service.py
│   │   │   ├── article_processing_service.py
│   │   │   ├── scraping_service.py
│   │   │   ├── search_service.py
│   │   │   └── ...
│   │   ├── repositories/
│   │   └── models/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── types/
│   └── package.json
├── infra/
│   ├── docker-compose.yml
│   └── docker/
├── docs/
│   ├── PROJECT_PLAN.md (this file)
│   ├── STRATEGIC_DECISIONS.md
│   └── AWS_DEPLOYMENT.md
└── CLAUDE.md
```

---

## 13. Next Steps (Phase 4)

1. **Implement RBAC** - Add role field to users, update endpoints
2. **Add engagement features** - Like, save, view count
3. **Integrate Crawl4AI** - Intelligent content extraction (CRITICAL component)
4. **Implement Tavily search** - Admin-only topic search endpoint
5. **Fix UI issues** - Search bar, parsing button, add article button
6. **AWS migration** - Remove LocalStack, use real DynamoDB
7. **Documentation cleanup** - Remove old docs, keep only current

---

**Maintained by:** Development Team  
**Last Review:** May 18, 2026  
**Next Review:** June 1, 2026
