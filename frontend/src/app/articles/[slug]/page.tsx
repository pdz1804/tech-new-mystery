'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowLeft, ExternalLink, Tag as TagIcon, Edit2, Trash2, Share2, Bookmark } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useArticleBySlug } from '@/hooks/useArticles';
import { apiClient } from '@/lib/api/client';
import { ArticleHeader } from '@/components/article/ArticleHeader';
import { MarkdownContent } from '@/components/article/MarkdownContent';
import { CommentThread } from '@/components/article/CommentThread';
import { RelatedArticles } from '@/components/article/RelatedArticles';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export default function ArticleDetailPage({ params }: { params: { slug: string } }) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const setIntendedDestination = useAuthStore((s) => s.setIntendedDestination);
  const { data, isLoading, error } = useArticleBySlug(params.slug);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (!isHydrated) return;
    if (!isAuthenticated) {
      setIntendedDestination(`/articles/${params.slug}`);
      router.push('/login');
    }
  }, [isAuthenticated, isHydrated, router, setIntendedDestination, params.slug]);

  if (!isHydrated || !isAuthenticated) {
    return null;
  }

  if (isLoading) {
    return (
      <motion.main
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="min-h-screen bg-white"
      >
        <div className="mx-auto max-w-4xl px-4 py-12">
          <motion.div variants={itemVariants} className="animate-pulse space-y-6">
            <div className="h-8 w-32 rounded-lg bg-slate-300" />
            <div className="h-12 w-3/4 rounded-lg bg-slate-300" />
            <div className="h-6 w-1/2 rounded-lg bg-slate-300" />
            <div className="space-y-3">
              {[...Array(10)].map((_, i) => (
                <div key={i} className="h-4 rounded-lg bg-slate-200" />
              ))}
            </div>
          </motion.div>
        </div>
      </motion.main>
    );
  }

  if (error) {
    return (
      <motion.main
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="min-h-screen bg-white flex items-center justify-center px-4"
      >
        <motion.div
          variants={itemVariants}
          className="rounded-2xl border border-slate-200 bg-white p-12 text-center max-w-md shadow-lg"
        >
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
            <span className="text-2xl">⚠️</span>
          </div>
          <p className="text-lg font-semibold text-slate-900">Failed to Load Article</p>
          <p className="mt-2 text-slate-600">Something went wrong. Please try again.</p>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => router.back()}
            className="mt-6 mx-auto flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-6 py-2 font-semibold text-white transition-all hover:shadow-button-primary"
          >
            <ArrowLeft className="h-4 w-4" />
            Go Back
          </motion.button>
        </motion.div>
      </motion.main>
    );
  }

  const article = data?.data;
  if (!article) {
    return (
      <motion.main
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="min-h-screen bg-white flex items-center justify-center px-4"
      >
        <motion.div
          variants={itemVariants}
          className="rounded-2xl border border-slate-200 bg-white p-12 text-center max-w-md shadow-lg"
        >
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-yellow-100">
            <span className="text-2xl">📄</span>
          </div>
          <p className="text-lg font-semibold text-slate-900">Article Not Found</p>
          <p className="mt-2 text-slate-600">The article you&apos;re looking for doesn&apos;t exist.</p>
        </motion.div>
      </motion.main>
    );
  }

  return (
    <motion.main
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="min-h-screen bg-white"
    >
      {/* Back Button Bar */}
      <motion.div
        variants={itemVariants}
        className="sticky top-16 bg-white border-b border-slate-200 shadow-sm"
      >
        <div className="mx-auto max-w-4xl px-4 py-4">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => router.back()}
            className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 font-semibold text-blue-600 transition-all hover:bg-slate-50 hover:shadow-sm"
          >
            <ArrowLeft className="h-5 w-5" />
            Back
          </motion.button>
        </div>
      </motion.div>

      {/* Article Content */}
      <motion.article
        variants={containerVariants}
        className="mx-auto max-w-4xl px-4 py-12"
      >
        {/* Article Header */}
        <ArticleHeader
          category={article.category || undefined}
          title={article.title}
          publishedAt={article.published_at || article.created_at}
          author={article.author || undefined}
          views={article.view_count}
        />

        {/* Summary Box */}
        {article.summary && (
          <motion.div
            variants={itemVariants}
            className="mb-12 rounded-xl border border-blue-200 bg-blue-50 p-8"
          >
            <div className="border-l-4 border-blue-600 pl-6">
              <p className="text-lg font-medium text-slate-900 leading-relaxed">
                {article.summary}
              </p>
            </div>
          </motion.div>
        )}

        {/* Content */}
        <motion.div variants={itemVariants} className="mb-12">
          {article.markdown_content ? (
            <MarkdownContent content={article.markdown_content} />
          ) : article.content ? (
            <div className="space-y-6 text-slate-800 leading-relaxed whitespace-pre-wrap">
              {article.content}
            </div>
          ) : (
            <p className="text-slate-600 italic">No content available for this article.</p>
          )}
        </motion.div>

        {/* Tags */}
        {article.tags && article.tags.length > 0 && (
          <motion.div
            variants={itemVariants}
            className="mb-12 flex flex-wrap gap-2 border-b border-slate-200 pb-8"
          >
            {article.tags.map((tag) => (
              <motion.span
                key={tag}
                whileHover={{ scale: 1.05 }}
                className="inline-flex items-center gap-1 rounded-full bg-primary-50 px-4 py-2 text-sm font-semibold text-primary-600 transition-colors hover:bg-primary-100 border border-primary-200"
              >
                <TagIcon className="h-4 w-4" />
                {tag}
              </motion.span>
            ))}
          </motion.div>
        )}

        {/* Source Link */}
        {article.original_url && (
          <motion.div
            variants={itemVariants}
            className="rounded-lg border border-slate-200 bg-white p-6 mb-12 shadow-sm"
          >
            <p className="mb-3 text-xs font-semibold text-slate-600">SOURCE</p>
            <a
              href={article.original_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-blue-600 font-semibold transition-colors hover:text-blue-700 break-all"
            >
              {article.original_url}
              <ExternalLink className="h-5 w-5 flex-shrink-0" />
            </a>
          </motion.div>
        )}

        {/* Article Actions - CRUD Operations */}
        <motion.div
          variants={itemVariants}
          className="rounded-lg border border-slate-200 bg-white p-6 mb-12 shadow-sm"
        >
          <p className="mb-4 text-xs font-semibold text-slate-600">ACTIONS</p>
          <div className="flex flex-wrap gap-3">
            {/* Edit Button */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => router.push(`/articles/${params.slug}/edit`)}
              className="btn-primary flex items-center gap-2"
              aria-label="Edit article"
              title="Edit this article"
            >
              <Edit2 className="h-4 w-4" />
              Edit
            </motion.button>

            {/* Share Button */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={async () => {
                if (navigator.share) {
                  try {
                    await navigator.share({
                      title: article.title,
                      text: article.summary || article.title,
                      url: window.location.href,
                    });
                  } catch (err) {
                    console.log('Share cancelled');
                  }
                } else {
                  // Fallback: copy to clipboard
                  await navigator.clipboard.writeText(window.location.href);
                  alert('Link copied to clipboard!');
                }
              }}
              className="flex items-center gap-2 rounded-lg bg-green-50 px-4 py-2.5 text-green-700 font-semibold hover:bg-green-100 transition-colors focus:outline-none focus:ring-2 focus:ring-green-500"
              aria-label="Share article"
              title="Share this article"
            >
              <Share2 className="h-4 w-4" />
              Share
            </motion.button>

            {/* Bookmark Button */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => {
                setIsBookmarked(!isBookmarked);
                // Save to localStorage
                const bookmarks = JSON.parse(localStorage.getItem('bookmarkedArticles') || '[]');
                if (!isBookmarked) {
                  bookmarks.push(article.article_id);
                } else {
                  bookmarks.splice(bookmarks.indexOf(article.article_id), 1);
                }
                localStorage.setItem('bookmarkedArticles', JSON.stringify(bookmarks));
              }}
              className={`flex items-center gap-2 rounded-lg px-4 py-2.5 font-semibold transition-colors focus:outline-none focus:ring-2 ${
                isBookmarked
                  ? 'bg-amber-50 text-amber-700 hover:bg-amber-100 focus:ring-amber-500'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200 focus:ring-slate-500'
              }`}
              aria-label={isBookmarked ? 'Remove bookmark' : 'Bookmark article'}
              title={isBookmarked ? 'Remove bookmark' : 'Bookmark this article'}
            >
              <Bookmark className={`h-4 w-4 ${isBookmarked ? 'fill-current' : ''}`} />
              {isBookmarked ? 'Saved' : 'Save'}
            </motion.button>

            {/* Delete Button */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={async () => {
                if (!confirm('Are you sure you want to delete this article? This action cannot be undone.')) {
                  return;
                }
                setIsDeleting(true);
                try {
                  await apiClient.delete(`/articles/${params.slug}`);
                  alert('Article deleted successfully!');
                  router.push('/articles');
                } catch (err: any) {
                  console.error('Delete failed:', err);
                  alert(err.response?.data?.detail || 'Failed to delete article');
                } finally {
                  setIsDeleting(false);
                }
              }}
              disabled={isDeleting}
              className="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-2.5 text-red-700 font-semibold hover:bg-red-100 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Delete article"
              title="Delete this article permanently"
            >
              <Trash2 className="h-4 w-4" />
              {isDeleting ? 'Deleting...' : 'Delete'}
            </motion.button>
          </div>
        </motion.div>

        {/* Comments Section */}
        <motion.div variants={itemVariants}>
          <CommentThread articleId={article.article_id} />
        </motion.div>

        {/* Related Articles */}
        {((article as { related_articles?: Array<{ article_id: string; title: string; slug: string; created_at: string; view_count: number }> }).related_articles?.length ?? 0) > 0 && (
          <RelatedArticles
            articles={(article as { related_articles?: Array<{ article_id: string; title: string; slug: string; created_at: string; view_count: number }> }).related_articles || []}
          />
        )}
      </motion.article>
    </motion.main>
  );
}
