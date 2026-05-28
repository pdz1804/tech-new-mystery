# Tech News Mystery - API Reference

**Version:** 1.0  
**Base URL:** `https://api.technewsmystery.com/v1` (production)  
**Base URL:** `http://localhost:8000/v1` (development)

---

## Authentication

All authenticated endpoints require a JWT token in the `Authorization` header:

```
Authorization: Bearer <token>
```

Token expiration: **1 day** (86,400 seconds)

---

## Auth Endpoints

### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePassword123"
}
```

**Response (201):**
```json
{
  "success": true,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "role": "user"
}
```

### Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "SecurePassword123"
}
```

**Response (200):**
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Get Current User
```http
GET /auth/me
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "role": "user",
  "is_active": true
}
```

---

## Article Endpoints

### List Articles
```http
GET /articles?limit=20&category=AI&tags=machine-learning&source_id=techcrunch.com
Authorization: Bearer <token>
```

**Query Parameters:**
- `limit` (int, 1-100, default: 20) - Items per page
- `last_key` (string) - Pagination cursor
- `category` (string) - Filter by category
- `source_id` (string) - Filter by source/domain
- `tags` (list) - Filter by tags (comma-separated)
- `start_date` (string) - ISO format (2026-05-18)
- `end_date` (string) - ISO format
- `sort_by` (string) - created_at, published_at, view_count

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "article_id": "uuid",
      "title": "OpenAI Releases New Model",
      "slug": "openai-releases-new-model",
      "summary": "OpenAI announced a breakthrough in AI with their latest model release.",
      "content": "Full article content here...",
      "markdown_content": "# Heading\nMarkdown formatted content",
      "author": "John Smith",
      "category": "AI",
      "tags": ["openai", "ai", "model"],
      "original_url": "https://techcrunch.com/article",
      "source_id": "techcrunch.com",
      "view_count": 150,
      "like_count": 25,
      "is_published": true,
      "created_at": "2026-05-18T10:30:00Z",
      "published_at": "2026-05-18T10:30:00Z"
    }
  ],
  "meta": {
    "limit": 20,
    "has_next": true,
    "next_cursor": "{\"article_id\": {\"S\": \"844ebd6c-d1f8-467a-bb73-e24b8672ed09\"}}",
    "total_count": 62
  }
}
```

#### Pagination Metadata

The `meta` object in the list response contains:

- **`limit`** (int) - Number of articles returned in this request
- **`has_next`** (bool) - Whether more articles exist beyond this page
- **`next_cursor`** (string) - Cursor for fetching the next page (base64 JSON). Only present if `has_next=true`
- **`total_count`** (int) - **Total number of articles matching the filters** - use this to calculate total pages

**Example Usage:**

```javascript
// Frontend: Calculate total pages
const totalArticles = response.meta.total_count;  // 62
const itemsPerPage = 12;
const totalPages = Math.ceil(totalArticles / itemsPerPage);  // 6 pages

// Pagination Display: Show smart pagination (e.g., page 3 of 100)
// UI shows: 1 2 3 4 5 ... 99 100  (with ellipsis for gaps)

// Backend: Fetch next page using cursor
const nextResponse = await fetch(
  `/articles?limit=20&last_key=${encodeURIComponent(response.meta.next_cursor)}`
);
```

**Pagination Strategy:**
- Use `limit` to control batch size (max 100)
- Use `next_cursor` for server-side pagination (DynamoDB cursor-based)
- Use `total_count` for UI pagination display (calculate total pages)
- Combine `total_count` with client-side sorting/filtering for responsive UX

### Get Article Detail
```http
GET /articles/{slug}
```

**Example:** `GET /articles/openai-releases-new-model`

**Response (200):** Same as list article object

**Response (404):**
```json
{
  "detail": "Article not found"
}
```

### Create Article (Manual)
```http
POST /articles
Content-Type: application/json
Authorization: Bearer <token>

{
  "title": "Breaking AI News",
  "summary": "A summary of the news",
  "content": "Full article content",
  "author": "Your Name",
  "category": "AI",
  "tags": ["ai", "news"],
  "original_url": "https://example.com/article",
  "source_id": "example.com"
}
```

**Response (201):** Created article object

### Create Article from URL
```http
POST /articles/from-url
Content-Type: application/json
Authorization: Bearer <token>

{
  "url": "https://techcrunch.com/2026/05/18/article",
  "title": "Optional custom title",
  "author": "Optional author"
}
```

**Process:**
1. Validates URL format
2. **Crawl4AI scrapes and extracts markdown** ⭐ (CRITICAL)
3. AI processes extracted content and generates: title, summary, category, tags
4. Article created with AI-generated metadata

**Response (201):**
```json
{
  "success": true,
  "data": {
    "article_id": "uuid",
    "title": "AI-Generated Title",
    "slug": "ai-generated-title",
    "summary": "AI-generated summary",
    "content": "Extracted content",
    "markdown_content": "# AI-Formatted Content",
    "author": "Extracted or provided",
    "category": "AI",
    "tags": ["ai", "generated", "content"],
    "original_url": "https://techcrunch.com/...",
    "source_id": "techcrunch.com",
    "created_at": "2026-05-18T10:30:00Z"
  }
}
```

### Update Article
```http
PUT /articles/{slug}
Content-Type: application/json
Authorization: Bearer <token>

{
  "title": "Updated Title",
  "content": "Updated content",
  "category": "DevOps",
  "tags": ["devops", "kubernetes"]
}
```

**Authorization:** Owner or Admin only

**Response (200):** Updated article object

### Delete Article
```http
DELETE /articles/{slug}
Authorization: Bearer <token>
```

**Authorization:** Owner or Admin only

**Response (200):**
```json
{
  "success": true,
  "message": "Article deleted successfully"
}
```

---

## Engagement Endpoints

### Like Article
```http
POST /articles/{article_id}/like
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Article liked"
  }
}
```

**Response (400):**
```json
{
  "detail": "Article already liked by this user"
}
```

### Unlike Article
```http
DELETE /articles/{article_id}/like
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Article unliked"
  }
}
```

### Get Like Count
```http
GET /articles/{article_id}/likes
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "article_id": "uuid",
    "like_count": 42
  }
}
```

### Save Article
```http
POST /articles/{article_id}/save
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "message": "Article saved"
}
```

### Unsave Article
```http
DELETE /articles/{article_id}/save
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "message": "Article removed from saves"
}
```

### Get Saved Articles
```http
GET /user/saved-articles?limit=20
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "article_id": "uuid",
      "title": "Saved Article",
      "slug": "saved-article",
      ...
    }
  ]
}
```

---

## Admin Endpoints (Admin Role Required)

### NewsAPI Search (Two-Phase Intelligent Search)
```http
POST /admin/newsapi/trigger
Content-Type: application/json
Authorization: Bearer <admin-token>

{
  "query": "machine learning innovation",
  "from_date": "2026-05-21"
}
```

**Parameters:**
- `query` (string, optional) - Custom search query. If omitted, uses default comprehensive query.
- `from_date` (string, optional) - Search from date (ISO format: YYYY-MM-DD). Defaults to yesterday.

**Search Strategy (Two Phases):**

**PHASE 1: Priority Sources** (Strict source filtering)
- TechCrunch (5 articles)
- The Verge (5 articles)
- Google News (5 articles)
- **Max: 15 articles from priority sources**

**PHASE 2: Fallback Search** (Unrestricted - triggered if PHASE 1 < 15 results)
- Searches without source restrictions
- Fills up to 15 total articles
- Maintains full deduplication across both phases

**Response (200):**
```json
{
  "success": true,
  "message": "NewsAPI scheduler task triggered successfully. Task ID: abc123"
}
```

The results are stored in the pending search queue and must be approved before article creation.

**Default Query (when custom query not provided):**
```
(artificial intelligence OR AI OR machine learning OR LLM OR generative AI OR 
deep learning OR neural networks OR transformers OR embeddings OR AWS OR Azure 
OR cloud computing OR tech startup OR funding OR innovation OR breakthrough)
```

---

### Tavily Search
```http
POST /admin/search/tavily
Content-Type: application/json
Authorization: Bearer <admin-token>

{
  "query": "AI breakthroughs 2026",
  "limit": 10
}
```

**Response (200):**
```json
{
  "success": true,
  "query": "AI breakthroughs 2026",
  "count": 10,
  "results": [
    {
      "url": "https://techcrunch.com/article1",
      "title": "OpenAI Announces New Model",
      "description": "OpenAI released a new model that can...",
      "source": "techcrunch.com",
      "published_date": "2026-05-18"
    },
    {
      "url": "https://arxiv.org/paper123",
      "title": "Research on Efficient AI Training",
      "description": "Researchers discover new method for...",
      "source": "arxiv.org",
      "published_date": "2026-05-17"
    }
  ]
}
```

### Approve & Create Article
```http
POST /admin/search/approve-and-create
Content-Type: application/json
Authorization: Bearer <admin-token>

{
  "url": "https://techcrunch.com/article1",
  "query": "AI breakthroughs 2026"
}
```

**Process:**
1. Scrapes URL with Crawl4AI
2. AI processes and generates metadata
3. Creates new article in database

**Response (201):**
```json
{
  "success": true,
  "data": {
    "article_id": "uuid",
    "slug": "openai-announces-new-model",
    "title": "OpenAI Announces New Model",
    "summary": "AI-generated 2-3 sentence summary",
    "category": "AI",
    "tags": ["openai", "ai-model", "release"],
    "author": "Extracted from content",
    "markdown_content": "# Formatted Content",
    "created_at": "2026-05-18T10:30:00Z"
  }
}
```

### Clean Search Queue
```http
DELETE /admin/searches/clean
Authorization: Bearer <admin-token>
```

**Description:**
Deletes all pending search results from the queue. Use when:
- Clearing out old search results before a new search campaign
- Starting fresh after reviewing a batch of results
- Cleaning up the queue for maintenance

⚠️ **Warning:** This action is **irreversible**. All pending searches will be permanently deleted.

**Response (200):**
```json
{
  "success": true,
  "message": "Successfully cleaned 42 pending searches from the queue"
}
```

**Response (200, empty queue):**
```json
{
  "success": true,
  "message": "Queue is already empty - nothing to clean"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid input: Title cannot be empty"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized to perform this action"
}
```

### 404 Not Found
```json
{
  "detail": "Article not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": "Failed to process URL: Connection timeout"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

- **Public endpoints:** 1000 requests/minute per IP
- **Authenticated endpoints:** 5000 requests/minute per user
- **Admin endpoints:** 100 requests/minute per admin

Headers included in response:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1634567890
```

---

## Pagination

For list endpoints, use cursor-based pagination:

```http
GET /articles?limit=20&last_key=<cursor>
```

The response includes `last_key` to fetch the next page:
```json
{
  "data": [...],
  "meta": {
    "limit": 20,
    "last_key": "article-id-50"
  }
}
```

If `last_key` is `null`, you've reached the end.

---

## Filtering Examples

### By Category
```
GET /articles?category=AI
GET /articles?category=DevOps
```

### By Source
```
GET /articles?source_id=techcrunch.com
GET /articles?source_id=arxiv.org
```

### By Tags
```
GET /articles?tags=machine-learning,neural-networks
```

### By Date Range
```
GET /articles?start_date=2026-05-01&end_date=2026-05-31
```

### Combined Filters
```
GET /articles?category=AI&source_id=techcrunch.com&tags=ai&sort_by=view_count
```

---

## Categories

Valid category values:
- `AI` - Artificial Intelligence
- `Web Development`
- `DevOps`
- `Cloud Computing`
- `Security`
- `Data Science`
- `Mobile Development`
- `Infrastructure`
- `Machine Learning`
- `Other`

---

## Common Workflows

### Workflow 1: User Registration & First Article
```
1. POST /auth/register → get user_id
2. POST /auth/login → get JWT token
3. POST /articles/from-url {url} → create article
4. GET /articles/{slug} → read article
5. POST /articles/{article_id}/like → like article
6. POST /articles/{article_id}/save → save for later
```

### Workflow 2: Admin Tavily Search
```
1. POST /admin/search/tavily {query: "AI breakthroughs"} → get results
2. Review results in frontend
3. POST /admin/search/approve-and-create {url} → create article
4. Repeat step 3 for other results
5. GET /articles → verify new articles in list
```

### Workflow 3: Browse & Engage
```
1. GET /articles → list articles
2. GET /articles/{slug} → view detail (increments view count)
3. POST /articles/{article_id}/like → like article
4. GET /user/saved-articles → get reading list
```

---

## Testing

### Pre-Created Test Accounts

**Use these accounts for development/testing** (automatically created when backend starts):

**Admin Account:**
- Username: `admin` | Password: `admin123` | Role: admin

**User Account:**
- Username: `testuser` | Password: `user123` | Role: user

### Using cURL

```bash
# Login with pre-created admin account
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Or login as regular user
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"user123"}'

# Save token for subsequent requests
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# List articles
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/articles

# Create article from URL
curl -X POST http://localhost:8000/v1/articles/from-url \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://techcrunch.com/article"}'

# Admin-only: Search with Tavily
curl -X POST http://localhost:8000/v1/admin/search/tavily \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"AI breakthroughs","limit":5}'
```

### Using Postman

1. Import collection: `docs/postman-collection.json`
2. Set environment: `development` or `production`
3. Create token via `/auth/login`
4. Run requests

### Using Python

```python
import requests

base_url = "http://localhost:8000/v1"

# Register
resp = requests.post(f"{base_url}/auth/register", json={
    "username": "test",
    "email": "test@example.com",
    "password": "test123"
})
print(resp.json())

# Login
login_resp = requests.post(f"{base_url}/auth/login", json={
    "username": "test",
    "password": "test123"
})
token = login_resp.json()["access_token"]

# List articles
headers = {"Authorization": f"Bearer {token}"}
articles = requests.get(f"{base_url}/articles", headers=headers)
print(articles.json())
```

---

**Version:** 1.0  
**Last Updated:** May 18, 2026  
**Maintained By:** API Team  
**Support:** api-support@example.com
