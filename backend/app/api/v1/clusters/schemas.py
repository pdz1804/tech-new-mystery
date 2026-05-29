"""Cluster request/response schemas."""

from pydantic import BaseModel, Field, ConfigDict


class TopArticleItem(BaseModel):
    """Top article in a cluster."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    engagement_score: float


class ClusterSummary(BaseModel):
    """Cluster summary for list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique cluster identifier")
    label: str = Field(..., description="Auto-generated cluster label")
    description: str = Field(..., description="Cluster description")
    article_count: int = Field(..., description="Number of articles in cluster")
    top_articles: list[TopArticleItem] = Field(
        default_factory=list, description="Top articles by engagement (up to 10)"
    )
    confidence: float | None = Field(
        None, ge=0, le=1, description="Average confidence score when available"
    )
    keywords: list[str] = Field(default_factory=list, description="Top 5 keywords")
    size_category: str = Field(..., description="SMALL, MEDIUM, or LARGE")
    diversity_score: float = Field(
        ..., ge=0, le=1, description="Cluster diversity score"
    )
    created_at: float = Field(..., description="Creation Unix timestamp")
    updated_at: float = Field(..., description="Last update Unix timestamp")


class PaginationInfo(BaseModel):
    """Pagination information."""

    total_count: int = Field(..., description="Total items across all pages")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class ClusterListResponse(BaseModel):
    """Response for GET /v1/clusters."""

    clusters: list[ClusterSummary] = Field(..., description="List of clusters")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")


class ArticleInCluster(BaseModel):
    """Article in a cluster (with confidence score)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    summary: str | None = None
    source: str
    published_at: float | None = None
    engagement_score: float
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Confidence this article belongs in cluster"
    )
    preview_image: str | None = None
    url: str


class ClusterMetrics(BaseModel):
    """Clustering quality metrics for a cluster."""

    silhouette_score: float | None = Field(
        None, description="Silhouette score (-1 to 1)"
    )
    davies_bouldin_index: float | None = Field(None, description="Davies-Bouldin index")
    calinski_harabasz_index: float | None = Field(
        None, description="Calinski-Harabasz index"
    )


class ClusterDetail(BaseModel):
    """Cluster detail response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique cluster identifier")
    label: str = Field(..., description="Auto-generated cluster label")
    description: str = Field(..., description="Cluster description")
    article_count: int = Field(..., description="Number of articles in cluster")
    keywords: list[str] = Field(default_factory=list, description="Top 5 keywords")
    size_category: str = Field(..., description="SMALL, MEDIUM, or LARGE")
    diversity_score: float = Field(
        ..., ge=0, le=1, description="Cluster diversity score"
    )
    confidence: float = Field(..., ge=0, le=1, description="Average confidence score")
    articles: list[ArticleInCluster] = Field(
        default_factory=list, description="Paginated articles in cluster"
    )
    pagination: PaginationInfo = Field(..., description="Article pagination info")
    metrics: ClusterMetrics = Field(..., description="Clustering quality metrics")
    updated_at: float = Field(..., description="Last update Unix timestamp")


class ClusterArticlesResponse(BaseModel):
    """Response for GET /v1/clusters/{cluster_id}/articles."""

    articles: list[ArticleInCluster] = Field(..., description="List of articles")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")


class TrendingClusterSummary(BaseModel):
    """Trending cluster summary."""

    model_config = ConfigDict(from_attributes=True)

    cluster_id: str
    label: str
    article_count: int
    trending_rank: int = Field(..., ge=1, le=5, description="Rank 1-5")
    momentum_score: float = Field(
        ..., ge=0, le=1, description="Trending momentum (engagement growth)"
    )
    engagement_trend: str = Field(..., description="UP, STABLE, or DOWN")
    articles_added_last_hour: int = Field(..., ge=0, description="New articles in last hour")
    keywords: list[str] = Field(default_factory=list)


class TrendingClustersResponse(BaseModel):
    """Response for GET /v1/clusters/trending."""

    trending_clusters: list[TrendingClusterSummary] = Field(
        ..., description="Top trending clusters (max 5)"
    )
