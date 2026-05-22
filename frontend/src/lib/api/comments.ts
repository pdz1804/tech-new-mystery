/**
 * Comments API functions.
 */

import { apiClient } from './client';
import type { CommentListResponse } from '@/types/comment';

export async function fetchArticleComments(articleId: string): Promise<CommentListResponse> {
  const response = await apiClient.get<CommentListResponse>(`/articles/${articleId}/comments`);
  return response.data;
}

export async function createComment(articleId: string, content: string): Promise<{ data: { comment_id: string; content: string; author?: string; created_at: string } }> {
  const response = await apiClient.post(`/articles/${articleId}/comments`, { content });
  return response.data;
}
