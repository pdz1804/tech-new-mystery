'use client';

import { useState, useEffect } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api/client';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Check, X, ExternalLink, Loader2 } from 'lucide-react';

interface PendingArticle {
  article_id: string;
  title: string;
  slug: string;
  summary: string | null;
  category: string | null;
  tags: string[];
  original_url: string;
  source_id: string;
  created_at: string;
}

export default function AdminQueuePage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const isHydrated = useAuthStore((s) => s.isHydrated);

  const [articles, setArticles] = useState<PendingArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

        const { data: response } = await apiClient.get('/admin/articles/queue');

        if (response.success) {
          setArticles(response.data);
        } else {
          setError('Failed to load pending articles');
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

  const handleApprove = async (articleId: string) => {
    try {
      setActionLoading(articleId);
      const { data } = await apiClient.post(`/admin/articles/${articleId}/approve`);

      if (data.success) {
        setArticles(articles.filter((a) => a.article_id !== articleId));
      } else {
        setError('Failed to approve article');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      console.error('Error approving article:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (articleId: string) => {
    try {
      setActionLoading(articleId);
      const { data } = await apiClient.delete(`/admin/articles/${articleId}/reject`);

      if (data.success) {
        setArticles(articles.filter((a) => a.article_id !== articleId));
      } else {
        setError('Failed to reject article');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      console.error('Error rejecting article:', err);
    } finally {
      setActionLoading(null);
    }
  };

  if (!isHydrated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900">Article Queue</h1>
          <p className="mt-2 text-slate-600">
            Review and approve articles fetched via Tavily ({articles.length} pending)
          </p>
        </div>

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
        ) : articles.length === 0 ? (
          <div className="rounded-lg border border-slate-200 bg-white p-12 text-center shadow-sm">
            <p className="text-lg text-slate-600">No pending articles</p>
            <p className="mt-2 text-sm text-slate-500">
              Check back later when new articles are fetched
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {articles.map((article) => (
              <div
                key={article.article_id}
                className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="p-6">
                  {/* Title and URL */}
                  <div className="mb-4 flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="mb-2 text-lg font-semibold text-slate-900">
                        {article.title}
                      </h3>
                      <a
                        href={article.original_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:underline"
                      >
                        View source
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    </div>
                  </div>

                  {/* Summary */}
                  {article.summary && (
                    <p className="mb-4 text-sm text-slate-600 line-clamp-2">
                      {article.summary}
                    </p>
                  )}

                  {/* Category and Tags */}
                  <div className="mb-4 flex flex-wrap items-center gap-2">
                    {article.category && (
                      <Badge className="bg-slate-100 text-slate-800">
                        {article.category}
                      </Badge>
                    )}
                    {article.tags.slice(0, 3).map((tag) => (
                      <Badge key={tag} className="bg-blue-100 text-blue-800">
                        {tag}
                      </Badge>
                    ))}
                    {article.tags.length > 3 && (
                      <span className="text-xs text-slate-500">
                        +{article.tags.length - 3} more
                      </span>
                    )}
                  </div>

                  {/* Created date */}
                  <p className="mb-4 text-xs text-slate-500">
                    Created{' '}
                    {new Date(article.created_at).toLocaleDateString()} at{' '}
                    {new Date(article.created_at).toLocaleTimeString()}
                  </p>

                  {/* Actions */}
                  <div className="flex gap-3">
                    <Button
                      onClick={() => handleApprove(article.article_id)}
                      disabled={actionLoading === article.article_id}
                      className="flex items-center gap-2 bg-green-600 hover:bg-green-700"
                    >
                      {actionLoading === article.article_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Check className="h-4 w-4" />
                      )}
                      Approve
                    </Button>
                    <Button
                      onClick={() => handleReject(article.article_id)}
                      disabled={actionLoading === article.article_id}
                      className="flex items-center gap-2 bg-red-600 hover:bg-red-700"
                    >
                      {actionLoading === article.article_id ? (
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
