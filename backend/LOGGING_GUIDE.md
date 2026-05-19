# Logging Guide - Tech News Mystery Backend

## Overview

The backend implements **comprehensive logging for debugging and monitoring**. All logs are written to both console and rotating file handlers.

**Key Points:**
- Logs rotate at 10MB per file, keeping 10 backups automatically
- DEBUG level logs only in development (`ENVIRONMENT=local` in .env)
- Separate log files per component for easy filtering and troubleshooting
- Detailed structured logging with timestamps, function names, and line numbers
- All major operations logged with clear success/error indicators (✅/❌/🔴)
- Perfect for production debugging, performance analysis, and incident investigation

---

## Log Files

All log files are stored in `logs/` directory:

```
logs/
├── app.log              # Main application log (all levels)
├── api.log              # API routes, request/response handling
├── services.log         # Business logic (articles, engagement, search)
├── database.log         # Repository operations (DynamoDB)
└── integrations.log     # External integrations (Crawl4AI, LLM, Tavily)
```

Each log file rotates at **10MB** with **10 backups** kept automatically.

---

## Log Levels

### ERROR (Red) - Production Issues
Critical problems that need immediate attention:

```
2026-05-19 10:30:45.123 - app.integrations - ERROR - [crawler_client.py:47] - scrape_url() - 🔴 Crawl4AI scraping failed: Connection timeout
2026-05-19 10:30:46.234 - app.repositories - ERROR - [article_repository.py:82] - create() - ❌ Failed to create article: ValidationError
```

**Common ERROR scenarios:**
- Database connection failures
- Crawl4AI scraping timeouts
- LLM API errors
- Invalid data validation failures

### WARNING (Yellow) - Degraded Operations
Unexpected conditions that don't stop processing:

```
2026-05-19 10:25:30.456 - app.services - WARNING - [article_service.py:210] - create_from_url() - Duplicate URL detected
2026-05-19 10:25:31.567 - app.integrations - WARNING - [llm_client.py:95] - generate() - LLM provider degraded, using fallback
```

**Common WARNING scenarios:**
- Duplicate article URLs
- LLM fallback activation
- Missing optional fields
- Retry attempts

### INFO (Blue) - Normal Operations
Key milestones and important state changes:

```
2026-05-19 10:20:00.000 - app.services - INFO - [article_service.py:205] - create_from_url() - Starting article creation from URL
2026-05-19 10:20:05.123 - app.services - INFO - [article_service.py:245] - create_from_url() - 🔴 CRITICAL: Scraping URL with Crawl4AI
2026-05-19 10:20:15.789 - app.services - INFO - [article_service.py:260] - create_from_url() - Processing extracted content with AI
2026-05-19 10:20:25.456 - app.services - INFO - [article_service.py:285] - create_from_url() - Saving article to DynamoDB
2026-05-19 10:20:26.012 - app.services - INFO - [article_service.py:287] - create_from_url() - ✅ Article created successfully
```

**Common INFO scenarios:**
- Article creation start/completion
- Service initialization
- Major pipeline milestones
- Success confirmations (with ✅)

### DEBUG (Gray) - Development Details
Detailed diagnostic information (development only):

```
2026-05-19 10:15:30.111 - app.services - DEBUG - [article_service.py:42] - __init__() - ArticleService initialized
2026-05-19 10:15:30.222 - app.services - DEBUG - [article_service.py:98] - get_article_by_slug() - Fetching article by slug: my-article-title
2026-05-19 10:15:30.333 - app.repositories - DEBUG - [article_repository.py:35] - get_by_slug() - Querying article by slug: my-article-title
2026-05-19 10:15:30.444 - app.services - DEBUG - [scraping_service.py:65] - scrape_url() - AsyncWebCrawler instance created
```

**Only shown when ENVIRONMENT=local (debug=true)**

---

## Tracing Article Creation Pipeline

When you create an article from a URL, here's what to look for in logs:

### Terminal Output (INFO level):
```
$ uvicorn app.main:app --reload

2026-05-19 10:20:00.000 - app.services - INFO - Starting article creation from URL: https://example.com/article
2026-05-19 10:20:05.123 - app.services - INFO - 🔴 CRITICAL: Scraping URL with Crawl4AI
2026-05-19 10:20:15.789 - app.services - INFO - Processing extracted content with AI
2026-05-19 10:20:25.456 - app.services - INFO - Saving article to DynamoDB
2026-05-19 10:20:26.012 - app.services - INFO - ✅ Article created successfully
```

### Check Detailed Logs:
```bash
# View service operations
tail -f logs/services.log

# View database operations
tail -f logs/database.log

# View integrations (Crawl4AI, LLM)
tail -f logs/integrations.log

# View all combined
tail -f logs/app.log
```

### Example services.log output:
```
2026-05-19 10:20:00.000 - app.services.article_service - DEBUG - [article_service.py:42] - __init__() - ArticleService initialized with repository: ArticleRepository
2026-05-19 10:20:00.123 - app.services.article_service - INFO - Starting article creation from URL: https://techcrunch.com/article
2026-05-19 10:20:00.234 - app.services.article_service - DEBUG - Validating URL format: https://techcrunch.com/article
2026-05-19 10:20:00.345 - app.services.article_service - DEBUG - Checking for duplicate URL: https://techcrunch.com/article
2026-05-19 10:20:05.123 - app.services.article_service - INFO - 🔴 CRITICAL: Scraping URL with Crawl4AI: https://techcrunch.com/article
2026-05-19 10:20:15.234 - app.services.scraping_service - INFO - 🔴 CRITICAL: Starting Crawl4AI scrape of URL: https://techcrunch.com/article
2026-05-19 10:20:15.345 - app.services.scraping_service - DEBUG - Validating URL: https://techcrunch.com/article
2026-05-19 10:20:15.456 - app.services.scraping_service - DEBUG - AsyncWebCrawler imported successfully
2026-05-19 10:20:15.567 - app.services.scraping_service - INFO - 🔴 Initializing AsyncWebCrawler for: https://techcrunch.com/article
2026-05-19 10:20:15.678 - app.services.scraping_service - DEBUG - AsyncWebCrawler instance created
2026-05-19 10:20:20.789 - app.services.scraping_service - DEBUG - Crawl4AI extraction successful
2026-05-19 10:20:20.890 - app.services.scraping_service - DEBUG -   - Markdown size: 2500 chars
2026-05-19 10:20:20.901 - app.services.scraping_service - DEBUG -   - HTML size: 5000 chars
2026-05-19 10:20:25.456 - app.services.article_processing_service - INFO - Processing URL content for: https://techcrunch.com/article
2026-05-19 10:20:25.567 - app.services.article_processing_service - DEBUG - Extracting clean text from HTML/markdown (size: 5000 chars)
2026-05-19 10:20:25.678 - app.services.article_processing_service - INFO - Generating title from content via LLM
2026-05-19 10:20:25.789 - app.services.article_processing_service - INFO - Generating summary and extracting passages via LLM
2026-05-19 10:20:25.890 - app.services.article_processing_service - INFO - Detecting content category via LLM
2026-05-19 10:20:26.001 - app.services.article_processing_service - INFO - Generating semantic tags via LLM
2026-05-19 10:20:26.112 - app.services.article_processing_service - INFO - Structuring content as markdown
2026-05-19 10:20:26.223 - app.services.article_processing_service - INFO - ✅ URL content processing complete in 1.22s
2026-05-19 10:20:26.334 - app.repositories.article_repository - INFO - Creating article in DynamoDB: uuid-here
2026-05-19 10:20:26.445 - app.repositories.article_repository - INFO - ✅ Article created successfully: uuid-here
2026-05-19 10:20:26.556 - app.services.article_service - INFO - ✅ Article created successfully: uuid-here (slug: my-article-title)
```

---

## Common Debugging Scenarios

### Scenario 1: Article Creation Fails

**Look for in logs/services.log:**
```
ERROR - 🔴 Crawl4AI scraping failed for https://example.com: Connection timeout
```

**Action:** Check if the URL is accessible, network connectivity, Crawl4AI installation.

**Look for in logs/integrations.log:**
```
ERROR - 🔴 CRITICAL: Crawl4AI library not installed
```

**Action:** Run `pip install crawl4ai` in backend venv.

### Scenario 2: LLM Processing Fails

**Look for in logs/integrations.log:**
```
ERROR - LLM provider 'bedrock' health check failed: InvalidRegionError
```

**Action:** Check AWS region (should be us-west-2), verify AWS credentials via `aws sts get-caller-identity`.

**Look for in logs/services.log:**
```
ERROR - ❌ Error processing URL content: APIConnectionError: Failed to connect to Bedrock
```

**Action:** Ensure AWS credentials are configured, check internet connectivity to Bedrock.

### Scenario 3: Database Operations Fail

**Look for in logs/database.log:**
```
ERROR - ❌ Failed to create article: ResourceNotFoundException
```

**Action:** Verify DynamoDB tables exist and have correct table name prefix (`tech-news-`).

**Check tables:**
```bash
python scripts/create_tables_boto3.py
```

### Scenario 4: Duplicate URL Error

**Look for in logs/services.log:**
```
WARNING - Duplicate URL detected: https://example.com/article (existing article: uuid-123)
```

**Action:** This is expected - the same article is being added twice. Try a different URL.

---

## Configuration

Log configuration is in `app/core/logging.py`:

- **Console output:** INFO level and above
- **File output:** DEBUG level and above (development) or INFO level (production)
- **Log format:** `%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s`
- **Example:** `2026-05-19 10:20:26.012 - app.services.article_service - INFO - [article_service.py:287] - create_from_url() - ✅ Article created successfully`

### Change Log Level

In `app/config.py`:
```python
DEBUG=True   # Sets log level to DEBUG (development)
DEBUG=False  # Sets log level to INFO (production)
```

---

## Viewing Logs

### Real-time Monitoring (Development)

```bash
# Watch all logs
tail -f logs/app.log

# Watch specific component
tail -f logs/services.log
tail -f logs/integrations.log
tail -f logs/database.log

# Search for errors
grep "ERROR" logs/*.log
grep "CRITICAL" logs/*.log
```

### Search and Filter

```bash
# Find all article creations
grep "Starting article creation" logs/services.log

# Find all Crawl4AI operations
grep "CRITICAL" logs/integrations.log

# Find errors in DynamoDB operations
grep "ERROR" logs/database.log | head -20

# Find by timestamp
grep "2026-05-19 10:20" logs/app.log
```

### Analyze Performance

```bash
# Check how long operations take
grep "complete in" logs/services.log

# Example: "URL content processing complete in 1.22s"
```

---

## Log Rotation

Logs automatically rotate when they reach **10MB**:

```
logs/app.log           (current, growing)
logs/app.log.1         (first backup, ~10MB)
logs/app.log.2         (second backup, ~10MB)
logs/app.log.3         (etc.)
...
logs/app.log.10        (oldest backup)
```

After 10 backups, the oldest is deleted. This keeps total disk usage ~100MB per log file.

---

## Best Practices

### When Adding New Logging

Use this pattern:

```python
logger = logging.getLogger(__name__)  # At module level

# In your method
logger.debug(f"Starting operation with param: {param}")  # Development details
logger.info(f"Operation started")  # Key milestones
logger.warning(f"Unexpected condition occurred")  # Non-fatal issues
logger.error(f"❌ Operation failed: {error}")  # Fatal errors
```

### Naming Conventions

- Use **emoji + message** for significant milestones:
  - 🔴 CRITICAL: Crawl4AI scraping
  - ✅ Success: Article created
  - ❌ Error: Failed to process
- Include relevant IDs (article_id, user_id, URL)
- Include timing for performance tracking
- Include error types and messages

### Sensitive Data

**Never log:**
- Passwords, API keys
- Full JWT tokens
- User email addresses (only log user_id)
- Credit card numbers

**Safe to log:**
- URLs
- Article IDs, user IDs
- Categories, tags
- HTTP status codes
- Timing information

---

## Troubleshooting Logging Issues

### Problem: Logs not being written

**Check:**
1. `logs/` directory exists and is writable:
   ```bash
   ls -la logs/
   ```

2. Logging is configured in main.py startup:
   ```python
   configure_logging()  # Should be called in lifespan
   ```

3. Check file permissions:
   ```bash
   chmod 755 logs/
   ```

### Problem: Logs are truncated or missing

**Check:**
1. Log rotation happened - check backup files
2. Disk space available:
   ```bash
   df -h  # Check free space
   ```

3. Increase rotation size in `app/core/logging.py`:
   ```python
   maxBytes=20 * 1024 * 1024,  # Change from 10MB to 20MB
   ```

### Problem: Performance impact from logging

**Optimize:**
1. Reduce DEBUG logs in production (set DEBUG=False)
2. Use lazy logging for expensive operations:
   ```python
   logger.debug(f"Content: {content[:100]}")  # Good
   logger.debug(f"Content: {expensive_function()}")  # Bad
   ```

---

**For questions:** Check logs first, then ask the development team.
