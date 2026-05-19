# Tech News Mystery

A modern full-stack web application for discovering, reading, and discussing tech news articles.

## Features

- **User Authentication**: Secure JWT-based authentication (1-day tokens)
- **Article Management**: Create, read, update, delete articles with AI-powered processing
- **Intelligent Content Extraction**: Crawl4AI for LLM-friendly markdown extraction (NOT BeautifulSoup)
- **AI Processing**: Claude 3.5 Haiku (via Bedrock) + OpenAI fallback for titles, summaries, categories, tags
- **Article Engagement**: Like, save, view count tracking
- **Admin Search**: Tavily API integration for topic-based article discovery
- **Role-Based Access**: Admin and user roles with proper authorization
- **Responsive Design**: Mobile-first responsive design (375px+)
- **Real AWS**: DynamoDB in us-west-2, Redis, IAM role-based auth

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: AWS DynamoDB (us-west-2, real AWS)
- **Cache**: Redis (Docker for dev, ElastiCache for prod)
- **Task Queue**: Celery with Redis broker
- **Web Scraping**: Crawl4AI (intelligent content extraction, NOT BeautifulSoup)
- **LLM**: Claude 3.5 Haiku (AWS Bedrock) + OpenAI GPT-4o-mini fallback
- **Search**: Tavily Search API
- **Authentication**: JWT tokens (1-day expiration)
- **Authorization**: Role-based access control (admin/user)

### Frontend
- **Framework**: Next.js 14 with React 18 (TypeScript)
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **UI Components**: Lucide icons, Framer Motion
- **Responsive**: Mobile-first design (375px+)

## Getting Started

### Test Accounts (Pre-Created for Development)

**Admin Account** (full system access):
```
Username: admin
Email: admin@example.com
Password: admin123
Role: admin (can search Tavily, manage users, all articles)
```

**User Account** (standard user features):
```
Username: testuser
Email: user@example.com
Password: user123
Role: user (create/manage own articles, like/save, engage)
```

⚠️ **These accounts are created automatically when backend starts.** Use them for API testing.

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (for Redis only - local dev)
- AWS credentials configured (for DynamoDB)
- AWS Bedrock access (us-west-2)
- OpenAI API key (for fallback)
- Tavily API key (for search)

### Quick Start

**For 5-minute setup with Docker:** See [QUICK_START.md](QUICK_START.md)

**For manual terminal startup:** See [MANUAL_STARTUP.md](MANUAL_STARTUP.md)

**For detailed setup:** See [SETUP.md](SETUP.md)

#### Quick Reference

```bash
# 1. Start Redis (Terminal 1)
cd infra && docker-compose up redis

# 2. Start Backend (Terminal 2)
cd backend
python -m venv venv && venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload

# 3. Start Frontend (Terminal 3)
cd frontend && npm install && npm run dev

# 4. Create DynamoDB tables (Terminal 4)
cd backend && python scripts/create_tables_boto3.py
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`

## API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/auth/register` | Register new user |
| POST | `/v1/auth/login` | Login user |
| GET | `/v1/auth/me` | Get current user |
| GET | `/v1/articles` | List articles |
| GET | `/v1/articles/{slug}` | Get article details |
| GET | `/v1/search` | Search articles |
| GET | `/v1/trending` | Get trending articles |
| GET | `/v1/comments/{article_id}` | Get article comments |
| POST | `/v1/comments` | Create comment |

## Error Handling

All API errors return structured responses with proper HTTP status codes and semantic error codes:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": []
  }
}
```

Error codes include: `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `DUPLICATE`, `VALIDATION_ERROR`, `INTERNAL_SERVER_ERROR`.

## Testing

Run the test suite:

```bash
cd backend
source venv/Scripts/activate
python -m pytest tests/ -v
```

**Test Coverage**: 183 tests passing with 64% code coverage

## Development

### Code Style
- Follow PEP 8 for Python
- Use ESLint and Prettier for JavaScript
- Match existing code patterns

### Making Changes
1. Create a feature branch
2. Make your changes
3. Run tests to ensure nothing breaks
4. Submit a pull request

## Deployment

The application is containerized and can be deployed using Docker:

```bash
docker-compose up -d
```

See deployment documentation for cloud provider instructions.

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
