/**
 * Hooks for fetching clusters and cluster details.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

interface ClusterListParams {
  page?: number;
  page_size?: number;
  sort_by?: 'size' | 'recency' | 'diversity';
}

interface ClusterArticlesParams {
  page?: number;
  page_size?: number;
  sort?: 'date' | 'engagement' | 'title';
}

interface PaginationInfo {
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface TopArticle {
  id: string;
  title: string;
  engagement_score: number;
}

interface ClusterSummary {
  id: string;
  label: string;
  description: string;
  article_count: number;
  top_articles: TopArticle[];
  confidence: number;
  keywords: string[];
  size_category: string;
  diversity_score: number;
  created_at: number;
  updated_at: number;
}

interface ClusterListResponse {
  clusters: ClusterSummary[];
  pagination: PaginationInfo;
}

interface ArticleInCluster {
  id: string;
  title: string;
  summary: string | null;
  source: string;
  published_at: number | null;
  engagement_score: number;
  confidence_score: number;
  preview_image: string | null;
  url: string;
}

interface ClusterMetrics {
  silhouette_score: number | null;
  davies_bouldin_index: number | null;
  calinski_harabasz_index: number | null;
}

interface ClusterDetail {
  id: string;
  label: string;
  description: string;
  article_count: number;
  keywords: string[];
  size_category: string;
  diversity_score: number;
  confidence: number;
  articles: ArticleInCluster[];
  pagination: PaginationInfo;
  metrics: ClusterMetrics;
  updated_at: number;
}

interface ClusterArticlesResponse {
  articles: ArticleInCluster[];
  pagination: PaginationInfo;
}

interface TrendingCluster {
  cluster_id: string;
  label: string;
  article_count: number;
  trending_rank: number;
  momentum_score: number;
  engagement_trend: string;
  articles_added_last_hour: number;
  keywords: string[];
}

interface TrendingClustersResponse {
  trending_clusters: TrendingCluster[];
}

export function useClusters(params: ClusterListParams = {}) {
  const queryParams = new URLSearchParams();
  if (params.page) queryParams.append('page', params.page.toString());
  if (params.page_size) queryParams.append('page_size', params.page_size.toString());
  if (params.sort_by) queryParams.append('sort_by', params.sort_by);

  return useQuery({
    queryKey: ['clusters', params],
    queryFn: async () => {
      const { data } = await apiClient.get<ClusterListResponse>(
        `/clusters?${queryParams.toString()}`
      );
      return data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useClusterDetail(cluster_id: string | null) {
  return useQuery({
    queryKey: ['clusters', cluster_id, 'detail'],
    queryFn: async () => {
      if (!cluster_id) return null;
      const { data } = await apiClient.get<ClusterDetail>(
        `/clusters/${cluster_id}`
      );
      return data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: !!cluster_id,
  });
}

export function useClusterArticles(
  cluster_id: string | null,
  params: ClusterArticlesParams = {}
) {
  const queryParams = new URLSearchParams();
  if (params.page) queryParams.append('page', params.page.toString());
  if (params.page_size) queryParams.append('page_size', params.page_size.toString());
  if (params.sort) queryParams.append('sort', params.sort);

  return useQuery({
    queryKey: ['clusters', cluster_id, 'articles', params],
    queryFn: async () => {
      if (!cluster_id) return null;
      const { data } = await apiClient.get<ClusterArticlesResponse>(
        `/clusters/${cluster_id}/articles?${queryParams.toString()}`
      );
      return data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: !!cluster_id,
  });
}

export function useTrendingClusters(limit: number = 5) {
  return useQuery({
    queryKey: ['clusters', 'trending', limit],
    queryFn: async () => {
      const { data } = await apiClient.get<TrendingClustersResponse>(
        `/clusters/trending?limit=${limit}`
      );
      return data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export type {
  ClusterListParams,
  ClusterArticlesParams,
  PaginationInfo,
  TopArticle,
  ClusterSummary,
  ClusterListResponse,
  ArticleInCluster,
  ClusterMetrics,
  ClusterDetail,
  ClusterArticlesResponse,
  TrendingCluster,
  TrendingClustersResponse,
};

// Keep backwards-compat alias so old pages using useClusters still compile
export type { ClusterDetail as ClusterDetailData };
