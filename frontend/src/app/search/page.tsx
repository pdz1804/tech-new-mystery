'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ChevronLeft, ChevronRight, Zap, X, Clock } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useSearchArticles } from '@/hooks/useSearch';
import { ArticleCard } from '@/components/article/ArticleCard';
import { ArticleCardSkeleton } from '@/components/ui/Skeleton';

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

function SearchContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const setIntendedDestination = useAuthStore((s) => s.setIntendedDestination);

  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [category, setCategory] = useState(searchParams.get('category') || '');
  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1'));
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [isFocused, setIsFocused] = useState(false);

  const { data, isLoading, error } = useSearchArticles(
    { q: query, category: category || undefined, page },
    !!query
  );

  useEffect(() => {
    if (!isHydrated) return;
    if (!isAuthenticated) {
      const params = new URLSearchParams();
      if (query) params.set('q', query);
      if (category) params.set('category', category);
      setIntendedDestination(`/search?${params.toString()}`);
      router.push('/login');
    }
  }, [isAuthenticated, isHydrated, router, setIntendedDestination, query, category]);

  useEffect(() => {
    const saved = localStorage.getItem('recentSearches');
    if (saved) {
      try {
        setRecentSearches(JSON.parse(saved));
      } catch {
        setRecentSearches([]);
      }
    }
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    if (query.trim()) {
      const updated = [query, ...recentSearches.filter(s => s !== query)].slice(0, 5);
      setRecentSearches(updated);
      localStorage.setItem('recentSearches', JSON.stringify(updated));
    }
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (category) params.set('category', category);
    router.push(`/search?${params.toString()}`);
  };

  const removeRecentSearch = (search: string) => {
    const updated = recentSearches.filter(s => s !== search);
    setRecentSearches(updated);
    localStorage.setItem('recentSearches', JSON.stringify(updated));
  };

  const clearSearch = () => {
    setQuery('');
    setCategory('');
    setPage(1);
  };

  if (!isHydrated || !isAuthenticated) {
    return null;
  }

  const categories = [
    'AI',
    'Web Development',
    'DevOps',
    'Security',
    'Mobile',
    'Cloud Computing',
    'Data Science',
    'Infrastructure',
    'Blockchain',
  ];

  return (
    <motion.main
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="min-h-screen bg-gradient-to-b from-slate-50 to-white"
    >
      {/* Hero Section */}
      <motion.section
        variants={itemVariants}
        className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-blue-500 to-indigo-600 px-4 py-20 md:py-28"
      >
        {/* Decorative background elements */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-white blur-3xl"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-blue-400 blur-3xl"></div>
        </div>

        <div className="relative mx-auto max-w-4xl">
          {/* Header */}
          <motion.div variants={itemVariants} className="text-center mb-12">
            <h1 className="text-5xl md:text-6xl font-bold mb-4 text-white">
              Find Articles
            </h1>
            <p className="text-lg md:text-xl text-blue-100 max-w-2xl mx-auto">
              Search across thousands of curated tech articles and stay ahead of the curve
            </p>
          </motion.div>

          {/* Search Form */}
          <motion.form
            variants={itemVariants}
            onSubmit={handleSearch}
            className="space-y-6"
          >
            {/* Search Input */}
            <div className="flex flex-col gap-4 mx-auto max-w-3xl">
              <div className="relative">
                <div className={`relative flex items-center rounded-xl transition-all duration-300 ${
                  isFocused
                    ? 'bg-white shadow-2xl ring-2 ring-blue-300'
                    : 'bg-white/95 shadow-lg hover:shadow-xl'
                }`}>
                  <Search
                    size={24}
                    className="absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-400 pointer-events-none flex-shrink-0"
                  />
                  <input
                    type="text"
                    placeholder="Search articles by keyword, topic, title..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    className="w-full pl-14 pr-14 py-4 text-lg text-slate-900 placeholder-slate-500 bg-transparent outline-none font-medium"
                    aria-label="Search articles"
                  />
                  {query && (
                    <motion.button
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.95 }}
                      type="button"
                      onClick={() => setQuery('')}
                      className="absolute right-4 p-2 text-slate-400 hover:text-slate-600 transition-colors"
                      aria-label="Clear search"
                    >
                      <X size={20} />
                    </motion.button>
                  )}
                </div>
              </div>

              {/* Category Filter Pills */}
              <motion.div
                variants={itemVariants}
                className="flex flex-wrap gap-2 justify-center"
              >
                {categories.map((cat) => {
                  const isActive = category === cat;
                  return (
                    <motion.button
                      key={cat}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      type="button"
                      onClick={() => {
                        setCategory(isActive ? '' : cat);
                        setPage(1);
                      }}
                      className={`px-4 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-300 ${
                        isActive
                          ? 'bg-white text-blue-600 shadow-lg'
                          : 'bg-white/20 text-white backdrop-blur-sm hover:bg-white/30 border border-white/30'
                      }`}
                      aria-pressed={isActive}
                      aria-label={`Filter by ${cat}`}
                    >
                      {cat}
                    </motion.button>
                  );
                })}
              </motion.div>

              {/* Active Filter Display */}
              {(query || category) && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="flex items-center justify-center gap-2"
                >
                  <button
                    onClick={clearSearch}
                    className="text-sm font-medium text-white/80 hover:text-white transition-colors flex items-center gap-2 bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg backdrop-blur-sm"
                  >
                    Clear search
                    <X size={16} />
                  </button>
                </motion.div>
              )}
            </div>
          </motion.form>
        </div>
      </motion.section>

      {/* Results Section */}
      <motion.section
        variants={itemVariants}
        className="mx-auto max-w-6xl px-4 py-16"
      >
        {!query ? (
          <motion.div variants={containerVariants} className="space-y-16">
            {/* Recent Searches */}
            {recentSearches.length > 0 && (
              <motion.div variants={itemVariants}>
                <div className="flex items-center gap-3 mb-8">
                  <Clock size={24} className="text-blue-600" />
                  <h2 className="text-2xl font-bold text-slate-900">Recent Searches</h2>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {recentSearches.map((search) => (
                    <motion.button
                      key={search}
                      whileHover={{ scale: 1.02, y: -2 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => {
                        setQuery(search);
                        const params = new URLSearchParams();
                        params.set('q', search);
                        if (category) params.set('category', category);
                        router.push(`/search?${params.toString()}`);
                      }}
                      className="group relative overflow-hidden rounded-xl border border-slate-200 bg-gradient-to-br from-blue-50 to-indigo-50 p-4 text-left transition-all hover:border-blue-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/0 via-blue-500/0 to-blue-500/0 group-hover:from-blue-500/5 group-hover:via-blue-500/5 group-hover:to-blue-500/5 transition-all"></div>
                      <div className="relative flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-slate-900 truncate group-hover:text-blue-600 transition-colors">{search}</p>
                          <p className="text-sm text-slate-500 mt-1">Search again</p>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            removeRecentSearch(search);
                          }}
                          className="ml-2 flex-shrink-0 p-1 rounded hover:bg-slate-200 text-slate-400 hover:text-slate-600 transition-colors"
                          aria-label={`Remove ${search} from recent searches`}
                        >
                          <X size={16} />
                        </button>
                      </div>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Empty State */}
            <motion.div
              variants={itemVariants}
              className="rounded-2xl border-2 border-dashed border-slate-300 bg-gradient-to-br from-slate-50 to-slate-100 p-16 text-center"
            >
              <motion.div
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 3, repeat: Infinity }}
                className="inline-block mb-4"
              >
                <div className="rounded-full bg-blue-100 p-6">
                  <Search size={40} className="text-blue-600" />
                </div>
              </motion.div>
              <h3 className="text-2xl font-bold text-slate-900 mb-2">Start Searching</h3>
              <p className="text-lg text-slate-600 mb-8">
                Enter keywords or browse by category to find articles that matter to you
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                {categories.slice(0, 3).map((cat) => (
                  <motion.button
                    key={cat}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setCategory(cat)}
                    className="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors"
                  >
                    Explore {cat}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          </motion.div>
        ) : isLoading ? (
          <motion.div
            variants={containerVariants}
            className="grid gap-6 md:grid-cols-2 lg:grid-cols-3"
          >
            {[...Array(6)].map((_, i) => (
              <ArticleCardSkeleton key={i} />
            ))}
          </motion.div>
        ) : error ? (
          <motion.div
            variants={itemVariants}
            className="rounded-2xl border border-red-200 bg-red-50 p-12 text-center"
          >
            <div className="inline-block mb-4 rounded-full bg-red-100 p-4">
              <Zap size={32} className="text-red-600" />
            </div>
            <h3 className="text-xl font-bold text-red-900 mb-2">Search Error</h3>
            <p className="text-red-700 mb-6">
              Something went wrong while searching. Please try again.
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setQuery('')}
              className="px-6 py-3 rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 transition-colors"
            >
              Try Again
            </motion.button>
          </motion.div>
        ) : data?.data && data.data.length > 0 ? (
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {/* Results Header */}
            <motion.div variants={itemVariants} className="mb-12">
              <div className="flex items-baseline gap-2 mb-4">
                <h2 className="text-3xl font-bold text-slate-900">Results</h2>
                <span className="text-lg text-slate-500">
                  {data.meta.total || 0} {data.meta.total === 1 ? 'article' : 'articles'} found
                </span>
              </div>
              <p className="text-slate-600">
                {category && (
                  <>
                    Showing <span className="font-semibold">{category}</span> articles for &quot;
                    <span className="font-semibold">{query}</span>&quot;
                  </>
                )}
                {!category && (
                  <>
                    Results for &quot;<span className="font-semibold">{query}</span>&quot;
                  </>
                )}
              </p>
            </motion.div>

            {/* Articles Grid */}
            <motion.div
              variants={containerVariants}
              className="mb-16 grid gap-6 md:grid-cols-2 lg:grid-cols-3"
            >
              {data.data.map((article) => (
                <ArticleCard
                  key={article.article_id}
                  id={article.article_id}
                  title={article.title}
                  slug={article.slug}
                  publishedAt={article.published_at || article.created_at}
                  category={article.category || undefined}
                  views={article.view_count}
                  summary={article.summary || undefined}
                />
              ))}
            </motion.div>

            {/* Pagination */}
            {data.meta.total && data.meta.total > (data.meta.limit || 10) && (
              <motion.div
                variants={itemVariants}
                className="flex items-center justify-center gap-4"
              >
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-3 font-semibold text-slate-700 transition-all hover:shadow-md hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500"
                  aria-label={`Go to previous page`}
                >
                  <ChevronLeft size={20} />
                  Previous
                </motion.button>
                <span className="rounded-lg border border-slate-300 bg-blue-50 px-6 py-3 font-semibold text-slate-900">
                  Page {page}
                </span>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setPage(page + 1)}
                  disabled={!data.meta.last_key}
                  className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-3 font-semibold text-slate-700 transition-all hover:shadow-md hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500"
                  aria-label={`Go to next page`}
                >
                  Next
                  <ChevronRight size={20} />
                </motion.button>
              </motion.div>
            )}
          </motion.div>
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
              <div className="rounded-full bg-slate-200 p-6">
                <Search size={40} className="text-slate-500" />
              </div>
            </motion.div>
            <h3 className="text-2xl font-bold text-slate-900 mb-2">No Articles Found</h3>
            <p className="text-lg text-slate-600 mb-8">
              Try different keywords, adjust your filters, or explore popular categories
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  setQuery('');
                  setCategory('');
                }}
                className="px-6 py-3 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors"
              >
                Clear All Filters
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => router.push('/articles')}
                className="px-6 py-3 rounded-lg border-2 border-blue-600 text-blue-600 font-medium hover:bg-blue-50 transition-colors"
              >
                Browse All Articles
              </motion.button>
            </div>
          </motion.div>
        )}
      </motion.section>
    </motion.main>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-50 flex items-center justify-center">Loading...</div>}>
      <SearchContent />
    </Suspense>
  );
}
