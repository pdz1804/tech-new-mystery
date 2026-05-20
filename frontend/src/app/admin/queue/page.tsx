'use client';

import { useState, useEffect } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api/client';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Check, X, ExternalLink, Loader2, Zap } from 'lucide-react';

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
  const [triggeringScheduler, setTriggeringScheduler] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

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

  const handleTriggerScheduler = async () => {
    try {
      setTriggeringScheduler(true);
      setError(null);
      setSuccessMessage(null);

      const { data } = await apiClient.post('/admin/tavily/trigger');

      if (data.success) {
        setSuccessMessage(data.message);
        // Auto-dismiss success message after 5 seconds
        setTimeout(() => setSuccessMessage(null), 5000);
        // Refresh queue after a delay to show new searches
        setTimeout(async () => {
          try {
            const { data: response } = await apiClient.get('/admin/searches');
            if (response.success) {
              setSearches(response.data);
            }
          } catch (err) {
            console.error('Error refreshing queue:', err);
          }
        }, 2000);
      } else {
        setError('Failed to trigger scheduler');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      console.error('Error triggering scheduler:', err);
    } finally {
      setTriggeringScheduler(false);
    }
  };

  if (!isHydrated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <div className="mb-8 flex items-start justify-between gap-4">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-slate-900">Search Queue</h1>
            <p className="mt-2 text-slate-600">
              Review and approve search results from Tavily ({searches.length} pending)
            </p>
          </div>
          <button
            type="button"
            onClick={handleTriggerScheduler}
            disabled={triggeringScheduler || loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all whitespace-nowrap flex-shrink-0"
            title="Manually trigger Tavily scheduler to fetch articles now"
          >
            {triggeringScheduler ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span className="hidden sm:inline">Triggering...</span>
              </>
            ) : (
              <>
                <Zap size={18} />
                <span className="hidden sm:inline">Trigger Tavily</span>
              </>
            )}
          </button>
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
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
              >
                <Skeleton className="mb-4 h-6 w-2/3" />
                <Skeleton className="mb-3 h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ))}
          </div>
        ) : searches.length === 0 ? (
          <div className="rounded-lg border border-slate-200 bg-white p-12 text-center shadow-sm">
            <p className="text-lg text-slate-600">No pending searches</p>
            <p className="mt-2 text-sm text-slate-500">
              Trigger Tavily to fetch search results or check back later
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {searches.map((search) => (
              <div
                key={search.search_id}
                className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="p-6">
                  {/* Title and URL */}
                  <div className="mb-4 flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="mb-2 text-lg font-semibold text-slate-900">
                        {search.title}
                      </h3>
                      <a
                        href={search.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:underline"
                      >
                        View source
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    </div>
                  </div>

                  {/* Snippet */}
                  {search.snippet && (
                    <p className="mb-4 text-sm text-slate-600 line-clamp-2">
                      {search.snippet}
                    </p>
                  )}

                  {/* Query and Source */}
                  <div className="mb-4 flex flex-wrap items-center gap-2">
                    <Badge className="bg-slate-100 text-slate-800">
                      {search.query}
                    </Badge>
                    {search.source && (
                      <Badge className="bg-blue-100 text-blue-800">
                        {search.source}
                      </Badge>
                    )}
                  </div>

                  {/* Created date */}
                  <p className="mb-4 text-xs text-slate-500">
                    Found{' '}
                    {new Date(search.created_at).toLocaleDateString()} at{' '}
                    {new Date(search.created_at).toLocaleTimeString()}
                  </p>

                  {/* Actions */}
                  <div className="flex gap-3">
                    <Button
                      onClick={() => handleApprove(search.search_id)}
                      disabled={actionLoading === search.search_id}
                      className="flex items-center gap-2 bg-green-600 hover:bg-green-700"
                    >
                      {actionLoading === search.search_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Check className="h-4 w-4" />
                      )}
                      Approve
                    </Button>
                    <Button
                      onClick={() => handleReject(search.search_id)}
                      disabled={actionLoading === search.search_id}
                      className="flex items-center gap-2 bg-red-600 hover:bg-red-700"
                    >
                      {actionLoading === search.search_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <X className="h-4 w-4" />
                      )}
                      Reject
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
