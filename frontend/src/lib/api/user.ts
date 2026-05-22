/**
 * User API functions.
 */

import { apiClient } from './client';

interface UserPreferences {
  theme?: string;
  notifications_enabled?: boolean;
  notification_enabled?: boolean;
  preferred_categories?: string[];
  digest_frequency?: string;
  [key: string]: string | string[] | boolean | undefined;
}

interface SavedArticle {
  article_id: string;
  title: string;
  slug: string;
  published_at?: string;
  created_at: string;
  category?: string;
  view_count?: number;
  summary?: string;
}

export async function fetchUserPreferences(): Promise<UserPreferences> {
  const response = await apiClient.get<{ success: boolean; data: UserPreferences }>('/user/preferences');
  return response.data.data;
}

export async function updateUserPreferences(preferences: UserPreferences): Promise<UserPreferences> {
  const response = await apiClient.put<{ success: boolean; data: UserPreferences }>('/user/preferences', preferences);
  return response.data.data;
}

export async function fetchSavedArticles(): Promise<SavedArticle[]> {
  const response = await apiClient.get<{ success: boolean; data: SavedArticle[] }>('/user/saves');
  return response.data.data;
}

export async function saveArticle(articleId: string): Promise<void> {
  await apiClient.post(`/user/saves/${articleId}`);
}

export async function unsaveArticle(articleId: string): Promise<void> {
  await apiClient.delete(`/user/saves/${articleId}`);
}
