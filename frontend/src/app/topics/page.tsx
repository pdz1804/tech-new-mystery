'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, Search, Filter, X, RefreshCw } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { apiClient } from '@/lib/api/client';
import { ClusterCard } from '@/components/article/ClusterCard';
import { ArticleCardSkeleton } from '@/components/ui/Skeleton';
import { AppLoadingState } from '@/components/ui/AppLoadingState';
import type { Cluster, ClusterListResponse, ClusterListParams } from '@/types/cluster';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

type SortOption = 'size' | 'recency' | 'diversity';

interface TopicsPageState {
  clusters: Cluster[];
  loading: boolean;
  error: string | null;
  currentPage: number;
  pageSize: number;
  totalPages: number;
  totalCount: number;
  sortBy: SortOption;
  searchQuery: string;
}

// ─── PCA-style cluster map (deterministic hash-based positions) ───────────────

const CLUSTER_COLORS = [
  '#3B82F6', '#8B5CF6', '#10B981', '#F59E0B',
  '#EF4444', '#06B6D4', '#84CC16', '#F97316',
];

function hashToPosition(str: string, seed: number): number {
  let h = seed;
  for (let i = 0; i < str.length; i++) {
    h = (h * 31 + str.charCodeAt(i)) & 0xffffffff;
  }
  return (Math.abs(h) % 80) + 10; // 10–90% of container
}

function ClusterMap({ clusters }: { clusters: Cluster[] }) {
  if (clusters.length === 0) return null;

  // SVG viewBox is 1000×260; positions are in those units
  const W = 1000;
  const H = 320;
  const displayedClusters = clusters.slice(0, 24);

  return (
    <div className="relative mb-8 w-full overflow-hidden rounded-2xl border border-slate-200/70 bg-white/85 shadow-[0_20px_45px_-28px_rgba(15,23,42,0.35)] backdrop-blur-xl">
      <div className="flex items-center justify-between border-b border-slate-200/70 px-5 py-4">
        <div>
          <p className="text-sm font-semibold text-slate-800">Article Topic Map</p>
          <p className="text-xs text-slate-500">Bubble size reflects cluster volume</p>
        </div>
        <p className="text-xs font-medium text-slate-500">{displayedClusters.length} visible</p>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-[320px] w-full"
        aria-label="Article topic map"
        role="img"
      >
        <defs>
          <pattern id="topic-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" strokeWidth="1" opacity="0.55" />
          </pattern>
        </defs>
        <rect width={W} height={H} fill="url(#topic-grid)" />
        {displayedClusters.map((cluster, i) => {
          const cx = (hashToPosition(cluster.id, 1) / 100) * W;
          const cy = (hashToPosition(cluster.id, 7) / 100) * H;
          const r = Math.max(22, Math.min(56, Math.sqrt(cluster.article_count) * 9 + 12));
          const color = CLUSTER_COLORS[i % CLUSTER_COLORS.length];
          const labelSize = Math.max(12, r * 0.42);
          return (
            <g key={cluster.id} className="cursor-pointer">
              <title>{`${cluster.label}: ${cluster.article_count} articles`}</title>
              <circle cx={cx} cy={cy} r={r + 8} fill={color} opacity={0.12} />
              <circle cx={cx} cy={cy} r={r} fill={color} opacity={0.86} />
              <text
                x={cx}
                y={cy}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={labelSize}
                fill="white"
                fontWeight="bold"
              >
                {cluster.article_count}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TopicsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);

  const [state, setState] = useState<TopicsPageState>({
    clusters: [],
    loading: true,
    error: null,
    currentPage: 1,
    pageSize: 12,
    totalPages: 1,
    totalCount: 0,
    sortBy: 'size',
    searchQuery: '',
  });

  const [showMobileFilters, setShowMobileFilters] = useState(false);
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [isTriggering, setIsTriggering] = useState(false);

  // Handle initial load and URL params
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    const pageParam = searchParams.get('page');
    const sortParam = searchParams.get('sort');
    const searchParam = searchParams.get('search');

    if (pageParam) setState((s) => ({ ...s, currentPage: parseInt(pageParam, 10) || 1 }));
    if (sortParam && ['size', 'recency', 'diversity'].includes(sortParam)) {
      setState((s) => ({ ...s, sortBy: sortParam as SortOption }));
    }
    if (searchParam) setState((s) => ({ ...s, searchQuery: searchParam }));
  }, [isAuthenticated, router, searchParams]);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(state.searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [state.searchQuery]);

  // Fetch clusters
  useEffect(() => {
    const fetchClusters = async () => {
      try {
        setState((s) => ({ ...s, loading: true, error: null }));

        const params: ClusterListParams = {
          page: state.currentPage,
          page_size: state.pageSize,
          sort_by: state.sortBy,
        };

        if (debouncedSearchQuery) {
          params.keyword = debouncedSearchQuery;
        }

        const response = await apiClient.get<ClusterListResponse>('/clusters', { params });
        const data = response.data;

        setState((s) => ({
          ...s,
          clusters: data.clusters || [],
          totalPages: data.pagination.total_pages,
          totalCount: data.pagination.total_count,
          currentPage: data.pagination.page,
          loading: false,
        }));

        // Update URL params
        const newParams = new URLSearchParams();
        newParams.set('page', state.currentPage.toString());
        newParams.set('sort', state.sortBy);
        if (debouncedSearchQuery) newParams.set('search', debouncedSearchQuery);
        router.push(`/topics?${newParams.toString()}`, { scroll: false });
      } catch (error) {
        console.error('Failed to fetch clusters:', error);
        setState((s) => ({
          ...s,
          error: 'Failed to load topics. Please try again.',
          loading: false,
        }));
      }
    };

    fetchClusters();
  }, [state.currentPage, state.sortBy, state.pageSize, debouncedSearchQuery, router]);

  const triggerClustering = async () => {
    setIsTriggering(true);
    try {
      const response = await apiClient.post('/admin/clustering/evaluations/trigger', {
        trigger_reason: 'Manual retrigger from admin panel',
      });

      const jobId = response.data?.job_id;
      alert('Clustering job queued! Page will auto-reload when done...');

      // Poll for completion every 3 seconds
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await apiClient.get(`/admin/clustering/evaluations/${jobId}`);
          if (statusResponse.data?.status === 'completed') {
            clearInterval(pollInterval);
            // Auto-reload page to show new clusters
            window.location.reload();
          }
        } catch {
          // Continue polling even if status check fails
        }
      }, 3000);

      // Stop polling after 10 minutes
      setTimeout(() => clearInterval(pollInterval), 600000);
    } catch {
      alert('Failed to trigger clustering.');
    } finally {
      setIsTriggering(false);
    }
  };

  const handleSearch = (query: string) => {
    setState((s) => ({ ...s, searchQuery: query, currentPage: 1 }));
  };

  const handleClearSearch = () => {
    setState((s) => ({ ...s, searchQuery: '', currentPage: 1 }));
  };

  const handleSortChange = (sort: SortOption) => {
    setState((s) => ({ ...s, sortBy: sort, currentPage: 1 }));
  };

  const handlePageChange = (page: number) => {
    setState((s) => ({ ...s, currentPage: page }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const getVisiblePages = useMemo(() => {
    const currentPage = state.currentPage;
    const totalPages = state.totalPages;

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
  }, [state.currentPage, state.totalPages]);

  if (!isAuthenticated) {
    return <AppLoadingState />;
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#f5f8fc]">
      {/* Main Content */}
      <div className="relative z-0 pt-44 md:pt-48">
        <div className="mx-auto max-w-7xl px-4 py-8 md:py-12">

          {/* ── Page header row ── */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
          >
            <div>
              <h1 className="mb-1 text-4xl font-bold text-slate-950 md:text-5xl">
                Topics
              </h1>
              <p className="text-base text-slate-500">
                Semantic clusters of recent tech news
              </p>
            </div>

            {/* Admin retrigger button */}
            {user?.is_admin && (
              <button
                type="button"
                onClick={triggerClustering}
                className="flex flex-shrink-0 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:border-blue-200 hover:text-blue-700 hover:shadow-md"
              >
                <RefreshCw size={16} className={isTriggering ? 'animate-spin' : ''} />
                {isTriggering ? 'Clustering...' : 'Retrigger Clustering'}
              </button>
            )}
          </motion.div>

          {/* ── Filters / Search bar ── */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="mb-8 space-y-4"
          >
            {/* Search + sort pill */}
            <div className="flex flex-col items-stretch gap-3 rounded-2xl border border-slate-200/80 bg-white/90 px-4 py-3 shadow-[0_18px_35px_-28px_rgba(15,23,42,0.45)] backdrop-blur-xl sm:flex-row sm:items-center">
              {/* Search input */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  placeholder="Search topics..."
                  value={state.searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="w-full rounded-xl bg-transparent py-2 pl-9 pr-4 text-sm text-slate-900 transition-all placeholder:text-slate-400 focus:outline-none"
                />
                {state.searchQuery && (
                  <button
                    type="button"
                    aria-label="Clear search"
                    onClick={handleClearSearch}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Divider */}
              <div className="hidden sm:block w-px h-6 bg-slate-200" />

              {/* Sort buttons — desktop */}
              <div className="hidden sm:flex items-center gap-1">
                <span className="text-xs text-slate-500 mr-1 font-medium">Sort:</span>
                {(['size', 'recency', 'diversity'] as const).map((sort) => (
                  <button
                    key={sort}
                    type="button"
                    onClick={() => handleSortChange(sort)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                      state.sortBy === sort
                        ? 'bg-blue-600 text-white shadow'
                        : 'border border-slate-200 bg-slate-50 text-slate-600 hover:bg-white'
                    }`}
                  >
                    {sort.charAt(0).toUpperCase() + sort.slice(1)}
                  </button>
                ))}
              </div>

              {/* Mobile filter toggle */}
              <button
                type="button"
                className="sm:hidden flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/80 border border-white/30 text-slate-600 text-xs font-medium"
                onClick={() => setShowMobileFilters(!showMobileFilters)}
              >
                <Filter className="w-3.5 h-3.5" />
                Filters
              </button>
            </div>

            {/* Mobile filters panel */}
            <AnimatePresence>
              {showMobileFilters && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="sm:hidden bg-gradient-to-br from-white/60 to-white/40 backdrop-blur-xl border border-white/30 rounded-2xl px-4 py-3 shadow-lg"
                >
                  <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Sort by</span>
                  <div className="grid grid-cols-3 gap-2 mt-2">
                    {(['size', 'recency', 'diversity'] as const).map((sort) => (
                      <button
                        key={sort}
                        type="button"
                        onClick={() => {
                          handleSortChange(sort);
                          setShowMobileFilters(false);
                        }}
                        className={`px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                          state.sortBy === sort
                            ? 'bg-blue-600 text-white'
                            : 'bg-white/80 border border-white/30 text-slate-600'
                        }`}
                      >
                        {sort.charAt(0).toUpperCase() + sort.slice(1)}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* ── PCA Topic Map ── */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15 }}
          >
            {!state.loading && <ClusterMap clusters={state.clusters} />}
          </motion.div>

          {/* ── Info text ── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mb-6 text-sm text-slate-500"
          >
            {state.loading ? (
              <span>Loading topics...</span>
            ) : (
              <span>
                Showing <span className="font-semibold text-slate-700">{state.clusters.length}</span> of{' '}
                <span className="font-semibold text-slate-700">{state.totalCount}</span> topics
              </span>
            )}
          </motion.div>

          {/* ── Error state ── */}
          {state.error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-6 p-4 rounded-2xl bg-red-50/80 border border-red-200/60 text-red-700 text-sm"
            >
              {state.error}
            </motion.div>
          )}

          {/* ── Cluster grid ── */}
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate={state.loading ? 'hidden' : 'visible'}
            className="mb-12"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {state.loading ? (
                Array.from({ length: state.pageSize }).map((_, i) => (
                  <ArticleCardSkeleton key={i} />
                ))
              ) : state.clusters.length > 0 ? (
                state.clusters.map((cluster) => (
                  <motion.div key={cluster.id} variants={itemVariants}>
                    <ClusterCard cluster={cluster} />
                  </motion.div>
                ))
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="col-span-full py-12 text-center"
                >
                  <div className="inline-flex flex-col items-center justify-center gap-3">
                    <div className="text-5xl">🔍</div>
                    <h3 className="text-xl font-semibold text-slate-900">
                      {state.searchQuery ? 'No topics found' : 'No topics available'}
                    </h3>
                    <p className="text-slate-500 text-sm max-w-sm">
                      {state.searchQuery
                        ? `Try adjusting your search for "${state.searchQuery}"`
                        : 'Topics will appear here once articles are clustered.'}
                    </p>
                    {state.searchQuery && (
                      <button
                        type="button"
                        onClick={handleClearSearch}
                        className="mt-2 px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
                      >
                        Clear search
                      </button>
                    )}
                  </div>
                </motion.div>
              )}
            </div>
          </motion.div>

          {/* ── Pagination ── */}
          {state.totalPages > 1 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="flex items-center justify-between sm:justify-center gap-2 flex-wrap"
            >
              <button
                type="button"
                onClick={() => handlePageChange(Math.max(1, state.currentPage - 1))}
                disabled={state.currentPage === 1}
                className="flex items-center gap-2 px-4 py-2 rounded-2xl bg-gradient-to-br from-white/70 to-white/50 backdrop-blur-xl border border-white/40 text-slate-700 font-medium transition-all hover:from-white/80 hover:to-white/60 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg"
              >
                <ChevronLeft className="w-5 h-5" />
                <span className="hidden sm:inline">Previous</span>
              </button>

              <div className="flex items-center gap-1 flex-wrap justify-center">
                {getVisiblePages.map((page, idx) =>
                  page === '...' ? (
                    <span key={`dots-${idx}`} className="px-2 text-slate-500">
                      ...
                    </span>
                  ) : (
                    <button
                      key={page}
                      type="button"
                      onClick={() => handlePageChange(page as number)}
                      className={`w-10 h-10 rounded-xl font-medium transition-all ${
                        state.currentPage === page
                          ? 'bg-blue-600 text-white shadow-xl'
                          : 'bg-gradient-to-br from-white/70 to-white/50 backdrop-blur-xl border border-white/40 text-slate-700 hover:from-white/80 hover:to-white/60 shadow-lg'
                      }`}
                    >
                      {page}
                    </button>
                  )
                )}
              </div>

              <button
                type="button"
                onClick={() => handlePageChange(Math.min(state.totalPages, state.currentPage + 1))}
                disabled={state.currentPage === state.totalPages}
                className="flex items-center gap-2 px-4 py-2 rounded-2xl bg-gradient-to-br from-white/70 to-white/50 backdrop-blur-xl border border-white/40 text-slate-700 font-medium transition-all hover:from-white/80 hover:to-white/60 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg"
              >
                <span className="hidden sm:inline">Next</span>
                <ChevronRight className="w-5 h-5" />
              </button>
            </motion.div>
          )}

          {/* Page info */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="mt-6 text-center text-sm text-slate-500"
          >
            Page <span className="font-semibold text-slate-700">{state.currentPage}</span> of{' '}
            <span className="font-semibold text-slate-700">{state.totalPages}</span>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
