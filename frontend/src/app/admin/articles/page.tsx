'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Edit2, Eye, Plus } from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { useArticles } from '@/hooks/useArticles';
import { ArticleCreateModal } from '@/components/article/ArticleCreateModal';
import { ArticleEditModal } from '@/components/article/ArticleEditModal';
import { useAuthStore } from '@/lib/stores/authStore';
import { format } from 'date-fns';
import type { ArticleResponse } from '@/types/article';
import { AppLoadingState } from '@/components/ui/AppLoadingState';

export default function ArticleManagementPage() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedArticle, setSelectedArticle] = useState<
    (ArticleResponse & { content?: string; author?: string }) | null
  >(null);
  const [showEditModal, setShowEditModal] = useState(false);

  const pageSize = 10;
  const { data, isLoading, error } = useArticles({
    page: currentPage,
    limit: pageSize,
  });

  // Check admin status
  useEffect(() => {
    if (!user?.is_admin) {
      router.push('/');
    }
  }, [user, router]);

  if (!user?.is_admin) {
    return <AppLoadingState variant="articles" />;
  }

  const articles = data?.data || [];
  const total = data?.meta.total || 0;
  const totalPages = Math.ceil(total / pageSize);

  // Filter articles by search query
  const filteredArticles = articles.filter((article) =>
    article.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleEditClick = (article: ArticleResponse) => {
    setSelectedArticle({
      ...article,
      content: '',
      author: article.title,
    });
    setShowEditModal(true);
  };

  const handleDeleteSuccess = () => {
    setShowEditModal(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-white to-slate-50 dark:from-slate-950 dark:to-slate-900 py-8">
      <div className="mx-auto max-w-6xl px-4">
        {/* Header */}
        <div className="mb-8">
          <h1 className="mb-2 text-4xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">Article Management</h1>
          <p className="text-slate-600">Manage and edit all articles in your system</p>
        </div>

        {/* Actions Bar */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Input
            placeholder="Search articles by title..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="flex-1"
          />
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="btn-primary flex items-center gap-2 whitespace-nowrap justify-center"
          >
            <Plus size={16} />
            Create Article
          </button>
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-gradient-to-br from-red-50 to-red-100 p-4 text-red-900 shadow-sm">
            Failed to load articles. Please try again.
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex justify-center py-12">
            <div className="text-slate-600">Loading articles...</div>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && filteredArticles.length === 0 && (
          <div className="rounded-xl border-2 border-dashed border-slate-300 bg-gradient-to-br from-slate-50 to-slate-100 p-12 text-center shadow-sm">
            <p className="text-slate-600">No articles found. {searchQuery && 'Try adjusting your search.'}</p>
          </div>
        )}

        {/* Articles Table */}
        {!isLoading && filteredArticles.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-lg glass-card">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 bg-gradient-to-r from-blue-50 to-indigo-50">
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Title</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Categories</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Quality</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Created</th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-slate-900">Views</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredArticles.map((article, idx) => (
                  <tr
                    key={article.article_id}
                    className={`border-b border-slate-100 transition-smooth ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'} hover:bg-blue-50/50`}
                  >
                    <td className="px-6 py-4">
                      <div>
                        <p className="font-semibold text-slate-900 line-clamp-1">{article.title}</p>
                        <p className="text-sm text-slate-500 mt-1">{article.slug}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-2">
                        {(article.categories && article.categories.length > 0
                          ? article.categories
                          : [article.category || 'Uncategorized']
                        ).map((cat) => (
                          <span
                            key={cat}
                            className="inline-block rounded-full bg-gradient-to-r from-blue-50 to-indigo-50 px-3 py-1 text-xs font-medium text-blue-700 border border-blue-200"
                          >
                            {cat}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      {article.quality_score !== undefined && article.quality_score !== null ? (
                        <div className="flex items-center justify-center gap-2">
                          <span
                            className={`inline-block rounded-full px-3 py-1 text-sm font-semibold ${
                              article.quality_score >= 8
                                ? 'bg-green-100 text-green-700'
                                : article.quality_score >= 5
                                  ? 'bg-amber-100 text-amber-700'
                                  : 'bg-red-100 text-red-700'
                            }`}
                          >
                            ★ {article.quality_score.toFixed(1)}
                          </span>
                        </div>
                      ) : (
                        <span className="text-sm text-slate-500">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600 font-medium">
                      {format(new Date(article.created_at), 'MMM d, yyyy')}
                    </td>
                    <td className="px-6 py-4 text-right text-sm font-semibold text-slate-900">
                      {article.view_count}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex justify-center gap-3">
                        <button
                          type="button"
                          onClick={() => window.open(`/articles/${article.slug}`, '_blank')}
                          className="rounded-lg p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 transition-smooth focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                          aria-label="View article"
                          title="View article"
                        >
                          <Eye size={18} />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleEditClick(article)}
                          className="rounded-lg p-2 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-smooth focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                          aria-label="Edit article"
                          title="Edit article"
                        >
                          <Edit2 size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!isLoading && totalPages > 1 && (
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4 py-6 border-t border-slate-200">
            <button
              type="button"
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-smooth disabled:opacity-50 disabled:cursor-not-allowed bg-white/50 backdrop-blur-sm text-slate-900 hover:bg-white/70 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              aria-label="Go to previous page"
            >
              Previous
            </button>
            <div className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 text-sm font-semibold text-slate-900 border border-blue-200">
              Page <span className="text-blue-600">{currentPage}</span> of <span className="text-blue-600">{totalPages}</span>
            </div>
            <button
              type="button"
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-smooth disabled:opacity-50 disabled:cursor-not-allowed bg-white/50 backdrop-blur-sm text-slate-900 hover:bg-white/70 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              aria-label="Go to next page"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* Modals */}
      <ArticleCreateModal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} />
      {selectedArticle && (
        <ArticleEditModal
          isOpen={showEditModal}
          article={selectedArticle}
          onClose={() => setShowEditModal(false)}
          onDeleteSuccess={handleDeleteSuccess}
        />
      )}
    </div>
  );
}
