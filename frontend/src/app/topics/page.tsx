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
import type {
  Cluster,
  ClusterListResponse,
  ClusterListParams,
  ClusterPCAMapResponse,
  PCAArticlePoint,
} from '@/types/cluster';

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
  pcaMap: ClusterPCAMapResponse | null;
}

// ─── PCA-style cluster map (deterministic hash-based positions) ───────────────

const CLUSTER_COLORS = [
  '#3B82F6', '#8B5CF6', '#10B981', '#F59E0B',
  '#EF4444', '#06B6D4', '#84CC16', '#F97316',
];

function truncateTitle(title: string, maxLength = 54) {
  return title.length > maxLength ? `${title.slice(0, maxLength - 1)}...` : title;
}

function ClusterMap({ data }: { data: ClusterPCAMapResponse | null }) {
  const W = 1000;
  const H = 420;
  const padding = 56;
  const [selectedPoint, setSelectedPoint] = useState<PCAArticlePoint | null>(null);
  const [draggedPointId, setDraggedPointId] = useState<string | null>(null);
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>({});
  const clusterById = new Map((data?.clusters ?? []).map((cluster) => [cluster.cluster_id, cluster]));
  const xFor = (point: PCAArticlePoint) => nodePositions[point.article_id]?.x ?? padding + ((point.x + 1) / 2) * (W - padding * 2);
  const yFor = (point: PCAArticlePoint) => nodePositions[point.article_id]?.y ?? padding + ((1 - (point.y + 1) / 2)) * (H - padding * 2);

  const updateDraggedNode = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!draggedPointId) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - bounds.left) / bounds.width) * W;
    const y = ((event.clientY - bounds.top) / bounds.height) * H;
    setNodePositions((positions) => ({
      ...positions,
      [draggedPointId]: {
        x: Math.max(padding / 2, Math.min(W - padding / 2, x)),
        y: Math.max(padding / 2, Math.min(H - padding / 2, y)),
      },
    }));
  };

  const isPreparing = data?.status === 'queued' || !data;

  return (
    <div className="relative mb-8 w-full overflow-hidden rounded-[28px] border border-white/55 border-t-white/90 bg-white/52 shadow-[0_26px_70px_-42px_rgba(15,23,42,0.55),inset_0_1px_0_rgba(255,255,255,0.9)] backdrop-blur-3xl">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_8%,rgba(255,255,255,0.92),transparent_34%),radial-gradient(circle_at_86%_18%,rgba(59,130,246,0.12),transparent_30%)]" />
      <div className="relative flex items-center justify-between border-b border-white/55 px-5 py-4">
        <div>
          <p className="text-sm font-bold text-slate-900">Article Embedding Map</p>
          <p className="text-xs font-medium text-slate-500">PCA projection of article embeddings, colored by cluster</p>
        </div>
        <p className="rounded-full border border-white/60 bg-white/55 px-3 py-1 text-xs font-semibold text-slate-600 backdrop-blur-xl">
          {isPreparing ? 'Preparing...' : `${data.total_articles} articles`}
        </p>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-[420px] w-full"
        aria-label="Article embedding PCA map"
        role="img"
        onPointerMove={updateDraggedNode}
        onPointerUp={() => setDraggedPointId(null)}
        onPointerLeave={() => setDraggedPointId(null)}
      >
        <defs>
          <radialGradient id="topic-map-wash" cx="50%" cy="42%" r="72%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.88" />
            <stop offset="68%" stopColor="#eff7ff" stopOpacity="0.62" />
            <stop offset="100%" stopColor="#dbeafe" stopOpacity="0.28" />
          </radialGradient>
          <filter id="topic-blur" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="8" />
          </filter>
        </defs>
        <rect width={W} height={H} fill="url(#topic-map-wash)" />

        {isPreparing && (
          <g>
            <circle cx={W / 2} cy={H / 2} r="44" fill="#3B82F6" opacity="0.12" />
            <circle cx={W / 2} cy={H / 2} r="18" fill="#3B82F6" opacity="0.62" />
            <text x={W / 2} y={H / 2 + 54} textAnchor="middle" fontSize="13" fill="#475569" fontWeight="700">
              Worker is preparing PCA map
            </text>
          </g>
        )}

        {(data?.points ?? []).map((point) => {
          const cluster = clusterById.get(point.cluster_id);
          const color = cluster?.color ?? '#64748B';
          const cx = xFor(point);
          const cy = yFor(point);
          const isSelected = selectedPoint?.article_id === point.article_id;

          return (
            <g
              key={point.article_id}
              className="group cursor-grab active:cursor-grabbing"
              onPointerDown={(event) => {
                event.preventDefault();
                setDraggedPointId(point.article_id);
                setSelectedPoint(point);
              }}
              onClick={() => setSelectedPoint(point)}
            >
              <title>{`${point.title} - ${point.cluster_label}`}</title>
              <circle cx={cx} cy={cy} r={isSelected ? 19 : 13} fill={color} opacity="0.16" filter="url(#topic-blur)" />
              <circle
                cx={cx}
                cy={cy}
                r={isSelected ? 10 : 6 + point.confidence_score * 2.5}
                fill={color}
                opacity="0.9"
                stroke="rgba(255,255,255,0.9)"
                strokeWidth="1.5"
              />
              <circle cx={cx - 2} cy={cy - 2} r="2" fill="white" opacity="0.45" />
              <g className="opacity-0 transition-opacity duration-150 group-hover:opacity-100">
                <rect
                  x={Math.min(cx + 12, W - 250)}
                  y={Math.max(cy - 28, 10)}
                  width="238"
                  height="42"
                  rx="14"
                  fill="rgba(255,255,255,0.9)"
                  stroke="rgba(255,255,255,0.95)"
                />
                <text
                  x={Math.min(cx + 24, W - 238)}
                  y={Math.max(cy - 3, 35)}
                  fontSize="12"
                  fill="#0f172a"
                  fontWeight="700"
                >
                  {truncateTitle(point.title)}
                </text>
                <text
                  x={Math.min(cx + 24, W - 238)}
                  y={Math.max(cy + 13, 51)}
                  fontSize="10"
                  fill="#64748b"
                  fontWeight="600"
                >
                  {truncateTitle(point.cluster_label, 34)}
                </text>
              </g>
            </g>
          );
        })}
      </svg>

      <div className="relative grid gap-3 border-t border-white/55 px-5 py-3 lg:grid-cols-[1fr_320px]">
        <div className="flex flex-wrap gap-2">
          {(data?.clusters ?? []).slice(0, 8).map((cluster) => (
            <span
              key={cluster.cluster_id}
              className="inline-flex items-center gap-2 rounded-full border border-white/60 bg-white/52 px-3 py-1 text-xs font-semibold text-slate-600 backdrop-blur-xl"
            >
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: cluster.color }} />
              {truncateTitle(cluster.label, 22)}
            </span>
          ))}
          {(data?.clusters.length ?? 0) > 8 && (
            <span className="inline-flex items-center rounded-full border border-white/60 bg-white/52 px-3 py-1 text-xs font-semibold text-slate-500 backdrop-blur-xl">
              +{(data?.clusters.length ?? 0) - 8} clusters
            </span>
          )}
        </div>

        <div className="rounded-2xl border border-white/60 bg-white/52 p-3 text-sm shadow-sm backdrop-blur-2xl">
          {selectedPoint ? (
            <>
              <p className="font-bold leading-5 text-slate-950">{selectedPoint.title}</p>
              <p className="mt-2 text-xs font-semibold text-slate-500">{selectedPoint.cluster_label}</p>
              <p className="mt-2 text-xs text-slate-500">
                Confidence {(selectedPoint.confidence_score * 100).toFixed(0)}%
              </p>
            </>
          ) : (
            <p className="text-xs font-medium leading-5 text-slate-500">
              Drag article nodes around. Hover for title, click a node to inspect details.
            </p>
          )}
        </div>
      </div>
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
    pcaMap: null,
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

        const clustersResponse = await apiClient.get<ClusterListResponse>('/clusters', { params });
        const data = clustersResponse.data;
        const clusterIds = (data.clusters || []).map((cluster) => cluster.id);
        const pcaParams = new URLSearchParams();
        pcaParams.set('limit', '250');
        clusterIds.forEach((clusterId) => pcaParams.append('cluster_ids', clusterId));
        const pcaResponse = await apiClient.get<ClusterPCAMapResponse>(
          `/clusters/pca-map?${pcaParams.toString()}`
        );

        setState((s) => ({
          ...s,
          clusters: data.clusters || [],
          pcaMap: pcaResponse.data,
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

  useEffect(() => {
    if (state.pcaMap?.status !== 'queued' || state.clusters.length === 0) return;

    const timer = window.setTimeout(async () => {
      try {
        const pcaParams = new URLSearchParams();
        pcaParams.set('limit', '250');
        state.clusters.forEach((cluster) => pcaParams.append('cluster_ids', cluster.id));
        const response = await apiClient.get<ClusterPCAMapResponse>(
          `/clusters/pca-map?${pcaParams.toString()}`
        );
        setState((s) => ({ ...s, pcaMap: response.data }));
      } catch {
        // Leave the queued state visible; the next page interaction will retry.
      }
    }, 2500);

    return () => window.clearTimeout(timer);
  }, [state.pcaMap?.status, state.clusters]);

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
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_16%_12%,rgba(37,99,235,0.10),transparent_30%),radial-gradient(circle_at_88%_8%,rgba(20,184,166,0.10),transparent_28%),linear-gradient(180deg,#f8fbff_0%,#eef5f8_100%)]">
      {/* Main Content */}
      <div className="relative z-0 pt-44 md:pt-48">
        <div className="mx-auto max-w-[1440px] px-4 py-6 md:px-8 md:py-10">
          {/* ── Filters / Search bar ── */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="mb-7 space-y-4"
          >
            {/* Search + sort pill */}
            <div className="flex flex-col items-stretch gap-3 rounded-[24px] border border-white/55 border-t-white/90 bg-white/62 px-4 py-3 shadow-[0_18px_45px_-32px_rgba(15,23,42,0.5),inset_0_1px_0_rgba(255,255,255,0.88)] backdrop-blur-3xl sm:flex-row sm:items-center">
              {/* Search input */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  placeholder="Search topics..."
                  value={state.searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="w-full rounded-2xl bg-white/30 py-2.5 pl-9 pr-4 text-sm font-medium text-slate-900 transition-all placeholder:text-slate-400 focus:bg-white/55 focus:outline-none"
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
              <div className="hidden h-6 w-px bg-white/70 sm:block" />

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
                        ? 'bg-blue-600 text-white shadow-[0_10px_22px_rgba(37,99,235,0.24)]'
                        : 'border border-white/55 bg-white/45 text-slate-600 hover:bg-white/75'
                    }`}
                  >
                    {sort.charAt(0).toUpperCase() + sort.slice(1)}
                  </button>
                ))}
              </div>

              {user?.is_admin && (
                <>
                  <div className="hidden h-6 w-px bg-white/70 sm:block" />
                  <button
                    type="button"
                    onClick={triggerClustering}
                    className="hidden flex-shrink-0 items-center justify-center gap-2 rounded-2xl border border-white/60 bg-white/58 px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm backdrop-blur-2xl transition-all hover:bg-white/82 hover:text-blue-700 sm:flex"
                  >
                    <RefreshCw size={15} className={isTriggering ? 'animate-spin' : ''} />
                    {isTriggering ? 'Clustering...' : 'Retrigger'}
                  </button>
                </>
              )}

              {/* Mobile filter toggle */}
              <div className="flex gap-2 sm:hidden">
                {user?.is_admin && (
                  <button
                    type="button"
                    onClick={triggerClustering}
                    className="flex items-center gap-2 rounded-xl border border-white/50 bg-white/70 px-3 py-1.5 text-xs font-semibold text-slate-700"
                  >
                    <RefreshCw size={14} className={isTriggering ? 'animate-spin' : ''} />
                    Run
                  </button>
                )}
                <button
                  type="button"
                  className="flex items-center gap-2 rounded-xl border border-white/50 bg-white/70 px-3 py-1.5 text-xs font-medium text-slate-600"
                  onClick={() => setShowMobileFilters(!showMobileFilters)}
                >
                  <Filter className="w-3.5 h-3.5" />
                  Filters
                </button>
              </div>
            </div>

            {/* Mobile filters panel */}
            <AnimatePresence>
              {showMobileFilters && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="sm:hidden rounded-2xl border border-white/55 bg-white/62 px-4 py-3 shadow-lg backdrop-blur-3xl"
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
                            : 'bg-white/65 border border-white/50 text-slate-600'
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
            {!state.loading && <ClusterMap data={state.pcaMap} />}
          </motion.div>

          {/* ── Info text ── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mb-6 flex flex-wrap items-center gap-2 text-sm text-slate-500"
          >
            {state.loading ? (
              <span>Loading topics...</span>
            ) : (
              <>
                <span className="rounded-full border border-white/60 bg-white/55 px-3 py-1.5 font-medium shadow-sm backdrop-blur-xl">
                  <span className="font-bold text-slate-800">{state.clusters.length}</span> visible
                </span>
                <span className="rounded-full border border-white/60 bg-white/55 px-3 py-1.5 font-medium shadow-sm backdrop-blur-xl">
                  <span className="font-bold text-slate-800">{state.totalCount}</span> topics in latest clustering set
                </span>
              </>
            )}
          </motion.div>

          {/* ── Error state ── */}
          {state.error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-6 rounded-2xl border border-red-200/60 bg-red-50/80 p-4 text-sm text-red-700"
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
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
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
                    <div className="flex h-14 w-14 items-center justify-center rounded-[22px] border border-white/60 bg-white/62 text-blue-600 shadow-lg backdrop-blur-2xl">
                      <Search size={24} aria-hidden="true" />
                    </div>
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
              className="flex flex-wrap items-center justify-between gap-2 sm:justify-center"
            >
              <button
                type="button"
                onClick={() => handlePageChange(Math.max(1, state.currentPage - 1))}
                disabled={state.currentPage === 1}
                className="flex items-center gap-2 rounded-2xl border border-white/55 bg-white/62 px-4 py-2 font-medium text-slate-700 shadow-lg backdrop-blur-3xl transition-all hover:bg-white/78 disabled:cursor-not-allowed disabled:opacity-40"
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
                          : 'border border-white/55 bg-white/62 text-slate-700 shadow-lg backdrop-blur-3xl hover:bg-white/78'
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
                className="flex items-center gap-2 rounded-2xl border border-white/55 bg-white/62 px-4 py-2 font-medium text-slate-700 shadow-lg backdrop-blur-3xl transition-all hover:bg-white/78 disabled:cursor-not-allowed disabled:opacity-40"
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
