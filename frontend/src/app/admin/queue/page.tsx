'use client';

import { useState, useEffect } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { apiClient } from '@/lib/api/client';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
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
        setSuccessMessage('✓ Search approved and article created');
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
        setSuccessMessage('✓ Search rejected successfully');
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

  const handleTriggerScheduler = async (source: 'tavily' | 'newsapi') => {
    try {
      setTriggeringScheduler(source);
      setError(null);
      setSuccessMessage(null);

      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const dateParam = yesterday.toISOString().split('T')[0];

      const endpoint = source === 'tavily' ? '/admin/tavily/trigger' : '/admin/newsapi/trigger';
      const params = new URLSearchParams();
      params.append(source === 'tavily' ? 'start_date' : 'from_date', dateParam);
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
    return null;
  }

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="relative min-h-screen"
    >
      {/* Hero Section */}
      <section className="section-glass pt-24">
        <motion.div
          variants={itemVariants}
          className="container-glass text-center mb-12"
        >
          <span className="text-label text-blue-400 mb-4 block uppercase">Admin Control</span>
          <h1 className="text-display mb-6 text-[rgba(255,255,255,0.95)]">Search Queue</h1>
          <p className="text-h3 font-normal mb-8 max-w-2xl mx-auto text-[rgba(255,255,255,0.65)]">
            Review and approve search results ({searches.length} pending)
          </p>

          {/* Trigger Buttons */}
          <motion.div
            variants={itemVariants}
            className="flex gap-4 justify-center flex-wrap"
          >
            <button
              type="button"
              onClick={() => handleTriggerScheduler('tavily')}
              disabled={triggeringScheduler !== null || loading}
              className="btn-liquid primary flex items-center gap-2"
              title="Fetch articles from Tavily"
            >
              <Zap size={20} />
              {triggeringScheduler === 'tavily' ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>Tavily...</span>
                </>
              ) : (
                <span>Tavily Search</span>
              )}
            </button>
            <button
              type="button"
              onClick={() => handleTriggerScheduler('newsapi')}
              disabled={triggeringScheduler !== null || loading}
              className="btn-liquid secondary flex items-center gap-2"
              title="Fetch articles from NewsAPI"
            >
              <Zap size={20} />
              {triggeringScheduler === 'newsapi' ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>NewsAPI...</span>
                </>
              ) : (
                <span>NewsAPI Search</span>
              )}
            </button>
          </motion.div>
        </motion.div>
      </section>

      {/* Content Section */}
      <section className="section-glass pb-20">
        <div className="container-glass">
          {/* Messages */}
          <AnimatePresence>
            {successMessage && (
              <motion.div
                variants={itemVariants}
                initial="hidden"
                animate="visible"
                exit={{ opacity: 0, y: -20 }}
                className="glass-panel p-4 border-green-500/50 mb-6 bg-gradient-to-r from-green-500/20 to-emerald-500/20"
              >
                <p className="text-green-300 font-semibold">{successMessage}</p>
              </motion.div>
            )}
            {error && (
              <motion.div
                variants={itemVariants}
                initial="hidden"
                animate="visible"
                exit={{ opacity: 0, y: -20 }}
                className="glass-panel p-4 border-red-500/50 mb-6 bg-gradient-to-r from-red-500/20 to-rose-500/20"
              >
                <p className="text-red-300 font-semibold">{error}</p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Queue List */}
          {loading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="glass-panel p-6">
                  <Skeleton className="mb-3 h-6 w-1/2" />
                  <Skeleton className="mb-2 h-4 w-full" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              ))}
            </div>
          ) : searches.length === 0 ? (
            <motion.div
              variants={itemVariants}
              className="glass-panel p-12 text-center"
            >
              <Eye size={48} className="mx-auto mb-4 text-[rgba(255,255,255,0.45)] opacity-50" />
              <p className="text-h3 mb-2 text-[rgba(255,255,255,0.95)]">No Pending Searches</p>
              <p className="text-body text-[rgba(255,255,255,0.65)]">
                Trigger Tavily or NewsAPI to fetch search results
              </p>
            </motion.div>
          ) : (
            <motion.div
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              className="space-y-4"
            >
              {searches.map((search) => (
                <motion.div
                  key={search.search_id}
                  variants={itemVariants}
                  className="glass-panel p-6 cursor-pointer hover:bg-white/[0.1]"
                  onClick={() => setSelectedSearch(search)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-h3 font-bold text-[rgba(255,255,255,0.95)] mb-2 hover:text-blue-400 transition-colors line-clamp-2">
                        {search.title}
                      </h3>
                      <p className="text-body text-[rgba(255,255,255,0.65)] mb-4 line-clamp-2">
                        {cleanSnippet(search.snippet, 120)}
                      </p>
                      <div className="flex flex-wrap gap-2 mb-4">
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
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-2 mt-4">
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
                      className="btn-liquid tertiary sm text-sm ml-auto"
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
              className="glass-panel floating max-w-2xl w-full max-h-[80vh] overflow-y-auto p-8 backdrop-blur-3xl backdrop-saturate-200"
            >
              <div className="mb-6">
                <h2 className="text-h2 font-bold text-[rgba(255,255,255,0.95)] mb-4">{selectedSearch.title}</h2>
                <p className="text-body text-[rgba(255,255,255,0.65)] mb-4 leading-relaxed">
                  {selectedSearch.snippet}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-8">
                <div className="glass-panel p-4">
                  <p className="text-label text-[rgba(255,255,255,0.65)] mb-2">Source</p>
                  <p className="text-body font-semibold text-[rgba(255,255,255,0.95)]">{selectedSearch.source || 'Unknown'}</p>
                </div>
                <div className="glass-panel p-4">
                  <p className="text-label text-[rgba(255,255,255,0.65)] mb-2">Date</p>
                  <p className="text-body font-semibold text-[rgba(255,255,255,0.95)]">
                    {new Date(selectedSearch.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
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
