'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowLeft, ChevronLeft, ChevronRight, ExternalLink, Zap } from 'lucide-react';
import { format } from 'date-fns';
import { useAuthStore } from '@/lib/stores/authStore';
import { apiClient } from '@/lib/api/client';
import { ArticleCardSkeleton } from '@/components/ui/Skeleton';
import { AppLoadingState } from '@/components/ui/AppLoadingState';
import type { ClusterDetailResponse } from '@/types/cluster';

interface DetailPageState {
  cluster: ClusterDetailResponse | null;
  loading: boolean;
  error: string | null;
  currentPage: number;
  pageSize: number;
}

export default function ClusterDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const clusterId = params.slug as string;

  const [state, setState] = useState<DetailPageState>({
    cluster: null,
    loading: true,
    error: null,
    currentPage: 1,
    pageSize: 20,
  });

  // Handle initial load and URL params
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    const pageParam = searchParams.get('page');
    if (pageParam) {
      setState((s) => ({ ...s, currentPage: parseInt(pageParam, 10) || 1 }));
    }
  }, [isAuthenticated, router, searchParams]);

  // Fetch cluster details
  useEffect(() => {
    const fetchClusterDetails = async () => {
      try {
        setState((s) => ({ ...s, loading: true, error: null }));

        const response = await apiClient.get<ClusterDetailResponse>(
          `/clusters/${clusterId}`,
          {
            params: {
              page: state.currentPage,
              page_size: state.pageSize,
            },
          }
        );

        setState((s) => ({
          ...s,
          cluster: response.data,
          loading: false,
        }));

        // Update URL
        const newParams = new URLSearchParams();
        newParams.set('page', state.currentPage.toString());
        router.push(`/topics/${clusterId}?${newParams.toString()}`, { scroll: false });
      } catch (error) {
        console.error('Failed to fetch cluster details:', error);
        setState((s) => ({
          ...s,
          error: 'Failed to load topic details. Please try again.',
          loading: false,
        }));
      }
    };

    if (clusterId) {
      fetchClusterDetails();
    }
  }, [clusterId, state.currentPage, state.pageSize, router]);

  const handlePageChange = (page: number) => {
    setState((s) => ({ ...s, currentPage: page }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const getVisiblePages = useMemo(() => {
    if (!state.cluster) return [];

    const currentPage = state.currentPage;
    const totalPages = state.cluster.pagination.total_pages;

    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }

    const pages: (number | string)[] = [];
    const firstPages = [1, 2];
    const lastPages = [totalPages - 1, totalPages];
    const neighbors = [currentPage - 1, currentPage, currentPage + 1].filter(
      (p) => p > 0 && p <= totalPages
    );

    firstPages.forEach((p) => {
      if (!pages.includes(p)) pages.push(p);
    });

    const gapAfterFirst = neighbors[0] > 2 + 1;
    if (gapAfterFirst) {
      pages.push('...');
      neighbors.forEach((p) => {
        if (!pages.includes(p)) pages.push(p);
      });
    } else {
      neighbors.forEach((p) => {
        if (!pages.includes(p)) pages.push(p);
      });
    }

    const gapBeforeLast = neighbors[neighbors.length - 1] < totalPages - 2;
    if (gapBeforeLast) {
      if (pages[pages.length - 1] !== '...') pages.push('...');
      lastPages.forEach((p) => {
        if (!pages.includes(p)) pages.push(p);
      });
    } else {
      lastPages.forEach((p) => {
        if (!pages.includes(p)) pages.push(p);
      });
    }

    return pages;
  }, [state.currentPage, state.cluster?.pagination.total_pages]);

  if (!isAuthenticated) {
    return <AppLoadingState />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 relative overflow-hidden">
      {/* Animated background blobs */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-0 -left-1/3 w-[600px] h-[600px] bg-blue-400/20 rounded-full mix-blend-multiply filter blur-3xl animate-blob"></div>
        <div className="absolute top-0 -right-1/4 w-[600px] h-[600px] bg-purple-400/20 rounded-full mix-blend-multiply filter blur-3xl animate-blob" style={{ animationDelay: '2s' }}></div>
        <div className="absolute -bottom-1/2 left-1/3 w-[600px] h-[600px] bg-cyan-400/20 rounded-full mix-blend-multiply filter blur-3xl animate-blob" style={{ animationDelay: '4s' }}></div>
      </div>

      {/* Main Content */}
      <div className="relative z-0 pt-20 md:pt-24">
        <div className="mx-auto max-w-7xl px-4 py-6 md:py-8">
          {/* Back Button */}
          <motion.button
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            onClick={() => router.back()}
            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium mb-6 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Topics
          </motion.button>

          {state.loading ? (
            <div className="space-y-6">
              <div className="h-12 bg-slate-200 rounded-lg animate-pulse"></div>
              <div className="h-6 bg-slate-200 rounded-lg animate-pulse w-2/3"></div>
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <ArticleCardSkeleton key={i} />
                ))}
              </div>
            </div>
          ) : state.error ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-12"
            >
              <div className="text-5xl mb-3">⚠️</div>
              <h3 className="text-xl font-semibold text-slate-900 mb-2">{state.error}</h3>
              <button
                onClick={() => router.push('/topics')}
                className="text-blue-600 hover:text-blue-700 font-medium transition-colors"
              >
                Return to Topics
              </button>
            </motion.div>
          ) : state.cluster ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6 }}
              className="space-y-8"
            >
              {/* Header Section */}
              <div className="space-y-4">
                <motion.h1
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-4xl md:text-5xl font-bold text-slate-900"
                >
                  {state.cluster.label}
                </motion.h1>

                <motion.p
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="text-lg text-slate-600 max-w-3xl"
                >
                  {state.cluster.description}
                </motion.p>

                {/* Metadata */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                  className="flex flex-wrap gap-4 items-center text-sm text-slate-600 pt-2"
                >
                  <span>📄 {state.cluster.article_count} articles</span>
                  <span>•</span>
                  <span>📊 Diversity: {(state.cluster.diversity_score * 100).toFixed(0)}%</span>
                  <span>•</span>
                  <span className="inline-flex items-center gap-1">
                    <span className="inline-block">●</span>
                    {state.cluster.size_category}
                  </span>
                </motion.div>
              </div>

              {/* Keywords/Tags */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="space-y-3"
              >
                <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
                  Keywords
                </h3>
                <div className="flex flex-wrap gap-2">
                  {state.cluster.keywords.map((keyword) => (
                    <span
                      key={keyword}
                      className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1.5 text-sm font-medium text-blue-700"
                    >
                      {keyword}
                    </span>
                  ))}
                </div>
              </motion.div>

              {/* Articles Section */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="space-y-6"
              >
                <div>
                  <h2 className="text-2xl font-bold text-slate-900 mb-1">Articles</h2>
                  <p className="text-sm text-slate-600">
                    {state.cluster.pagination.total_count} articles in this topic
                  </p>
                </div>

                {/* Articles List */}
                <div className="space-y-3">
                  {state.cluster.articles.map((article, idx) => (
                    <motion.button
                      key={article.id}
                      type="button"
                      onClick={() => router.push(`/articles/${article.id}`)}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      className="group w-full text-left p-4 rounded-xl bg-gradient-to-br from-white/60 to-white/40 border border-white/40 backdrop-blur-xl hover:from-white/80 hover:to-white/60 hover:border-white/60 transition-all shadow-lg"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0 space-y-2">
                          <h3 className="text-lg font-semibold text-slate-900 group-hover:text-blue-600 transition-colors line-clamp-2">
                            {article.title}
                          </h3>

                          {article.summary && (
                            <p className="text-sm text-slate-600 line-clamp-2">
                              {article.summary}
                            </p>
                          )}

                          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 pt-1">
                            <span className="font-medium text-slate-600">{article.source}</span>
                            <span>•</span>
                            <span>
                              {format(new Date(article.published_at * 1000), 'MMM d, yyyy')}
                            </span>
                            <span>•</span>
                            <span className="inline-flex items-center gap-1 font-medium text-slate-600">
                              <Zap className="w-3 h-3" />
                              {article.engagement_score.toFixed(1)} engagement
                            </span>
                          </div>
                        </div>

                        <div className="flex-shrink-0 flex flex-col items-end gap-2">
                          <svg className="w-5 h-5 text-slate-400 group-hover:text-blue-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>

                          <div className="text-right">
                            <div className="text-xs text-slate-500 font-medium">Confidence</div>
                            <div className="text-sm font-semibold text-slate-700 bg-white/60 rounded px-2 py-0.5">
                              {(article.confidence_score * 100).toFixed(0)}%
                            </div>
                          </div>
                        </div>
                      </div>
                    </motion.button>
                  ))}
                </div>

                {/* Pagination */}
                {state.cluster.pagination.total_pages > 1 && (
                  <div className="flex items-center justify-between sm:justify-center gap-2 flex-wrap pt-6 border-t border-white/20">
                    {/* Previous Button */}
                    <button
                      onClick={() => handlePageChange(Math.max(1, state.currentPage - 1))}
                      disabled={state.currentPage === 1}
                      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-br from-white/70 to-white/50 border border-white/40 text-slate-700 font-medium transition-all hover:from-white/80 hover:to-white/60 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
                    >
                      <ChevronLeft className="w-5 h-5" />
                      <span className="hidden sm:inline">Previous</span>
                    </button>

                    {/* Page Numbers */}
                    <div className="flex items-center gap-1 flex-wrap justify-center">
                      {getVisiblePages.map((page, idx) => (
                        page === '...' ? (
                          <span key={`dots-${idx}`} className="px-2 text-slate-600">
                            ...
                          </span>
                        ) : (
                          <button
                            key={page}
                            onClick={() => handlePageChange(page as number)}
                            className={`w-10 h-10 rounded-xl font-medium transition-all ${
                              state.currentPage === page
                                ? 'bg-blue-600 text-white shadow-xl'
                                : 'bg-gradient-to-br from-white/70 to-white/50 text-slate-700 hover:from-white/80 hover:to-white/60 border border-white/40 shadow-lg'
                            }`}
                          >
                            {page}
                          </button>
                        )
                      ))}
                    </div>

                    {/* Next Button */}
                    <button
                      onClick={() =>
                        handlePageChange(
                          Math.min(
                            state.cluster!.pagination.total_pages,
                            state.currentPage + 1
                          )
                        )
                      }
                      disabled={
                        state.currentPage === state.cluster.pagination.total_pages
                      }
                      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-br from-white/70 to-white/50 border border-white/40 text-slate-700 font-medium transition-all hover:from-white/80 hover:to-white/60 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
                    >
                      <span className="hidden sm:inline">Next</span>
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                )}

                {/* Page Info */}
                {state.cluster.pagination.total_pages > 1 && (
                  <div className="text-center text-sm text-slate-600">
                    Page <span className="font-semibold">{state.currentPage}</span> of{' '}
                    <span className="font-semibold">{state.cluster.pagination.total_pages}</span>
                  </div>
                )}
              </motion.div>
            </motion.div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
