/**
 * Search API functions.
 */

import { apiClient } from './client';
import type { ArticleListResponse } from '@/types/article';

export interface SearchParams {
  q: string;
  category?: string;
  source_id?: string;
  page?: number;
  limit?: number;
}

export async function searchArticles(params: SearchParams): Promise<ArticleListResponse> {
  const response = await apiClient.get<ArticleListResponse>('/search', { params });
  return response.data;
}
