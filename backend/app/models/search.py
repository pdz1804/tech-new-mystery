"""Pydantic models for search requests and responses."""

from pydantic import BaseModel, Field
from typing import List, Optional


class HybridSearchRequest(BaseModel):
    """Request schema for hybrid search."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    dense_weight: float = Field(0.6, ge=0.0, le=1.0, description="Weight for dense search (0-1)")
    bm25_weight: float = Field(0.4, ge=0.0, le=1.0, description="Weight for BM25 search (0-1)")
    category: Optional[str] = Field(None, description="Optional category filter")


class SearchResultItem(BaseModel):
    """Single search result."""

    article_id: str
    title: str
    summary: str
    category: Optional[str] = None
    dense_score: Optional[float] = None
    bm25_score: Optional[float] = None
    hybrid_score: Optional[float] = None


class HybridSearchResponse(BaseModel):
    """Response schema for hybrid search."""

    success: bool
    query: str
    results: List[SearchResultItem]
    count: int
    time_ms: float = Field(..., description="Query execution time in milliseconds")
    error: Optional[str] = None


class QdrantStatsResponse(BaseModel):
    """Response schema for Qdrant collection statistics."""

    collection_name: str
    points_count: int
    vectors_count: int
    status: str


class QdrantStatsMetaResponse(BaseModel):
    """Wrapper response for Qdrant statistics."""

    success: bool
    data: QdrantStatsResponse
