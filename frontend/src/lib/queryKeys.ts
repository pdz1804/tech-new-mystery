/**
 * React Query key factory for type-safe query keys.
 * All query keys are centralized here to avoid hardcoded strings.
 */

import type { ArticleListParams } from '@/types/article';

export const articleKeys = {
  all: ['articles'] as const,
  lists: () => [...articleKeys.all, 'list'] as const,
  list: (params: ArticleListParams) => [...articleKeys.lists(), params] as const,
  details: () => [...articleKeys.all, 'detail'] as const,
  detail: (slug: string) => [...articleKeys.details(), slug] as const,
  trending: (limit?: number) => [...articleKeys.all, 'trending', limit] as const,
  featured: (limit?: number) => [...articleKeys.all, 'featured', limit] as const,
  latest: (limit?: number) => [...articleKeys.all, 'latest', limit] as const,
};

export const authKeys = {
  all: ['auth'] as const,
  me: () => [...authKeys.all, 'me'] as const,
};

export const commentKeys = {
  all: ['comments'] as const,
  byArticle: (articleId: string) => [...commentKeys.all, articleId] as const,
};

export const searchKeys = {
  all: ['search'] as const,
  results: (query: string) => [...searchKeys.all, 'results', query] as const,
};

export const userKeys = {
  all: ['user'] as const,
  saves: () => [...userKeys.all, 'saves'] as const,
  preferences: () => [...userKeys.all, 'preferences'] as const,
  submissions: () => [...userKeys.all, 'submissions'] as const,
};

export const sourceKeys = {
  all: ['sources'] as const,
  lists: () => [...sourceKeys.all, 'list'] as const,
};
