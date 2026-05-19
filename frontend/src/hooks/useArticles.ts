/**
 * Hooks for fetching articles and mutations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { articleKeys } from '@/lib/queryKeys';
import {
  fetchArticles,
  fetchTrendingArticles,
  fetchArticleBySlug,
  createArticle,
  createArticleFromUrl,
  updateArticle,
  deleteArticle,
  type CreateArticleRequest,
  type UpdateArticleRequest,
  type CreateArticleFromUrlRequest,
} from '@/lib/api/articles';
import type { ArticleListParams } from '@/types/article';

export function useArticles(params: ArticleListParams = {}) {
  return useQuery({
    queryKey: articleKeys.list(params),
    queryFn: () => fetchArticles(params),
    staleTime: 1000 * 60 * 2,
  });
}

export function useFeaturedArticles(limit: number = 3) {
  return useQuery({
    queryKey: articleKeys.featured(limit),
    queryFn: () => fetchArticles({ limit }),
    staleTime: 1000 * 60 * 5,
  });
}

export function useLatestArticles(limit: number = 10) {
  return useQuery({
    queryKey: articleKeys.latest(limit),
    queryFn: () => fetchArticles({ limit }),
    staleTime: 1000 * 60 * 5,
  });
}

export function useTrendingArticles(limit: number = 10) {
  return useQuery({
    queryKey: articleKeys.trending(limit),
    queryFn: () => fetchTrendingArticles(limit),
    staleTime: 1000 * 60 * 5,
  });
}

export function useArticleBySlug(slug: string) {
  return useQuery({
    queryKey: articleKeys.detail(slug),
    queryFn: () => fetchArticleBySlug(slug),
    staleTime: 1000 * 60 * 10,
    enabled: !!slug,
  });
}

export function useCreateArticle() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateArticleRequest) => createArticle(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: articleKeys.lists() });
    },
  });
}

export function useCreateArticleFromUrl() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateArticleFromUrlRequest) => createArticleFromUrl(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: articleKeys.lists() });
    },
  });
}

export function useUpdateArticle() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ slug, data }: { slug: string; data: UpdateArticleRequest }) =>
      updateArticle(slug, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: articleKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: articleKeys.detail(data.data.slug),
      });
    },
  });
}

export function useDeleteArticle() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (slug: string) => deleteArticle(slug),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: articleKeys.lists() });
    },
  });
}
