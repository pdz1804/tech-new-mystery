'use client';

import { useState, useEffect } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { apiClient } from '@/lib/api/client';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { AppLoadingState } from '@/components/ui/AppLoadingState';
import { SearchQueryModal } from '@/components/admin/SearchQueryModal';
import { NewsAPIModal } from '@/components/admin/NewsAPIModal';
import { Check, X, ExternalLink, Loader2, Zap, Eye, Clock } from 'lucide-react';

interface PendingSearch {
  search_id: string;
  query: string;
  title: string;
  url: string;
  snippet: string | null;
  source: string | null;
  created_at: string;
  status: string;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

const DEFAULT_TAVILY_QUERIES = [
  'artificial intelligence breakthroughs',
  'AI agents autonomous systems',
  'machine learning innovation',
  'AWS cloud technology',
  'Google Cloud Platform GCP',
];

const DEFAULT_NEWSAPI_QUERIES = [
  'artificial intelligence breakthroughs',
  'AI agents autonomous systems',
  'machine learning innovation',
  'AWS cloud technology',
  'Microsoft Azure cloud',
  'LLM language model news',
];

export default function AdminQueuePage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const isHydrated = useAuthStore((s) => s.isHydrated);

  const [searches, setSearches] = useState<PendingSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [triggeringScheduler, setTriggeringScheduler] = useState<string | null>(null);
  const [autoReviewLoading, setAutoReviewLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [selectedSearch, setSelectedSearch] = useState<PendingSearch | null>(null);
  const [queryModalOpen, setQueryModalOpen] = useState(false);
  const [queryModalSource, setQueryModalSource] = useState<'tavily' | 'newsapi'>('tavily');
  const [newsAPIModalOpen, setNewsAPIModalOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalSearches, setTotalSearches] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const LIMIT = 20;

  // Queue monitoring
  const [queueStats, setQueueStats] = useState<any>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  useEffect(() => {
    if (isHydrated && !user?.is_admin) {
      router.push('/');
      return;
    }
  }, [isHydrated, user?.is_admin, router]);

  useEffect(() => {
    const fetchQueue = async () => {
      try {
        setLoading(true);
        setError(null);

        const { data: response } = await apiClient.get(`/admin/searches?page=${currentPage}&limit=${LIMIT}`);

        if (response.success) {
          setSearches(response.data);
          setTotalSearches(response.total || 0);
          setTotalPages(response.total_pages || 0);
        } else {
          setError('Failed to load pending searches');
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        console.error('Error fetching queue:', err);
      } finally {
        setLoading(false);
      }
    };

    if (isHydrated) {
      fetchQueue();
    }
  }, [isHydrated, currentPage]);

  useEffect(() => {
    const fetchQueueStats = async () => {
      try {
        setStatsLoading(true);
        const { data: response } = await apiClient.get('/admin/queue/stats');
        if (response.success) {
          setQueueStats(response);
        }
      } catch (err) {
        console.error('Error fetching queue stats:', err);
      } finally {
        setStatsLoading(false);
      }
    };

    if (isHydrated && user?.is_admin) {
      fetchQueueStats();
      const interval = setInterval(fetchQueueStats, 3000);
      return () => clearInterval(interval);
    }
  }, [isHydrated, user?.is_admin]);

  const handleApprove = async (searchId: string) => {
    try {
      setActionLoading(searchId);
      const { data } = await apiClient.post(`/admin/searches/${searchId}/approve`);

      if (data.success) {
        setSearches(searches.filter((s) => s.search_id !== searchId));
        setSelectedSearch(null);
        setSuccessMessage('Search approved and article created');
        setTimeout(() => setSuccessMessage(null), 5000);
      } else {
        setError('Failed to approve search');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      if (message.includes('409') || message.includes('already exists')) {
        setError('This article already exists. Click Delete to remove this search result.');
      } else {
        setError(message);
      }
      console.error('Error approving search:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (searchId: string) => {
    try {
      setActionLoading(searchId);
      const { data } = await apiClient.delete(`/admin/searches/${searchId}/reject`);

      if (data.success) {
        setSearches(searches.filter((s) => s.search_id !== searchId));
        setSelectedSearch(null);
        setSuccessMessage('Search rejected successfully');
        setTimeout(() => setSuccessMessage(null), 5000);
      } else {
        setError('Failed to reject search');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      console.error('Error rejecting search:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleOpenQueryModal = (source: 'tavily' | 'newsapi') => {
    if (source === 'newsapi') {
      setNewsAPIModalOpen(true);
    } else {
      setQueryModalSource(source);
      setQueryModalOpen(true);
    }
  };

  const handleConfirmSearch = async (queries: string[]) => {
    try {
      setTriggeringScheduler(queryModalSource);
      setError(null);
      setSuccessMessage(null);
      setQueryModalOpen(false);

      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const dateParam = yesterday.toISOString().split('T')[0];

      const endpoint = queryModalSource === 'tavily' ? '/admin/tavily/trigger' : '/admin/newsapi/trigger';
      const params = new URLSearchParams();
      params.append(queryModalSource === 'tavily' ? 'start_date' : 'from_date', dateParam);

      // Add queries as comma-separated if newsapi supports it
      if (queryModalSource === 'newsapi') {
        params.append('queries', queries.join(','));
      }

      const { data } = await apiClient.post(`${endpoint}?${params.toString()}`);

      if (data.success) {
        setSuccessMessage(data.message);
        setTimeout(() => setSuccessMessage(null), 5000);

        // Single refresh after 3 seconds to check for results
        setTimeout(async () => {
          try {
            const { data: response } = await apiClient.get('/admin/searches');
            if (response.success) {
              setSearches(response.data);
            }
          } catch (err) {
            console.error('Error refreshing queue:', err);
          }
        }, 3000);
      } else {
        setError('Failed to trigger scheduler');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      console.error('Error triggering scheduler:', err);
    } finally {
      setTriggeringScheduler(null);
    }
  };

  const handleCleanQueue = async () => {
    if (!window.confirm('⚠️ Are you sure you want to delete ALL pending searches? This cannot be undone.')) {
      return;
    }

    try {
      setTriggeringScheduler('clean');
      setError(null);

      const { data } = await apiClient.delete('/admin/searches/clean');

      if (data.success) {
        setSuccessMessage(data.message || 'Queue cleaned successfully!');
        setSearches([]);
        setCurrentPage(1);
        setTotalSearches(0);
        setTotalPages(0);
        setTimeout(() => setSuccessMessage(null), 5000);
      } else {
        setError(data.message || 'Failed to clean queue');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      console.error('Error cleaning queue:', err);
    } finally {
      setTriggeringScheduler(null);
    }
  };

  const handleAutoReview = async () => {
    try {
      setAutoReviewLoading(true);
      setError(null);

      const { data } = await apiClient.post('/admin/searches/auto-review');

      if (data.success) {
        setSuccessMessage(`Auto-review task queued (ID: ${data.task_id}). This may take a few minutes...`);
        setTimeout(() => setSuccessMessage(null), 8000);

        // Refresh queue after a delay
        setTimeout(async () => {
          try {
            const { data: response } = await apiClient.get(`/admin/searches?page=${currentPage}&limit=${LIMIT}`);
            if (response.success) {
              setSearches(response.data);
              setTotalSearches(response.total || 0);
              setTotalPages(response.total_pages || 0);
            }
          } catch (err) {
            console.error('Error refreshing queue:', err);
          }
        }, 3000);
      } else {
        setError('Failed to trigger auto-review');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      console.error('Error triggering auto-review:', err);
    } finally {
      setAutoReviewLoading(false);
    }
  };

  const cleanSnippet = (text: string | null, limit: number = 150) => {
    if (!text) return '';
    const cleaned = text
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1')
      .replace(/<[^>]+>/g, '')
      .replace(/\n+/g, ' ')
      .trim();
    if (limit && cleaned.length > limit) {
      return cleaned.substring(0, limit);
    }
    return cleaned;
  };

  if (!isHydrated) {
    return <AppLoadingState variant="queue" />;
  }

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="queue-stage app-page-shell"
    >
      {/* Hero Section */}
      <section className="pb-8">
        <motion.div
          variants={itemVariants}
          className="app-page-container"
        >
          <div className="app-hero-panel p-4 sm:p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="text-left">
                <h1 className="mb-1 font-sans text-3xl font-bold text-black sm:text-4xl">Search Queue</h1>
                <p className="max-w-2xl text-sm text-black/60 sm:text-base">
                  Review and approve search results ({totalSearches} pending)
                </p>
              </div>

              {/* Trigger Buttons */}
              <motion.div
                variants={itemVariants}
                className="flex flex-wrap gap-3 lg:justify-end"
              >
                <button
                  type="button"
                  onClick={() => handleOpenQueryModal('tavily')}
                  disabled={triggeringScheduler !== null || loading}
                  className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-semibold
                    px-6 py-3 rounded-xl flex items-center gap-2 shadow-lg shadow-blue-500/20
                    hover:shadow-lg hover:shadow-blue-500/40 hover:-translate-y-1 transition-all
                    disabled:opacity-50 disabled:hover:translate-y-0"
                  title="Review and search Tavily"
                >
                  <Zap size={20} />
                  {triggeringScheduler === 'tavily' ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      <span>Searching...</span>
                    </>
                  ) : (
                    <span>Tavily Search</span>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => handleOpenQueryModal('newsapi')}
                  disabled={triggeringScheduler !== null || loading}
                  className="bg-white/80 backdrop-blur-md border border-black/10 text-black font-semibold
                    px-6 py-3 rounded-xl flex items-center gap-2 hover:bg-white/90 hover:border-black/20
                    transition-all disabled:opacity-50"
                  title="Review and search NewsAPI"
                >
                  <Zap size={20} />
                  {triggeringScheduler === 'newsapi' ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      <span>Searching...</span>
                    </>
                  ) : (
                    <span>NewsAPI Search</span>
                  )}
                </button>
                <button
                  type="button"
                  onClick={handleAutoReview}
                  disabled={triggeringScheduler !== null || autoReviewLoading || loading || searches.length === 0}
                  className="bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold
                    px-6 py-3 rounded-xl flex items-center gap-2 shadow-lg shadow-green-500/20
                    hover:shadow-lg hover:shadow-green-500/40 hover:-translate-y-1 transition-all
                    disabled:opacity-50 disabled:hover:translate-y-0"
                  title="Automatically review, evaluate, and publish/reject all pending searches"
                >
                  {autoReviewLoading ? (
                    <>
                      <Loader2 size={20} className="animate-spin" />
                      <span>Reviewing...</span>
                    </>
                  ) : (
                    <>
                      <Zap size={20} />
                      <span>Auto-Review All</span>
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={handleCleanQueue}
                  disabled={triggeringScheduler !== null || loading || searches.length === 0}
                  className="bg-red-50 border border-red-200 text-red-700 font-semibold
                    px-6 py-3 rounded-xl flex items-center gap-2 hover:bg-red-100 hover:border-red-300
                    transition-all disabled:opacity-50"
                  title="Clear all pending searches from queue"
                >
                  <X size={20} />
                  <span>Clean Queue</span>
                </button>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Queue Stats Section */}
      {queueStats && (
        <section className="pb-8">
          <motion.div
            variants={itemVariants}
            className="app-page-container"
          >
            <div className="glass-panel p-4 sm:p-6 rounded-2xl">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-semibold text-black/80 flex items-center gap-2">
                  <Eye size={18} />
                  Real-Time Queue Status
                </h2>
                <div className="text-xs text-black/50">
                  Updated: {new Date(queueStats.timestamp).toLocaleTimeString()}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {/* Pending */}
                <div className="rounded-lg bg-blue-50/50 border border-blue-200/50 p-3">
                  <div className="text-xs text-blue-600/70 font-medium mb-1">Pending</div>
                  <div className="text-2xl font-bold text-blue-700">{queueStats.total_pending}</div>
                </div>

                {/* Being Processed */}
                <div className="rounded-lg bg-green-50/50 border border-green-200/50 p-3">
                  <div className="text-xs text-green-600/70 font-medium mb-1">Processing</div>
                  <div className="text-2xl font-bold text-green-700">{queueStats.being_processed}</div>
                </div>

                {/* Queued in Redis */}
                <div className="rounded-lg bg-amber-50/50 border border-amber-200/50 p-3">
                  <div className="text-xs text-amber-600/70 font-medium mb-1">Queued</div>
                  <div className="text-2xl font-bold text-amber-700">{queueStats.queued_in_redis}</div>
                </div>

                {/* Capacity */}
                <div className={`rounded-lg ${queueStats.capacity_available ? 'bg-emerald-50/50 border border-emerald-200/50' : 'bg-red-50/50 border border-red-200/50'} p-3`}>
                  <div className={`text-xs ${queueStats.capacity_available ? 'text-emerald-600/70' : 'text-red-600/70'} font-medium mb-1`}>
                    {queueStats.capacity_available ? '✓ Capacity' : '⚠ Capacity'}
                  </div>
                  <div className={`text-2xl font-bold ${queueStats.capacity_available ? 'text-emerald-700' : 'text-red-700'}`}>
                    {Math.round(queueStats.queue_depth_percent)}%
                  </div>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mt-4 pt-4 border-t border-black/10">
                <div className="mb-2 flex items-center justify-between text-xs">
                  <span className="text-black/60 font-medium">Queue Depth</span>
                  <span className="text-black/50">
                    {queueStats.total_pending + queueStats.being_processed + queueStats.queued_in_redis} / 1000
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-black/10 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      queueStats.queue_depth_percent > 80
                        ? 'bg-red-500'
                        : queueStats.queue_depth_percent > 50
                        ? 'bg-amber-500'
                        : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(queueStats.queue_depth_percent, 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </motion.div>
        </section>
      )}

      {/* Content Section */}
      <section className="pb-20">
        <div className="app-page-container">
          {/* Messages */}
          <AnimatePresence>
            {successMessage && (
              <motion.div
                variants={itemVariants}
                initial="hidden"
                animate="visible"
                exit={{ opacity: 0, y: -20 }}
                className="glass-panel mb-6 border-green-500/30 p-4"
              >
                <p className="text-green-700 font-semibold">{successMessage}</p>
              </motion.div>
            )}
            {error && (
              <motion.div
                variants={itemVariants}
                initial="hidden"
                animate="visible"
                exit={{ opacity: 0, y: -20 }}
                className="glass-panel mb-6 border-red-500/30 p-4"
              >
                <p className="text-red-700 font-semibold">{error}</p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Queue List */}
          {loading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="queue-card p-6">
                  <Skeleton className="mb-3 h-6 w-1/2" />
                  <Skeleton className="mb-2 h-4 w-full" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              ))}
            </div>
          ) : searches.length === 0 ? (
            <motion.div
              variants={itemVariants}
              className="queue-card p-12 text-center"
            >
              <Eye size={48} className="mx-auto mb-4 text-black/30 opacity-50" />
              <p className="text-h3 mb-2 text-black">No Pending Searches</p>
              <p className="text-body text-black/60">
                Trigger Tavily or NewsAPI to fetch search results
              </p>
            </motion.div>
          ) : (
            <>
              <motion.div
                variants={containerVariants}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                className="queue-review-list"
              >
                {searches.map((search) => (
                  <motion.div
                    key={search.search_id}
                    variants={itemVariants}
                    className="queue-review-row cursor-pointer"
                    onClick={() => setSelectedSearch(search)}
                  >
                      <div className="min-w-0">
                        <h3 className="queue-review-title line-clamp-2 transition-colors hover:text-blue-600">
                          {search.title}
                        </h3>
                        <p className="queue-review-preview line-clamp-2">
                          {cleanSnippet(search.snippet, 180)}
                        </p>
                      </div>

                      <div className="queue-review-meta">
                          {search.source && (
                            <Badge variant="info" size="sm">
                              {search.source}
                            </Badge>
                          )}
                          <Badge variant="info" size="sm">
                            <Clock size={12} className="inline mr-1" />
                            {new Date(search.created_at).toLocaleDateString()}
                          </Badge>
                      </div>

                    {/* Action Buttons */}
                    <div className="flex shrink-0 justify-start gap-2 lg:justify-end">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleApprove(search.search_id);
                        }}
                        disabled={actionLoading === search.search_id}
                        className="btn-liquid primary sm text-sm"
                      >
                        {actionLoading === search.search_id ? (
                          <>
                            <Loader2 size={16} className="animate-spin inline mr-1" />
                            Approving...
                          </>
                        ) : (
                          <>
                            <Check size={16} className="inline mr-1" />
                            Approve
                          </>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleReject(search.search_id);
                        }}
                        disabled={actionLoading === search.search_id}
                        className="btn-liquid secondary sm text-sm"
                      >
                        {actionLoading === search.search_id ? (
                          <>
                            <Loader2 size={16} className="animate-spin inline mr-1" />
                            Rejecting...
                          </>
                        ) : (
                          <>
                            <X size={16} className="inline mr-1" />
                            Reject
                          </>
                        )}
                      </button>
                      <a
                        href={search.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-liquid tertiary sm text-sm"
                        title="Open article in new tab"
                      >
                        <ExternalLink size={16} className="inline" />
                      </a>
                    </div>
                  </motion.div>
                ))}
              </motion.div>

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <motion.div
                  variants={itemVariants}
                  className="mt-8 flex items-center justify-center gap-3"
                >
                  <button
                    type="button"
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1 || loading}
                    className="btn-liquid secondary sm"
                  >
                    ← Prev
                  </button>
                  <span className="text-sm font-semibold text-black/60">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    type="button"
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages || loading}
                    className="btn-liquid secondary sm"
                  >
                    Next →
                  </button>
                </motion.div>
              )}
            </>
          )}
        </div>
      </section>

      {/* Search Query Modal (Tavily only) */}
      <SearchQueryModal
        isOpen={queryModalOpen}
        source={queryModalSource}
        defaultQueries={queryModalSource === 'tavily' ? DEFAULT_TAVILY_QUERIES : DEFAULT_NEWSAPI_QUERIES}
        onConfirm={handleConfirmSearch}
        onCancel={() => setQueryModalOpen(false)}
        isLoading={triggeringScheduler !== null}
      />

      {/* NewsAPI Modal */}
      <NewsAPIModal
        isOpen={newsAPIModalOpen}
        onClose={() => setNewsAPIModalOpen(false)}
      />

      {/* Detail Modal */}
      <AnimatePresence>
        {selectedSearch && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-[32px] z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedSearch(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="glass-modal queue-preview-modal p-6 sm:p-7"
            >
              <div className="mb-6 border-b border-black/10 pb-5">
                <span className="text-label mb-3 block text-blue-600">Queue Preview</span>
                <h2 className="mb-3 font-sans text-2xl font-bold leading-tight text-black sm:text-3xl">
                  {selectedSearch.title}
                </h2>
                <p className="text-base leading-relaxed text-black/62">
                  {cleanSnippet(selectedSearch.snippet, 520)}
                </p>
              </div>

              <div className="mb-7 grid gap-4 sm:grid-cols-2">
                <div className="glass-panel p-4">
                  <p className="text-label text-black/60 mb-2">Source</p>
                  <p className="text-body font-semibold text-black">{selectedSearch.source || 'Unknown'}</p>
                </div>
                <div className="glass-panel p-4">
                  <p className="text-label text-black/60 mb-2">Date</p>
                  <p className="text-body font-semibold text-black">
                    {new Date(selectedSearch.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={() => handleApprove(selectedSearch.search_id)}
                  disabled={actionLoading === selectedSearch.search_id}
                  className="btn-liquid primary flex-1"
                >
                  {actionLoading === selectedSearch.search_id ? (
                    <>
                      <Loader2 size={18} className="animate-spin inline mr-2" />
                      Approving...
                    </>
                  ) : (
                    <>
                      <Check size={18} className="inline mr-2" />
                      Approve & Create
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => handleReject(selectedSearch.search_id)}
                  disabled={actionLoading === selectedSearch.search_id}
                  className="btn-liquid secondary flex-1"
                >
                  {actionLoading === selectedSearch.search_id ? (
                    <>
                      <Loader2 size={18} className="animate-spin inline mr-2" />
                      Rejecting...
                    </>
                  ) : (
                    <>
                      <X size={18} className="inline mr-2" />
                      Reject
                    </>
                  )}
                </button>
                <a
                  href={selectedSearch.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-liquid tertiary"
                  title="Open in new tab"
                >
                  <ExternalLink size={18} />
                </a>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
