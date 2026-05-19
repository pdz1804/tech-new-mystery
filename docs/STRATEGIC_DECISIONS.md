# Strategic Decisions & Architecture - Tech News Mystery

**Created:** 2026-05-14

---

## 1. Frontend Framework Decision

### Options Evaluated
1. **Create React App (CRA)** - Simple, familiar
2. **Next.js 14** - SSR, better performance, built-in features
3. **Vue 3** - Alternative option
4. **Svelte** - Lightweight alternative

### Decision: Next.js 14
**Why:**
- Server-side rendering benefits for SEO (important for news site)
- Built-in API routes (can replace some backend endpoints if needed)
- Image optimization out-of-box
- Better performance metrics (Lighthouse scores)
- Growing ecosystem and better TypeScript support
- Vercel deployment is seamless

**Alternative if simpler:** Create React App with TypeScript for faster iteration

---

## 2. LLM Model Selection

### Options
1. **Claude (Anthropic)** - Excellent summarization, context window, cost-effective
2. **GPT-4o (OpenAI)** - Powerful, widely adopted, higher cost
3. **Claude Haiku** - Faster, cheaper, good for summarization
4. **Open source (Llama 2, Mistral)** - Full control, no API costs

### Decision: Claude API (Anthropic)
**Primary Choice:**
- Excellent at summarization and citation extraction
- Good cost-performance ratio
- Can use prompt caching for repeated summaries
- Strong context understanding for citations
- No jailbreak concerns with tech content

**Fallback:** Claude Haiku for cost optimization, Haiku 4.5 is very capable

**Optional Future:** Implement fallback to open-source models for cost control

---

## 3. Database Design Principles

### Why DynamoDB (NoSQL)?
- Fully managed serverless database (no ops overhead)
- High scalability and performance for read-heavy workloads
- Global Secondary Indexes (GSI) for flexible querying
- Native support for flexible JSON schemas
- Cost-effective with pay-per-request or provisioned capacity
- Excellent integration with AWS Lambda and serverless architecture
- Automatic backup and point-in-time recovery

### Key Indexing Strategy (Global Secondary Indexes)
```
Articles Table:
- Primary: article_id (HASH)
- GSI 1: slug (HASH) - for unique URL lookups
- GSI 2: source_id (HASH) + published_at (RANGE) - for source-based queries
- LSI: category - for category-based filtering

User Saves Table:
- Primary: user_id (HASH) + article_id (RANGE) - for user's saves

Comments Table:
- Primary: comment_id (HASH)
- GSI: article_id (HASH) + created_at (RANGE) - for article comments

Submissions Table:
- Primary: submission_id (HASH)
- GSI: user_id (HASH) + submitted_at (RANGE) - for user submissions
```

### Caching Strategy
- Articles (full content) - cache 1 hour
- Trending list - cache 30 minutes
- User preferences - cache until update
- Search results - cache 5 minutes
- News sources - cache 24 hours

---

## 4. API Design Principles

### Versioning
- All endpoints prefixed with `/v1/`
- Future updates can introduce `/v2/` without breaking clients
- Maintains backward compatibility

### Response Format
```json
{
  "success": true,
  "data": { /* actual data */ },
  "meta": {
    "pagination": { "page": 1, "limit": 20, "total": 100 }
  }
}
```

### Error Handling
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": []
  }
}
```

### Rate Limiting
- 100 requests/minute for unauthenticated
- 1000 requests/minute for authenticated
- 10000 requests/day for API keys (future)

---

## 5. Authentication Strategy

### Why JWT over sessions?
- Stateless authentication (better for distributed systems)
- Works well with mobile apps (future)
- Easier to scale horizontally
- Standard OAuth2 integration (future)

### Token Structure
```python
{
  "sub": "user_id",
  "email": "user@example.com",
  "exp": 1234567890,
  "iat": 1234567890,
  "type": "access"  # access, refresh
}
```

### Security Measures
- Passwords hashed with bcrypt (passlib)
- HTTPS enforcement
- CORS properly configured
- Rate limiting on login endpoints
- Refresh tokens for long-lived sessions
- Token blacklist for logout (Redis)

---

## 6. Crawl4AI Integration Strategy

### Why Crawl4AI?
- LLM-friendly markdown output
- Async/concurrent crawling
- Automatic boilerplate removal
- Extraction with CSS/XPath or LLM
- Python native (matches FastAPI)
- Active community

### Implementation Pattern
```python
async def crawl_and_extract(url: str) -> ArticleData:
    # 1. Crawl with Crawl4AI
    result = await AsyncWebCrawler().arun(url)
    
    # 2. Extract markdown
    markdown_content = result.markdown
    
    # 3. Parse metadata
    metadata = extract_metadata(markdown_content)
    
    # 4. Store in database
    article = Article(
        url=url,
        content=result.html,
        markdown_content=markdown_content,
        **metadata
    )
    return article
```

### Error Handling
- Retry failed crawls (exponential backoff)
- Fallback to simplified parsing
- Store error logs for analysis
- Alert on repeated failures

---

## 7. Scheduling & Task Queue

### Why Celery + Redis?
- Distributed task queue
- Scheduled tasks support (celery-beat)
- Retries and error handling
- Task monitoring and logging
- Horizontal scaling

### Alternative: AWS Lambda + EventBridge
- Serverless (lower ops overhead)
- Good for scheduled tasks
- Less overhead for simple schedules
- Higher latency (cold starts)

### Decision: Hybrid Approach
- **Celery** for frequent tasks (hourly status checks, index updates)
- **Lambda + EventBridge** for scheduled crawls (daily 2am)
- **SQS** for occasional async tasks (user submissions)

---

## 8. Deployment Architecture

### Local Development
```
Docker Compose:
- FastAPI (port 8000)
- LocalStack for DynamoDB emulation (port 4566)
- Redis (port 6379)
- Celery worker
- React dev server (port 3000)
```

### AWS Staging
```
- ECS Fargate for FastAPI
- DynamoDB with provisioned capacity
- ElastiCache for Redis
- Lambda for scheduled tasks
- S3 for assets
- CloudFront for CDN
```

### AWS Production
```
- ECS with auto-scaling
- DynamoDB with on-demand or provisioned capacity + auto-scaling
- ElastiCache with failover
- Lambda with proper concurrency limits
- S3 with versioning and lifecycle
- CloudFront with WAF
- DynamoDB point-in-time recovery enabled
- CloudWatch monitoring
- SNS for alerts
```

---

## 9. Cost Optimization Strategy

### LLM API Costs
- Use prompt caching for frequently summarized patterns
- Batch processing of articles
- Claude Haiku for simple tasks, Claude for complex
- Monitor token usage closely
- Set budget alerts in AWS

### AWS Services
- Use Auto Scaling for ECS (scale down at night)
- RDS: Use Multi-AZ only in production, single-AZ in staging
- S3: Implement lifecycle policies (archive after 90 days)
- Lambda: Set memory limits appropriately (usually 512-1024MB)
- ElastiCache: Smaller instance in staging

### Estimation (Monthly)
- **DynamoDB:** $30-100/month (on-demand or provisioned with auto-scaling)
- **ElastiCache:** $20-50/month
- **ECS Fargate:** $100-200/month
- **Lambda:** $5-20/month
- **S3/CloudFront:** $10-30/month
- **LLM API (Claude):** $200-500/month (depends on volume)
- **Total:** ~$365-900/month at scale

---

## 10. Development Workflow

### Git Strategy
```
main (production)
├── staging (staging environment)
├── feature/article-search
├── feature/user-preferences
└── fix/crawl-timeout
```

### Code Quality
- Pre-commit hooks (black, flake8, mypy for Python)
- ESLint + Prettier for JavaScript
- GitHub Actions for CI/CD
- Code coverage targets: 80%+

### Testing Strategy
- Unit tests: 70%
- Integration tests: 20%
- E2E tests: 10%
- Run tests on every PR

### PR Process
1. Feature branch from main
2. Open PR with description
3. Code review (1+ approval)
4. CI/CD pipeline passes
5. Merge to main
6. Auto-deploy to staging
7. Manual deploy to production

---

## 11. Performance Targets

### Backend
- Article list API: <150ms (DynamoDB query)
- Article detail: <100ms (DynamoDB get item)
- Search: <800ms (scan with filters)
- Trending calculation: <2s
- Crawl per article: <10s
- Summarization: <20s

### Frontend
- Home page: <2s load time
- Search results: <1s
- Article detail: <1.5s
- Largest Contentful Paint (LCP): <2.5s
- Cumulative Layout Shift (CLS): <0.1

### Infrastructure
- DynamoDB query p95: <50ms
- API response p95: <300ms
- Lambda cold start: <5s
- Cache hit rate: >80%
- DynamoDB throttle rate: 0%

---

## 12. Security Considerations

### Data Protection
- HTTPS everywhere
- Secrets in AWS Secrets Manager
- Database encryption at rest
- S3 bucket encryption
- Regular security audits

### Input Validation
- Sanitize user inputs (URLs, text)
- Validate file uploads
- Rate limiting per user
- CSRF protection (if using sessions)

### Content Safety
- Moderate user comments (future)
- Flag suspicious submissions
- Log all admin actions
- Regular backups (daily)

---

## 13. Monitoring & Observability

### Metrics to Track
- Crawl success rate
- Average summarization time
- API response times
- Cache hit rates
- Error rates by endpoint
- User engagement metrics
- Cost per article processed

### Tools
- **Logging:** CloudWatch Logs + Python logging
- **Metrics:** CloudWatch Metrics
- **Tracing:** X-Ray for Lambda
- **Monitoring:** CloudWatch Dashboards
- **Alerting:** SNS notifications

### Alert Rules
- Crawl failure rate >10%
- API response time p95 >500ms
- Error rate >5%
- Database connection pool exhaustion
- Cost threshold exceeded

---

## Next Steps

1. **Confirm these decisions** - Do you want changes?
2. **Choose frontend:** Next.js or React CRA?
3. **Choose LLM:** Claude, Haiku, or GPT-4o?
4. **Confirm deployment approach** - Hybrid Celery+Lambda or pure Lambda?
5. **Proceed with implementation** - Ready to start Phase 1?

---

## Document References
- See `PROJECT_PLAN.md` for full feature list
- See `TASK_BREAKDOWN.md` for implementation tasks
- AWS architecture diagrams available in `/infra` (to be created)
