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
import SquircleButton from '@/components/ui/SquircleButton';
import { AppLoadingState } from '@/components/ui/AppLoadingState';

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
    return <AppLoadingState variant="article" />;
  }

  if (isLoading) {
    return <AppLoadingState variant="article" />;
  }

  if (error) {
    return (
      <motion.main
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="min-h-screen flex items-center justify-center px-4"
      >
        <motion.div
          variants={itemVariants}
          className="error-dialog-glass p-12 text-center max-w-md"
        >
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
            <span className="text-2xl">⚠️</span>
          </div>
          <p className="text-lg font-semibold text-black">Failed to Load Article</p>
          <p className="mt-2 text-black/70">Something went wrong. Please try again.</p>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => router.back()}
            className="mt-6 mx-auto flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-6 py-2 font-semibold text-white transition-all hover:bg-blue-700 hover:shadow-lg"
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
        className="min-h-screen flex items-center justify-center px-4"
      >
        <motion.div
          variants={itemVariants}
          className="error-dialog-glass p-12 text-center max-w-md"
        >
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-yellow-100">
            <span className="text-2xl">📄</span>
          </div>
          <p className="text-lg font-semibold text-black">Article Not Found</p>
          <p className="mt-2 text-black/70">The article you&apos;re looking for doesn&apos;t exist.</p>
        </motion.div>
      </motion.main>
    );
  }

  return (
    <motion.main
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="article-detail-stage app-page-shell search-stage"
      id="main-content"
    >
      <div className="article-detail-container">
        {/* Back Button */}
        <motion.div
          variants={itemVariants}
          className="article-detail-backbar"
        >
          <SquircleButton
            variant="secondary"
            size="sm"
            onClick={() => router.back()}
          >
            <ArrowLeft className="h-5 w-5" />
            Back
          </SquircleButton>
        </motion.div>

      {/* Article Content */}
      <motion.article
        variants={containerVariants}
          className="article-reading-panel"
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
              className="mb-10"
          >
              <div className="article-summary-panel">
                <p className="article-summary-label">Summary</p>
                <p className="article-summary-text">
                  {article.summary}
                </p>
              </div>
          </motion.div>
        )}

        {/* Content */}
          <motion.div variants={itemVariants} className="article-body mb-12">
          {article.markdown_content ? (
              <MarkdownContent content={article.markdown_content} className="article-markdown" />
          ) : article.content ? (
              <div className="space-y-6 whitespace-pre-wrap text-base leading-8 text-black/75 sm:text-lg">
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
              className="mb-10 flex flex-wrap gap-2 border-b border-black/10 pb-8"
          >
            {article.tags.map((tag) => (
              <motion.span
                key={tag}
                whileHover={{ scale: 1.05 }}
                  className="article-tag-pill"
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
              className="mb-10"
          >
              <div className="article-source-panel">
                <p className="mb-3 text-xs font-bold uppercase tracking-[0.14em] text-black/45">Source</p>
              <a
                href={article.original_url}
                target="_blank"
                rel="noopener noreferrer"
                  className="flex items-center gap-2 break-all font-semibold text-[#007AFF] transition-colors hover:text-[#0A84FF]"
              >
                {article.original_url}
                <ExternalLink className="h-5 w-5 flex-shrink-0" />
              </a>
              </div>
          </motion.div>
        )}

        {/* Article Actions - CRUD Operations */}
        <motion.div
          variants={itemVariants}
            className="mb-10"
        >
            <div className="article-source-panel">
              <p className="mb-4 text-xs font-bold uppercase tracking-[0.14em] text-black/45">Actions</p>
            <div className="flex flex-wrap gap-3">
              {/* Edit Button */}
              <SquircleButton
                variant="primary"
                size="md"
                onClick={() => router.push(`/articles/${params.slug}/edit`)}
                aria-label="Edit article"
                title="Edit this article"
              >
                <Edit2 className="h-4 w-4" />
                Edit
              </SquircleButton>

              {/* Share Button */}
              <SquircleButton
                variant="secondary"
                size="md"
                onClick={async () => {
                  if (navigator.share) {
                    try {
                      await navigator.share({
                        title: article.title,
                        text: article.summary || article.title,
                        url: window.location.href,
                      });
                    } catch {
                      console.log('Share cancelled');
                    }
                  } else {
                    // Fallback: copy to clipboard
                    await navigator.clipboard.writeText(window.location.href);
                    alert('Link copied to clipboard!');
                  }
                }}
                aria-label="Share article"
                title="Share this article"
              >
                <Share2 className="h-4 w-4" />
                Share
              </SquircleButton>

              {/* Bookmark Button */}
              <SquircleButton
                variant={isBookmarked ? 'primary' : 'secondary'}
                size="md"
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
                aria-label={isBookmarked ? 'Remove bookmark' : 'Bookmark article'}
                title={isBookmarked ? 'Remove bookmark' : 'Bookmark this article'}
              >
                <Bookmark className={`h-4 w-4 ${isBookmarked ? 'fill-current' : ''}`} />
                {isBookmarked ? 'Saved' : 'Save'}
              </SquircleButton>

              {/* Delete Button */}
              <SquircleButton
                variant="secondary"
                size="md"
                onClick={async () => {
                  if (!confirm('Are you sure you want to delete this article? This action cannot be undone.')) {
                    return;
                  }
                  setIsDeleting(true);
                  try {
                    await apiClient.delete(`/articles/${params.slug}`);
                    alert('Article deleted successfully!');
                    router.push('/articles');
                  } catch (err) {
                    console.error('Delete failed:', err);
                    const errorMessage = err instanceof Error ? err.message : 'Failed to delete article';
                    alert(errorMessage);
                  } finally {
                    setIsDeleting(false);
                  }
                }}
                disabled={isDeleting}
                aria-label="Delete article"
                title="Delete this article permanently"
              >
                <Trash2 className="h-4 w-4" />
                {isDeleting ? 'Deleting...' : 'Delete'}
              </SquircleButton>
            </div>
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
      </div>
    </motion.main>
  );
}
