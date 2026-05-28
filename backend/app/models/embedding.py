"""Pydantic schemas for embedding service."""

from pydantic import BaseModel
from typing import List


class EmbeddingRequest(BaseModel):
    """Request schema for embedding articles."""

    article_ids: List[str]
    force_regenerate: bool = False


class EmbeddingResponse(BaseModel):
    """Response schema for embedding operation."""

    article_id: str
    embedding: List[float]
    model: str
    cached: bool
    timestamp: int


class CachedEmbedding(BaseModel):
    """Schema for cached embedding in DynamoDB."""

    article_id: str
    embedding: List[float]
    model: str
    timestamp: int
