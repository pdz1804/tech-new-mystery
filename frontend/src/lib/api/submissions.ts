/**
 * Article submissions API functions.
 */

import { apiClient } from './client';

interface ArticleSubmission {
  submission_id: string;
  url: string;
  article_id?: string;
  status: string;
  created_at: string;
}

export async function submitArticle(url: string): Promise<{ data: ArticleSubmission }> {
  const response = await apiClient.post('/user/submissions', { url });
  return response.data;
}

export async function fetchUserSubmissions(): Promise<{ data: ArticleSubmission[] }> {
  const response = await apiClient.get<{ data: ArticleSubmission[] }>('/user/submissions');
  return response.data;
}
