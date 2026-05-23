"""Search business logic service."""

import logging
from typing import Optional
from app.repositories.article_repository import ArticleRepository
from app.config import settings

logger = logging.getLogger(__name__)


class SearchService:
    """Search service for business logic."""

    def __init__(self, article_repo: ArticleRepository) -> None:
        """Initialize service."""
        self._article_repo = article_repo

    async def search(
        self,
        query: str,
        limit: int = 20,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Search articles by query and optional filters.

        Returns:
            dict: Results with matching articles and metadata
        """
        try:
            if not query or not query.strip():
                return {
                    "query": query,
                    "results": [],
                    "total": 0,
                    "filters": {"category": category, "tags": tags},
                }

            # Get all articles (DynamoDB lacks native full-text search)
            articles, _ = await self._article_repo.list_all(limit=1000)

            if not articles:
                return {
                    "query": query,
                    "results": [],
                    "total": 0,
                    "filters": {"category": category, "tags": tags},
                }

            # Filter and score results
            query_lower = query.lower()
            scored_results = []

            for article in articles:
                if not article.is_published:
                    continue

                score = self._calculate_relevance_score(article, query_lower)

                if score > 0:
                    # Apply category filter
                    if category and getattr(article, "category", "").lower() != category.lower():
                        continue

                    # Apply tags filter
                    if tags:
                        article_tags = [
                            t.lower() for t in getattr(article, "tags", [])
                        ]
                        if not any(tag.lower() in article_tags for tag in tags):
                            continue

                    scored_results.append((score, article))

            # Sort by score descending
            scored_results.sort(key=lambda x: x[0], reverse=True)

            # Format results
            results = [
                self._format_article(article) for _, article in scored_results[:limit]
            ]

            return {
                "query": query,
                "results": results,
                "total": len(results),
                "filters": {"category": category, "tags": tags},
            }

        except Exception as e:
            logger.error(f"Search error for query '{query}': {e}")
            return {
                "query": query,
                "results": [],
                "total": 0,
                "error": str(e),
            }

    def _calculate_relevance_score(self, article, query_lower: str) -> float:
        """Calculate relevance score for article.

        Scoring rules:
        - Title exact match: 100 points
        - Title contains query: 50 points
        - Content contains query: 20 points
        - Tag match: 15 points each
        """
        score = 0.0
        title = (getattr(article, "title", "") or "").lower()
        content = (getattr(article, "content", "") or "").lower()
        summary = (getattr(article, "summary", "") or "").lower()
        tags = [t.lower() for t in getattr(article, "tags", [])]

        # Title scoring
        if title == query_lower:
            score += 100
        elif query_lower in title:
            score += 50

        # Content scoring
        content_matches = content.count(query_lower)
        if content_matches > 0:
            score += min(content_matches * 5, 100)

        # Summary scoring
        if query_lower in summary:
            score += 30

        # Tag scoring
        for tag in tags:
            if query_lower == tag or query_lower in tag:
                score += 15

        return score

    def _format_article(self, article) -> dict:
        """Format article for response."""
        return {
            "article_id": article.article_id,
            "title": article.title,
            "slug": article.slug,
            "summary": article.summary,
            "category": article.category,
            "tags": getattr(article, "tags", []),
            "published_at": getattr(article, "published_at", None),
            "view_count": getattr(article, "view_count", 0),
        }

    async def tavily_search(
        self,
        query: str,
        include_domains: Optional[list[str]] = None,
        start_date: Optional[str] = None,
        search_depth: Optional[str] = None,
    ) -> dict:
        """
        Search web using Tavily Search API for tech news and articles.

        Args:
            query: The search query
            include_domains: List of domains to search in (default: tech news domains)
            start_date: Search from this date onwards (format: YYYY-MM-DD)
            search_depth: 'basic' or 'advanced' search depth (default: 'basic')

        Returns:
            dict with keys:
            - success: Boolean indicating if search succeeded
            - query: The original query
            - results: List of search results [{url, title, description, source, published_date}, ...]
            - count: Number of results returned
            - error: Error message if search failed
        """
        if not query or not query.strip():
            return {
                "success": False,
                "query": query,
                "results": [],
                "count": 0,
                "error": "Query cannot be empty"
            }

        # Default tech domains filter
        if not include_domains:
            include_domains = [
                "techcrunch.com",
                "arxiv.org",
                "github.com",
                "medium.com",
                "dev.to",
                "hackernews.org",
                "twitter.com",
                "thenextweb.com",
                "wired.com",
                "theverge.com",
            ]

        api_key = settings.tavily_api_key
        if not api_key:
            logger.error("TAVILY_API_KEY not configured")
            return {
                "success": False,
                "query": query,
                "results": [],
                "count": 0,
                "error": "Tavily API key not configured"
            }

        try:
            from tavily import TavilyClient

            logger.info(f"[TAVILY_SEARCH] Initializing TavilyClient with API key")
            client = TavilyClient(api_key=api_key)

            # Build search parameters for Tavily API
            search_params = {
                "query": query,
                "search_depth": search_depth or "basic",
                "include_raw_content": "markdown",
            }

            # Add optional parameters if provided
            if start_date:
                search_params["start_date"] = start_date

            # Execute search with parameters
            logger.info(f"[TAVILY_SEARCH] Searching query='{query}', start_date={start_date}, search_depth={search_depth}...")
            response = client.search(**search_params)

            logger.info(f"[TAVILY_SEARCH] Response received: {len(response.get('results', []))} results")

            # Format results
            results = []
            for item in response.get("results", []):
                results.append({
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "description": item.get("content", ""),
                    "source": item.get("source", ""),
                    "published_date": item.get("published_date"),
                })

            logger.info(f"[TAVILY_SEARCH] Formatted {len(results)} results")
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results),
                "error": None
            }

        except ImportError:
            logger.error("Tavily library not installed. Install with: pip install tavily-python")
            return {
                "success": False,
                "query": query,
                "results": [],
                "count": 0,
                "error": "Tavily library not installed"
            }
        except Exception as e:
            logger.error(f"Error searching with Tavily: {str(e)}", exc_info=True)
            logger.error(f"[TAVILY_SEARCH] Search params used: {search_params}")
            return {
                "success": False,
                "query": query,
                "results": [],
                "count": 0,
                "error": f"Search failed: {str(e)}"
            }

    async def newsapi_search(
        self,
        query: str,
        limit: int = 10,
        from_date: Optional[str] = None,
        sort_by: Optional[str] = None,
        sources: Optional[list[str]] = None,
    ) -> dict:
        """
        Search news using NewsAPI for tech news and articles.

        Args:
            query: The search query
            limit: Maximum number of results (default 10)
            from_date: Search from this date onwards (format: YYYY-MM-DD)
            sort_by: Sort results by 'popularity', 'publishedAt', or 'relevancy'
            sources: List of source IDs to filter by (e.g., ['techcrunch', 'the-verge'])

        Returns:
            dict with keys:
            - success: Boolean indicating if search succeeded
            - query: The original query
            - results: List of search results [{url, title, description, source, published_date}, ...]
            - count: Number of results returned
            - error: Error message if search failed
        """
        if not query or not query.strip():
            return {
                "success": False,
                "query": query,
                "results": [],
                "count": 0,
                "error": "Query cannot be empty"
            }

        api_key = settings.newsapi_key
        if not api_key:
            logger.error("NEWSAPI_KEY not configured")
            return {
                "success": False,
                "query": query,
                "results": [],
                "count": 0,
                "error": "NewsAPI key not configured"
            }

        try:
            import newsapi
            from newsapi import NewsApiClient

            logger.info(f"[NEWSAPI_SEARCH] Initializing NewsAPI client")
            client = NewsApiClient(api_key=api_key)

            # Build search parameters
            search_params = {
                "q": query,
                "language": "en",
                "page_size": limit,
                "sort_by": sort_by or "publishedAt",
            }

            # Add optional date filter if provided (use 'from_param' to avoid reserved keyword)
            if from_date:
                search_params["from_param"] = from_date
                logger.debug(f"[NEWSAPI_SEARCH] Added from_date filter: {from_date}")

            # Add optional sources filter if provided
            if sources:
                search_params["sources"] = ",".join(sources)
                logger.debug(f"[NEWSAPI_SEARCH] Added sources filter: {sources}")

            # Search for articles
            logger.info(f"[NEWSAPI_SEARCH] Searching query='{query}', limit={limit}, from_date={from_date}, sources={sources}, sort_by={sort_by or 'publishedAt'}...")
            logger.debug(f"[NEWSAPI_SEARCH] Search params: {search_params}")

            response = client.get_everything(**search_params)

            if response.get("status") != "ok":
                logger.warning(f"[NEWSAPI_SEARCH] NewsAPI error: {response.get('message')}")
                return {
                    "success": False,
                    "query": query,
                    "results": [],
                    "count": 0,
                    "error": response.get("message", "NewsAPI request failed")
                }

            logger.info(f"[NEWSAPI_SEARCH] Response received: {len(response.get('articles', []))} results")

            # Format results
            results = []
            for item in response.get("articles", []):
                results.append({
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "source": item.get("source", {}).get("name", ""),
                    "published_date": item.get("publishedAt"),
                })

            logger.info(f"[NEWSAPI_SEARCH] Formatted {len(results)} results")
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results),
                "error": None
            }

        except ImportError as e:
            logger.error(f"NewsAPI library not installed: {str(e)}")
            return {
                "success": False,
                "query": query,
                "results": [],
                "count": 0,
                "error": "NewsAPI library not installed"
            }
        except TypeError as e:
            logger.error(f"NewsAPI parameter error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "query": query,
                "results": [],
                "count": 0,
                "error": f"Invalid parameter: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error searching with NewsAPI: {str(e)}", exc_info=True)
            return {
                "success": False,
                "query": query,
                "results": [],
                "count": 0,
                "error": f"Search failed: {str(e)}"
            }
