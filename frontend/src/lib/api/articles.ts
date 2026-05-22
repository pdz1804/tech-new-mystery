/**
 * Article API functions.
 * Plain async functions that call the backend.
 */

import { apiClient } from './client';
import type { ArticleListParams, ArticleListResponse, ArticleDetailResponse } from '@/types/article';

export async function fetchArticles(params: ArticleListParams = {}): Promise<ArticleListResponse> {
  const response = await apiClient.get<ArticleListResponse>('/articles', { params });
  return response.data;
}

export async function fetchArticleBySlug(slug: string): Promise<ArticleDetailResponse> {
  const response = await apiClient.get<ArticleDetailResponse>(`/articles/${slug}`);
  return response.data;
}

export async function fetchTrendingArticles(limit: number = 20): Promise<ArticleListResponse> {
  const response = await apiClient.get<ArticleListResponse>('/trending', {
    params: { limit },
  });
  return response.data;
}

export interface CreateArticleRequest {
  title: string;
  url: string;
  content?: string;
  author?: string;
  category?: string;
  tags?: string[];
  summary?: string;
}

export interface UpdateArticleRequest {
  title?: string;
  content?: string;
  author?: string;
  category?: string;
  tags?: string[];
  summary?: string;
}

export interface CreateArticleFromUrlRequest {
  url: string;
  title?: string;
  author?: string;
  auto_summarize?: boolean;
}

export async function createArticle(data: CreateArticleRequest): Promise<ArticleDetailResponse> {
  const response = await apiClient.post<ArticleDetailResponse>('/articles', data);
  return response.data;
}

export async function createArticleFromUrl(data: CreateArticleFromUrlRequest): Promise<ArticleDetailResponse> {
  const response = await apiClient.post<ArticleDetailResponse>('/articles/from-url', data);
  return response.data;
}

export async function updateArticle(slug: string, data: UpdateArticleRequest): Promise<ArticleDetailResponse> {
  const response = await apiClient.put<ArticleDetailResponse>(`/articles/${slug}`, data);
  return response.data;
}

export async function deleteArticle(slug: string): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.delete(`/articles/${slug}`);
  return response.data;
}
