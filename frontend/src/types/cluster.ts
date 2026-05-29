/**
 * Cluster types matching backend schemas.
 */

export interface ClusterArticle {
  id: string;
  title: string;
  engagement_score: number;
  confidence_score?: number;
  published_at?: string;
}

export interface Cluster {
  id: string;
  label: string;
  description: string;
  keywords: string[];
  article_count: number;
  size_category: 'SMALL' | 'MEDIUM' | 'LARGE';
  diversity_score: number;
  top_articles: ClusterArticle[];
  created_at: number;
  updated_at: number;
}

export interface ClusterListResponse {
  success?: boolean;
  clusters: Cluster[];
  pagination: {
    total_count: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

export interface ClusterDetailResponse {
  success?: boolean;
  id: string;
  label: string;
  description: string;
  keywords: string[];
  article_count: number;
  size_category: 'SMALL' | 'MEDIUM' | 'LARGE';
  diversity_score: number;
  articles: Array<ArticleInCluster>;
  pagination: {
    total_count: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

export interface ArticleInCluster {
  id: string;
  title: string;
  summary?: string;
  source: string;
  published_at: number;
  engagement_score: number;
  confidence_score: number;
  url: string;
}

export interface ClusterListParams {
  page?: number;
  page_size?: number;
  sort_by?: 'size' | 'recency' | 'diversity';
  keyword?: string;
}
