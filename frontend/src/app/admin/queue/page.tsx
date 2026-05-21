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
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [selectedSearch, setSelectedSearch] = useState<PendingSearch | null>(null);
  const [queryModalOpen, setQueryModalOpen] = useState(false);
  const [queryModalSource, setQueryModalSource] = useState<'tavily' | 'newsapi'>('tavily');

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

        const { data: response } = await apiClient.get('/admin/searches');

        if (response.success) {
          setSearches(response.data);
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
  }, [isHydrated]);

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
    setQueryModalSource(source);
    setQueryModalOpen(true);
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
        let pollCount = 0;
        const pollInterval = setInterval(async () => {
          pollCount++;
          if (pollCount > 24) {
            clearInterval(pollInterval);
            return;
          }
          try {
            const { data: response } = await apiClient.get('/admin/searches');
            if (response.success && response.data.length > 0) {
              setSearches(response.data);
              clearInterval(pollInterval);
            }
          } catch (err) {
            console.error('Error refreshing queue:', err);
          }
        }, 5000);
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
                  Review and approve search results ({searches.length} pending)
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
              </motion.div>
            </div>
          </div>
        </motion.div>
      </section>

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
          )}
        </div>
      </section>

      {/* Search Query Modal */}
      <SearchQueryModal
        isOpen={queryModalOpen}
        source={queryModalSource}
        defaultQueries={queryModalSource === 'tavily' ? DEFAULT_TAVILY_QUERIES : DEFAULT_NEWSAPI_QUERIES}
        onConfirm={handleConfirmSearch}
        onCancel={() => setQueryModalOpen(false)}
        isLoading={triggeringScheduler !== null}
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
