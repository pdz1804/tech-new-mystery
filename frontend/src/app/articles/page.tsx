'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, Filter, Plus } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { apiClient } from '@/lib/api/client';
import { ArticleCard } from '@/components/article/ArticleCard';
import { ArticleCardSkeleton } from '@/components/ui/Skeleton';
import { ArticleCreateModal } from '@/components/article/ArticleCreateModal';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.15 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

interface ArticleResponse {
  success: boolean;
  data: Array<{
    article_id: string;
    title: string;
    slug: string;
    summary?: string;
    category?: string;
    view_count?: number;
    published_at?: string;
    created_at?: string;
  }>;
  meta: {
    limit: number;
    last_key?: {
      article_id: { S: string };
    };
  };
}

type SortOption = 'newest' | 'oldest' | 'popular';

const CATEGORIES = ['All', 'AI', 'Web Development', 'DevOps', 'Security', 'Mobile'];

export default function ArticlesPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const setIntendedDestination = useAuthStore((s) => s.setIntendedDestination);

  const [page, setPage] = useState(1);
  const [allArticles, setAllArticles] = useState<ArticleResponse['data']>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [sortBy, setSortBy] = useState<SortOption>('newest');
  const [showFilters, setShowFilters] = useState(false);
  const [isArticleModalOpen, setIsArticleModalOpen] = useState(false);

  const itemsPerPage = 12;

  useEffect(() => {
    if (!isHydrated) return;
    if (!isAuthenticated) {
      setIntendedDestination('/articles');
      router.push('/login');
    }
  }, [isAuthenticated, isHydrated, router, setIntendedDestination]);

  useEffect(() => {
    const fetchArticles = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data: responseData } = await apiClient.get<ArticleResponse>('/articles?limit=100');

        if (responseData.success) {
          setAllArticles(responseData.data);
        } else {
          setError('Failed to load articles');
        }
      } catch (err) {
        setError('Error loading articles');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    if (isAuthenticated) {
      fetchArticles();
    }
  }, [isAuthenticated]);

  if (!isHydrated || !isAuthenticated) {
    return null;
  }

  // Filter articles
  let filteredArticles = allArticles;
  if (selectedCategory !== 'All') {
    filteredArticles = filteredArticles.filter(
      (a) => a.category === selectedCategory
    );
  }

  // Sort articles
  const sortedArticles = [...filteredArticles].sort((a, b) => {
    if (sortBy === 'newest') {
      return new Date(b.published_at || b.created_at || 0).getTime() -
             new Date(a.published_at || a.created_at || 0).getTime();
    } else if (sortBy === 'oldest') {
      return new Date(a.published_at || a.created_at || 0).getTime() -
             new Date(b.published_at || b.created_at || 0).getTime();
    } else if (sortBy === 'popular') {
      return (b.view_count || 0) - (a.view_count || 0);
    }
    return 0;
  });

  // Pagination
  const totalPages = Math.ceil(sortedArticles.length / itemsPerPage);
  const startIdx = (page - 1) * itemsPerPage;
  const endIdx = startIdx + itemsPerPage;
  const currentArticles = sortedArticles.slice(startIdx, endIdx);

  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    setPage(1);
    setShowFilters(false);
  };

  const handleSortChange = (sort: SortOption) => {
    setSortBy(sort);
    setPage(1);
  };

  return (
    <>
      <ArticleCreateModal
        isOpen={isArticleModalOpen}
        onClose={() => {
          setIsArticleModalOpen(false);
          // Refresh articles list after creation
          const fetchArticles = async () => {
            try {
              const { data: responseData } = await apiClient.get<ArticleResponse>('/articles?limit=100');
              if (responseData.success) {
                setAllArticles(responseData.data);
              }
            } catch (err) {
              console.error(err);
            }
          };
          fetchArticles();
        }}
      />
      <motion.main
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="min-h-screen bg-white"
        id="main-content"
      >
      {/* Header */}
      <motion.section
        variants={itemVariants}
        className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-blue-500 to-indigo-600 px-4 py-20 md:py-28"
      >
        {/* Decorative background */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-white blur-3xl"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-blue-400 blur-3xl"></div>
        </div>

        <div className="relative mx-auto max-w-6xl">
          <motion.div variants={itemVariants} className="flex flex-col md:flex-row md:items-center md:justify-between gap-6 md:gap-0">
            <div className="space-y-3">
              <h1 className="text-5xl md:text-6xl font-bold text-white">
                Latest Articles
              </h1>
              <p className="text-lg md:text-xl text-blue-100">
                Explore {allArticles.length} curated articles on technology and innovation
              </p>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setIsArticleModalOpen(true)}
              className="flex items-center gap-2 px-6 py-3 bg-white text-blue-600 font-semibold rounded-xl shadow-lg hover:shadow-xl hover:bg-blue-50 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-300 whitespace-nowrap"
              aria-label="Create a new article"
            >
              <Plus size={20} aria-hidden="true" />
              Add Article
            </motion.button>
          </motion.div>
        </div>
      </motion.section>

      {/* Content Section */}
      <motion.section
        variants={itemVariants}
        className="mx-auto max-w-6xl px-4 py-16"
      >
        {/* Filters & Sort Bar */}
        <motion.div
          variants={itemVariants}
          className="mb-16 flex flex-col gap-8"
        >
          {/* Desktop Filter Bar */}
          <div className="hidden md:flex items-center justify-between gap-8 rounded-xl glass-card p-6">
            {/* Categories - Horizontal */}
            <div className="flex flex-wrap gap-3 flex-1">
              <span className="text-sm font-semibold text-slate-700 flex items-center">Filter:</span>
              {CATEGORIES.map((cat) => (
                <motion.button
                  key={cat}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => handleCategoryChange(cat)}
                  className={`px-4 py-2.5 rounded-full font-medium transition-smooth focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 text-sm ${
                    selectedCategory === cat
                      ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-lg'
                      : 'bg-white/50 backdrop-blur-sm text-slate-700 hover:bg-white/70 border border-white/50'
                  }`}
                  aria-pressed={selectedCategory === cat}
                  aria-label={`Filter articles by ${cat}`}
                >
                  {cat}
                </motion.button>
              ))}
            </div>

            {/* Sort Dropdown */}
            <div className="flex items-center gap-3 flex-shrink-0">
              <label htmlFor="sort" className="text-sm font-semibold text-slate-700">
                Sort:
              </label>
              <select
                id="sort"
                value={sortBy}
                onChange={(e) => handleSortChange(e.target.value as SortOption)}
                className="px-4 py-2.5 rounded-lg border border-white/50 bg-white/50 backdrop-blur-sm text-slate-900 font-medium hover:bg-white/70 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 text-sm transition-smooth"
                aria-label="Sort articles by newest, oldest, or most popular"
              >
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
                <option value="popular">Most Popular</option>
              </select>
            </div>
          </div>

          {/* Mobile Filter Button */}
          <div className="md:hidden flex items-center gap-2">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-700"
              aria-expanded={showFilters}
              aria-label={`${showFilters ? 'Close' : 'Open'} filters and sort options`}
            >
              <Filter size={20} aria-hidden="true" />
              Filters & Sort
            </motion.button>

            {selectedCategory !== 'All' && (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => handleCategoryChange('All')}
                className="px-3 py-3 text-sm bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-400"
                aria-label="Clear category filter and show all articles"
              >
                Clear
              </motion.button>
            )}
          </div>

          {/* Mobile Filter Panel */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="md:hidden glass-card p-4 space-y-4"
              >
                {/* Categories */}
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 mb-3">Categories</h3>
                  <div className="flex flex-wrap gap-2">
                    {CATEGORIES.map((cat) => (
                      <motion.button
                        key={cat}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => handleCategoryChange(cat)}
                        className={`px-4 py-3 rounded-full text-sm font-medium transition-smooth focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 ${
                          selectedCategory === cat
                            ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-lg'
                            : 'bg-white/50 backdrop-blur-sm text-slate-700 border border-white/50 hover:bg-white/70'
                        }`}
                        aria-pressed={selectedCategory === cat}
                        aria-label={`Filter by ${cat}`}
                      >
                        {cat}
                      </motion.button>
                    ))}
                  </div>
                </div>

                {/* Sort */}
                <div>
                  <label htmlFor="mobile-sort" className="text-sm font-semibold text-slate-900 mb-3 block">Sort by</label>
                  <select
                    id="mobile-sort"
                    value={sortBy}
                    onChange={(e) => {
                      handleSortChange(e.target.value as SortOption);
                      setShowFilters(false);
                    }}
                    className="w-full px-4 py-2 rounded-lg border border-white/50 bg-white/50 backdrop-blur-sm text-slate-900 font-medium hover:bg-white/70 transition-smooth"
                    aria-label="Sort articles by newest, oldest, or most popular"
                  >
                    <option value="newest">Newest First</option>
                    <option value="oldest">Oldest First</option>
                    <option value="popular">Most Popular</option>
                  </select>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Result Count */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-600">
              <span className="font-semibold text-slate-900">{sortedArticles.length}</span> article{sortedArticles.length !== 1 ? 's' : ''} {selectedCategory !== 'All' && `in ${selectedCategory}`}
            </div>
            {selectedCategory !== 'All' && (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => handleCategoryChange('All')}
                className="text-xs font-semibold text-blue-600 hover:text-blue-700 px-3 py-1 rounded-lg hover:bg-blue-50 transition-colors"
                aria-label="Clear category filter"
              >
                Clear Filter
              </motion.button>
            )}
          </div>
        </motion.div>

        {/* Articles Grid */}
        {isLoading ? (
          <motion.div
            variants={containerVariants}
            className="grid gap-6 md:grid-cols-2 lg:grid-cols-3"
          >
            {[...Array(12)].map((_, i) => (
              <ArticleCardSkeleton key={i} />
            ))}
          </motion.div>
        ) : error ? (
          <motion.div
            variants={itemVariants}
            className="rounded-xl border border-red-200 bg-red-50 p-8 text-center"
          >
            <p className="text-lg font-semibold text-red-900">{error}</p>
          </motion.div>
        ) : currentArticles.length > 0 ? (
          <>
            <motion.div
              className="mb-16 grid gap-6 md:grid-cols-2 lg:grid-cols-3"
            >
              {currentArticles.map((article, i) => (
                <motion.div
                  key={article.article_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.05 }}
                >
                  <ArticleCard
                    id={article.article_id}
                    title={article.title}
                    slug={article.slug}
                    publishedAt={article.published_at || article.created_at || new Date().toISOString()}
                    category={article.category}
                    views={article.view_count}
                    summary={article.summary}
                  />
                </motion.div>
              ))}
            </motion.div>

            {/* Modern Pagination */}
            {totalPages > 1 && (
              <motion.div
                variants={itemVariants}
                className="flex flex-col items-center justify-center gap-8 py-12 border-t-2 border-slate-200 mt-8"
              >
                {/* Pagination Controls */}
                <nav className="flex items-center gap-2 flex-wrap justify-center" aria-label="Pagination navigation">
                  {/* Previous Button */}
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => {
                      setPage(Math.max(1, page - 1));
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    disabled={page === 1}
                    className="flex items-center gap-1 px-4 py-3 rounded-lg font-medium transition-smooth disabled:opacity-50 disabled:cursor-not-allowed bg-white/50 backdrop-blur-sm text-slate-900 hover:bg-white/70 border border-white/50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                    aria-label={`Go to previous page (page ${Math.max(1, page - 1)})`}
                  >
                    <ChevronLeft size={18} aria-hidden="true" />
                    <span className="hidden sm:inline text-sm">Previous</span>
                  </motion.button>

                  {/* Page Numbers - Smart Pagination */}
                  <div className="flex items-center gap-1">
                    {/* First Page */}
                    {page > 3 && (
                      <>
                        <motion.button
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={() => {
                            setPage(1);
                            window.scrollTo({ top: 0, behavior: 'smooth' });
                          }}
                          className="h-11 w-11 rounded-lg font-semibold text-slate-900 bg-white/50 backdrop-blur-sm hover:bg-white/70 border border-white/50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-smooth"
                          aria-label="Go to page 1"
                        >
                          1
                        </motion.button>
                        {page > 4 && (
                          <span className="px-2 text-slate-600">…</span>
                        )}
                      </>
                    )}

                    {/* Page Range Around Current Page */}
                    {Array.from({ length: totalPages }, (_, i) => i + 1)
                      .filter(p => Math.abs(p - page) <= 2 || p === 1 || p === totalPages)
                      .map((p) => {
                        const shouldShow = Math.abs(p - page) <= 2 || p === 1 || p === totalPages;
                        if (!shouldShow) return null;

                        return (
                          <motion.button
                            key={p}
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => {
                              setPage(p);
                              window.scrollTo({ top: 0, behavior: 'smooth' });
                            }}
                            aria-label={`Go to page ${p}`}
                            aria-current={page === p ? 'page' : undefined}
                            className={`h-11 w-11 rounded-lg font-semibold transition-smooth focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                              page === p
                                ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-lg focus:ring-primary-700'
                                : 'bg-white/50 backdrop-blur-sm text-slate-900 hover:bg-white/70 border border-white/50 focus:ring-primary-500'
                            }`}
                          >
                            {p}
                          </motion.button>
                        );
                      })}

                    {/* Last Page */}
                    {page < totalPages - 2 && (
                      <>
                        {page < totalPages - 3 && (
                          <span className="px-2 text-slate-600">…</span>
                        )}
                        <motion.button
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={() => {
                            setPage(totalPages);
                            window.scrollTo({ top: 0, behavior: 'smooth' });
                          }}
                          className="h-11 w-11 rounded-lg font-semibold text-slate-900 bg-white/50 backdrop-blur-sm hover:bg-white/70 border border-white/50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-smooth"
                          aria-label={`Go to page ${totalPages}`}
                        >
                          {totalPages}
                        </motion.button>
                      </>
                    )}
                  </div>

                  {/* Next Button */}
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => {
                      setPage(Math.min(totalPages, page + 1));
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    disabled={page === totalPages}
                    className="flex items-center gap-1 px-4 py-3 rounded-lg font-medium transition-smooth disabled:opacity-50 disabled:cursor-not-allowed bg-white/50 backdrop-blur-sm text-slate-900 hover:bg-white/70 border border-white/50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                    aria-label={`Go to next page (page ${Math.min(totalPages, page + 1)})`}
                  >
                    <span className="hidden sm:inline text-sm">Next</span>
                    <ChevronRight size={18} aria-hidden="true" />
                  </motion.button>
                </nav>

                {/* Pagination Info */}
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 text-sm text-slate-600">
                  <span>
                    Page <span className="font-semibold text-slate-900">{page}</span> of{' '}
                    <span className="font-semibold text-slate-900">{totalPages}</span>
                  </span>
                  <span className="hidden sm:inline text-slate-400">•</span>
                  <span>
                    Showing <span className="font-semibold text-slate-900">{currentArticles.length}</span> of{' '}
                    <span className="font-semibold text-slate-900">{sortedArticles.length}</span> articles
                  </span>
                </div>
              </motion.div>
            )}
          </>
        ) : (
          <motion.div
            variants={itemVariants}
            className="rounded-2xl border-2 border-dashed border-slate-300 bg-gradient-to-br from-slate-50 to-slate-100 p-16 text-center"
          >
            <motion.div
              animate={{ opacity: [1, 0.5, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="inline-block mb-4"
            >
              <div className="inline-flex items-center justify-center h-20 w-20 rounded-full bg-slate-200 mb-4">
                <Filter size={40} className="text-slate-600" aria-hidden="true" />
              </div>
            </motion.div>
            <p className="text-2xl font-bold text-slate-900 mb-2">No articles found</p>
            <p className="text-lg text-slate-600 mb-8">
              Try adjusting your filters or selecting a different category
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => {
                setSelectedCategory('All');
                setPage(1);
              }}
              className="btn-primary"
              aria-label="Clear all filters and view all available articles"
            >
              View All Articles
            </motion.button>
          </motion.div>
        )}
      </motion.section>
    </motion.main>
    </>
  );
}
