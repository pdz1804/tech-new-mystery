'use client';

import { useState, useEffect } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api/client';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Check, X, ExternalLink, Loader2, Zap, Eye } from 'lucide-react';

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
    // Protect route - redirect if not admin
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
        setSuccessMessage('Search approved and article created successfully');
        setTimeout(() => setSuccessMessage(null), 5000);
      } else {
        setError('Failed to approve search');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
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

  const handleTriggerScheduler = async (source: 'tavily' | 'newsapi') => {
    try {
      setTriggeringScheduler(source);
      setError(null);
      setSuccessMessage(null);

      const endpoint = source === 'tavily' ? '/admin/tavily/trigger' : '/admin/newsapi/trigger';
      const { data } = await apiClient.post(endpoint);

      if (data.success) {
        setSuccessMessage(data.message);
        // Auto-dismiss success message after 5 seconds
        setTimeout(() => setSuccessMessage(null), 5000);
        // Poll every 5 seconds for up to 2 minutes for new results (Tavily takes ~30s)
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
    // Remove markdown links and HTML tags, keep just plain text
    const cleaned = text
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1') // [text](url) → text
      .replace(/<[^>]+>/g, '') // remove HTML tags
      .replace(/\n+/g, ' ') // replace newlines with space
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-slate-900">Search Queue</h1>
            <p className="mt-2 text-slate-600">
              Review and approve search results ({searches.length} pending)
            </p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button
              type="button"
              onClick={() => handleTriggerScheduler('tavily')}
              disabled={triggeringScheduler !== null || loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all whitespace-nowrap"
              title="Manually trigger Tavily scheduler to fetch articles now"
            >
              {triggeringScheduler === 'tavily' ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span className="hidden sm:inline">Tavily...</span>
                </>
              ) : (
                <>
                  <Zap size={18} />
                  <span className="hidden sm:inline">Tavily</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => handleTriggerScheduler('newsapi')}
              disabled={triggeringScheduler !== null || loading}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all whitespace-nowrap"
              title="Manually trigger NewsAPI scheduler to fetch articles now"
            >
              {triggeringScheduler === 'newsapi' ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span className="hidden sm:inline">NewsAPI...</span>
                </>
              ) : (
                <>
                  <Zap size={18} />
                  <span className="hidden sm:inline">NewsAPI</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Success Message */}
        {successMessage && (
          <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4 text-green-700">
            {successMessage}
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
              >
                <Skeleton className="mb-3 h-5 w-1/3" />
                <Skeleton className="mb-2 h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            ))}
          </div>
        ) : searches.length === 0 ? (
          <div className="rounded-lg border border-slate-200 bg-white p-12 text-center shadow-sm">
            <p className="text-lg text-slate-600">No pending searches</p>
            <p className="mt-2 text-sm text-slate-500">
              Trigger Tavily or NewsAPI to fetch search results
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {searches.map((search) => (
              <div
                key={search.search_id}
                className="rounded-lg border border-slate-200 bg-white shadow-sm hover:shadow-md transition-shadow overflow-hidden"
              >
                <div className="p-5">
                  {/* Title Row */}
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-slate-900 line-clamp-2 hover:text-blue-600 cursor-pointer"
                        onClick={() => setSelectedSearch(search)}
                      >
                        {search.title}
                      </h3>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelectedSearch(search)}
                      className="flex-shrink-0 p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                      title="Preview article details"
                    >
                      <Eye size={20} />
                    </button>
                  </div>

                  {/* Snippet Preview */}
                  {search.snippet && (
                    <p className="text-sm text-slate-600 mb-3 line-clamp-2">
                      {cleanSnippet(search.snippet)}...
                    </p>
                  )}

                  {/* Metadata Row */}
                  <div className="flex flex-wrap items-center gap-2 mb-4">
                    <Badge className="bg-slate-100 text-slate-800 text-xs">
                      {search.query}
                    </Badge>
                    {search.source && (
                      <Badge className="bg-blue-100 text-blue-800 text-xs">
                        {search.source}
                      </Badge>
                    )}
                    <span className="text-xs text-slate-500">
                      {new Date(search.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  {/* Actions Row */}
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleApprove(search.search_id)}
                      disabled={actionLoading === search.search_id}
                      className="flex items-center gap-1.5 px-3 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm"
                    >
                      {actionLoading === search.search_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Check className="h-4 w-4" />
                      )}
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => handleReject(search.search_id)}
                      disabled={actionLoading === search.search_id}
                      className="flex items-center gap-1.5 px-3 py-2 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm"
                    >
                      {actionLoading === search.search_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <X className="h-4 w-4" />
                      )}
                      Reject
                    </button>
                    <a
                      href={search.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-auto flex items-center gap-1.5 px-3 py-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors text-sm"
                      title="Open source article in new tab"
                    >
                      View
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {selectedSearch && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedSearch(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-slate-200 p-6 flex items-start justify-between gap-4">
              <div className="flex-1">
                <h2 className="text-2xl font-bold text-slate-900 mb-3">
                  {selectedSearch.title}
                </h2>
                <div className="flex flex-wrap gap-2">
                  <Badge className="bg-slate-100 text-slate-800">
                    {selectedSearch.query}
                  </Badge>
                  {selectedSearch.source && (
                    <Badge className="bg-blue-100 text-blue-800">
                      {selectedSearch.source}
                    </Badge>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedSearch(null)}
                className="text-slate-400 hover:text-slate-600 p-2 hover:bg-slate-100 rounded-lg transition-colors flex-shrink-0"
                title="Close preview"
              >
                <X size={24} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-5">
              {/* Source Link */}
              <a
                href={selectedSearch.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-blue-600 hover:underline break-all text-sm"
              >
                {selectedSearch.url.substring(0, 70)}...
                <ExternalLink size={16} className="flex-shrink-0" />
              </a>

              {/* Content Preview */}
              {selectedSearch.snippet && (
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 max-h-96 overflow-y-auto">
                  <p className="text-slate-700 leading-relaxed whitespace-pre-wrap break-words">
                    {cleanSnippet(selectedSearch.snippet, 0)}
                  </p>
                  <p className="text-xs text-slate-500 mt-4 sticky bottom-0 bg-slate-50 py-2">
                    Review this content, then click Approve to create article or Reject to discard
                  </p>
                </div>
              )}

              {/* Metadata */}
              <div className="text-sm text-slate-600 py-4 border-y border-slate-200">
                <p>Found: {new Date(selectedSearch.created_at).toLocaleString()}</p>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="bg-slate-50 border-t border-slate-200 p-6 flex gap-3">
              <button
                type="button"
                onClick={() => handleApprove(selectedSearch.search_id)}
                disabled={actionLoading === selectedSearch.search_id}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {actionLoading === selectedSearch.search_id ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Creating...</span>
                  </>
                ) : (
                  <>
                    <Check className="h-5 w-5" />
                    <span>Approve & Create</span>
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={() => handleReject(selectedSearch.search_id)}
                disabled={actionLoading === selectedSearch.search_id}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {actionLoading === selectedSearch.search_id ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                  </>
                ) : (
                  <>
                    <X className="h-5 w-5" />
                  </>
                )}
                Delete
              </button>
              <button
                type="button"
                onClick={() => setSelectedSearch(null)}
                className="flex-1 px-4 py-3 bg-slate-200 text-slate-900 font-medium rounded-lg hover:bg-slate-300 transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
