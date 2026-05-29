'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Share2,
  Bookmark,
  ExternalLink,
  Calendar,
  Eye,
  Badge as BadgeIcon,
} from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useClusterDetail, useClusterArticles } from '@/hooks/useClusters';
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

function formatDate(ts: number | null): string {
  if (!ts) return 'Unknown';
  const date = new Date(ts * 1000);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatTimeAgo(ts: number | null): string {
  if (!ts) return 'Unknown';
  const date = new Date(ts * 1000);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'Just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

function getSourceDomain(url: string): string {
  try {
    return new URL(url).hostname.replace('www.', '');
  } catch {
    return 'Source';
  }
}

type SortOption = 'date' | 'engagement' | 'title';

export default function ClusterDetailPage({ params }: { params: { slug: string } }) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const setIntendedDestination = useAuthStore((s) => s.setIntendedDestination);

  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<SortOption>('date');
  const [isBookmarked, setIsBookmarked] = useState(false);

  const { data: clusterDetail, isLoading: detailLoading, error: detailError } = useClusterDetail(params.slug);
  const { data: articlesData, isLoading: articlesLoading } = useClusterArticles(params.slug, {
    page,
    page_size: 20,
    sort: sortBy,
  });

  useEffect(() => {
    if (!isHydrated) return;
    if (!isAuthenticated) {
      setIntendedDestination(`/clusters/${params.slug}`);
      router.push('/login');
    }
  }, [isAuthenticated, isHydrated, router, setIntendedDestination, params.slug]);

  if (!isHydrated || !isAuthenticated) {
    return <AppLoadingState variant="article" />;
  }

  if (detailLoading) {
    return <AppLoadingState variant="article" />;
  }

  if (detailError || !clusterDetail) {
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
          <p className="text-lg font-semibold text-black">Failed to Load Cluster</p>
          <p className="mt-2 text-black/70">The cluster you&apos;re looking for doesn&apos;t exist or couldn&apos;t be loaded.</p>
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

  const articles = articlesData?.articles || [];
  const pagination = articlesData?.pagination || {
    total_count: clusterDetail.article_count,
    page: 1,
    page_size: 20,
    total_pages: Math.ceil(clusterDetail.article_count / 20),
  };

  const getVisiblePages = (currentPage: number, totalPages: number): (number | string)[] => {
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
  };

  const visiblePages = getVisiblePages(page, pagination.total_pages);

  const diversityColor =
    clusterDetail.diversity_score >= 0.6
      ? 'text-green-600'
      : clusterDetail.diversity_score >= 0.3
        ? 'text-amber-600'
        : 'text-orange-600';

  return (
    <motion.main
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="cluster-detail-stage app-page-shell search-stage"
      id="main-content"
    >
      <div className="cluster-detail-container">
        {/* Back Button */}
        <motion.div
          variants={itemVariants}
          className="cluster-detail-backbar mb-8"
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

        {/* Cluster Header */}
        <motion.div
          variants={itemVariants}
          className="cluster-header-panel mb-10 rounded-3xl bg-gradient-to-br from-slate-50 to-slate-100/50 p-8 backdrop-blur-sm border border-slate-200/50"
        >
          <div className="max-w-4xl">
            <h1 className="text-4xl font-bold text-black mb-3">{clusterDetail.label}</h1>
            <p className="text-lg text-black/70 mb-6 leading-relaxed max-w-2xl">
              {clusterDetail.description}
            </p>

            {/* Keywords/Tags */}
            {clusterDetail.keywords && clusterDetail.keywords.length > 0 && (
              <div className="mb-6 flex flex-wrap gap-2">
                {clusterDetail.keywords.map((keyword) => (
                  <motion.span
                    key={keyword}
                    whileHover={{ scale: 1.05 }}
                    className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1.5 text-sm font-medium text-blue-700"
                  >
                    <BadgeIcon className="h-3.5 w-3.5" />
                    {keyword}
                  </motion.span>
                ))}
              </div>
            )}

            {/* Metrics Row */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-6">
              <div className="rounded-xl bg-white/70 backdrop-blur-sm p-3 border border-slate-200/50">
                <p className="text-xs font-semibold uppercase text-black/50">Articles</p>
                <p className="text-2xl font-bold text-black mt-1">{clusterDetail.article_count}</p>
              </div>
              <div className="rounded-xl bg-white/70 backdrop-blur-sm p-3 border border-slate-200/50">
                <p className="text-xs font-semibold uppercase text-black/50">Diversity</p>
                <div className="flex items-center gap-1 mt-1">
                  <p className={`text-2xl font-bold ${diversityColor}`}>
                    {(clusterDetail.diversity_score * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
              <div className="rounded-xl bg-white/70 backdrop-blur-sm p-3 border border-slate-200/50">
                <p className="text-xs font-semibold uppercase text-black/50">Size</p>
                <p className="text-2xl font-bold text-black mt-1">{clusterDetail.size_category}</p>
              </div>
              <div className="rounded-xl bg-white/70 backdrop-blur-sm p-3 border border-slate-200/50">
                <p className="text-xs font-semibold uppercase text-black/50">Updated</p>
                <p className="text-xs font-medium text-black/70 mt-1">
                  {formatTimeAgo(clusterDetail.updated_at)}
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap gap-3">
              <SquircleButton
                variant="secondary"
                size="md"
                onClick={async () => {
                  if (navigator.share) {
                    try {
                      await navigator.share({
                        title: clusterDetail.label,
                        text: clusterDetail.description,
                        url: window.location.href,
                      });
                    } catch {
                      console.log('Share cancelled');
                    }
                  } else {
                    await navigator.clipboard.writeText(window.location.href);
                    alert('Link copied to clipboard!');
                  }
                }}
              >
                <Share2 className="h-4 w-4" />
                Share
              </SquircleButton>

              <SquircleButton
                variant={isBookmarked ? 'primary' : 'secondary'}
                size="md"
                onClick={() => {
                  setIsBookmarked(!isBookmarked);
                  const bookmarks = JSON.parse(localStorage.getItem('bookmarkedClusters') || '[]');
                  if (!isBookmarked) {
                    bookmarks.push(clusterDetail.id);
                  } else {
                    bookmarks.splice(bookmarks.indexOf(clusterDetail.id), 1);
                  }
                  localStorage.setItem('bookmarkedClusters', JSON.stringify(bookmarks));
                }}
              >
                <Bookmark className={`h-4 w-4 ${isBookmarked ? 'fill-current' : ''}`} />
                {isBookmarked ? 'Saved' : 'Save'}
              </SquircleButton>
            </div>
          </div>
        </motion.div>

        {/* Articles Section */}
        <motion.div variants={itemVariants} className="mb-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6">
            <h2 className="text-2xl font-bold text-black">
              Articles ({pagination.total_count})
            </h2>

            {/* Sorting */}
            <div className="segmented-glass">
              {(['date', 'engagement', 'title'] as const).map((sort) => (
                <button
                  key={sort}
                  type="button"
                  onClick={() => {
                    setSortBy(sort);
                    setPage(1);
                  }}
                  className={`segmented-item capitalize ${sortBy === sort ? 'active' : ''}`}
                >
                  <span>{sort}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Results Info */}
          <motion.div variants={itemVariants} className="mb-6">
            <p className="text-black/60 text-sm">
              Showing {articles.length} of {pagination.total_count} articles
            </p>
          </motion.div>

          {/* Articles List */}
          {articlesLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className="h-32 rounded-2xl bg-slate-200 animate-pulse"
                />
              ))}
            </div>
          ) : articles.length > 0 ? (
            <motion.div
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.05 }}
              className="space-y-4 mb-10"
            >
              {articles.map((article) => (
                <motion.article
                  key={article.id}
                  variants={itemVariants}
                  whileHover={{ scale: 1.01 }}
                  className="cluster-article-card group cursor-pointer rounded-2xl bg-white/60 backdrop-blur-sm border border-slate-200/70 p-5 transition-all hover:bg-white/80 hover:border-slate-300/70 hover:shadow-lg"
                >
                  <div
                    onClick={() => router.push(`/articles/${article.id}`)}
                    className="block"
                  >
                    <h3 className="text-lg font-semibold text-black mb-2 line-clamp-2 group-hover:text-blue-600 transition-colors">
                      {article.title}
                    </h3>

                    {article.summary && (
                      <p className="text-sm text-black/70 mb-3 line-clamp-2">
                        {article.summary}
                      </p>
                    )}

                    {/* Article Meta */}
                    <div className="flex flex-wrap items-center gap-4 text-xs text-black/60 mb-3">
                      <div className="flex items-center gap-1">
                        <span className="font-medium">{getSourceDomain(article.url)}</span>
                      </div>
                      {article.published_at && (
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3.5 w-3.5" />
                          <span>{formatDate(article.published_at)}</span>
                        </div>
                      )}
                      <div className="flex items-center gap-1">
                        <Eye className="h-3.5 w-3.5" />
                        <span>{article.engagement_score.toFixed(0)} views</span>
                      </div>
                      <div className="flex items-center gap-1 ml-auto">
                        <span className="font-medium text-blue-600">
                          {(article.confidence_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>

                    {/* Read More Link */}
                    <div className="flex items-center gap-1 text-sm font-semibold text-blue-600 group-hover:text-blue-700 transition-colors">
                      Read Article
                      <ExternalLink className="h-4 w-4" />
                    </div>
                  </div>
                </motion.article>
              ))}
            </motion.div>
          ) : (
            <motion.div variants={itemVariants} className="apple-empty-state p-6 text-center">
              <p className="text-black/60">No articles found in this cluster.</p>
            </motion.div>
          )}

          {/* Pagination */}
          {pagination.total_pages > 1 && (
            <motion.div
              variants={itemVariants}
              className="flex items-center justify-center gap-2 mt-10 flex-wrap"
            >
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-black transition-all hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>

              {visiblePages.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    if (typeof p === 'number') {
                      setPage(p);
                    }
                  }}
                  disabled={p === '...'}
                  className={`inline-flex items-center justify-center rounded-lg px-3 py-2 text-sm font-semibold transition-all ${
                    p === page
                      ? 'bg-blue-600 text-white'
                      : p === '...'
                        ? 'cursor-not-allowed text-black/60'
                        : 'border border-slate-300 text-black hover:bg-slate-100'
                  }`}
                >
                  {p}
                </button>
              ))}

              <button
                onClick={() => setPage(Math.min(pagination.total_pages, page + 1))}
                disabled={page === pagination.total_pages}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-black transition-all hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </motion.div>
          )}
        </motion.div>
      </div>
    </motion.main>
  );
}
