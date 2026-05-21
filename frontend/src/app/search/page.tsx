'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Search, ChevronLeft, ChevronRight, Clock, TrendingUp } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useSearchArticles } from '@/hooks/useSearch';
import { useFilterMetadata } from '@/hooks/useFilterMetadata';
import { ArticleCard } from '@/components/article/ArticleCard';
import { ArticleCardSkeleton } from '@/components/ui/Skeleton';
import { AppLoadingState } from '@/components/ui/AppLoadingState';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6 } },
};

function SearchContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const setIntendedDestination = useAuthStore((s) => s.setIntendedDestination);

  const { data: filterData, isLoading: filterLoading } = useFilterMetadata();

  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [category, setCategory] = useState(searchParams.get('category') || '');
  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1'));
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [isFocused, setIsFocused] = useState(false);

  const { data, isLoading, error } = useSearchArticles(
    { q: query, category: category || undefined, page },
    !!query
  );

  const categories = filterData?.data?.categories || [];
  const suggestions = ['Agentic AI', 'AI infrastructure', 'Model safety', 'Edge AI', 'Robotics', 'AI chips'];

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
  };

  const handleCategoryClick = (cat: { name: string; count: number }) => {
    if (cat.count > 0) {
      setCategory(cat.name);
      setPage(1);
    }
  };

  const results = data?.data || [];
  const totalResults = data?.meta?.total || 0;
  const itemsPerPage = data?.meta?.limit || 12;
  const totalPages = Math.ceil(totalResults / itemsPerPage);

  if (!isHydrated || !isAuthenticated) {
    return <AppLoadingState variant="search" />;
  }

  return (
    <motion.main
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="search-stage relative min-h-screen"
      id="main-content"
    >
      <div className="browse-image-backdrop" aria-hidden="true">
        <picture>
          <source media="(max-width: 768px)" srcSet="/img/background-mobile-03.jpg" />
          <source media="(min-width: 769px)" srcSet="/img/background-web-03.jpg" />
          <img src="/img/background-web-03.jpg" alt="" />
        </picture>
      </div>

      {/* Hero Search Section */}
      <section className="app-page-shell pb-10">
        <motion.div
          variants={itemVariants}
          className="app-page-container"
        >
          <div className={`browse-search-stage ${query ? 'min-h-0 place-items-stretch' : ''}`}>
          <div className="browse-entry-panel mb-8">
            <div className="mx-auto mb-6 max-w-2xl">
              <span className="text-label mb-3 block text-blue-600">Browse</span>
              <h1 className="mb-3 font-sans text-4xl font-bold leading-tight text-black sm:text-5xl">Search the tech signal</h1>
              <p className="text-base text-black/60 sm:text-lg">
                Track AI systems, infrastructure, safety, chips, robotics, and emerging research.
              </p>
            </div>
            {/* Search Input */}
            <motion.form
              variants={itemVariants}
              onSubmit={handleSearch}
              className="browse-search-card"
            >
              <div className="relative flex w-full flex-col gap-3 sm:block">
                <input
                  type="text"
                  placeholder="Search agentic AI, model safety, AI chips..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onFocus={() => setIsFocused(true)}
                  onBlur={() => setTimeout(() => setIsFocused(false), 200)}
                  className="input-glass w-full py-4 text-base sm:text-lg"
                />
                <span className="browse-search-icon">
                  <Search size={18} />
                </span>
                <button
                  type="submit"
                  className="browse-search-submit"
                  aria-label="Search articles"
                  title="Search articles"
                >
                  Search
                </button>

                {/* Dropdown: Recent Searches & Quick Categories */}
                {isFocused && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-panel absolute left-0 right-0 top-full z-50 mt-2 p-6 text-left"
                  >
                  {recentSearches.length > 0 && (
                    <>
                      <p className="text-label text-black/60 mb-3 block">Recent Searches</p>
                      <div className="space-y-2 mb-6">
                        {recentSearches.map((s) => (
                          <button
                            key={s}
                            type="button"
                            onClick={() => {
                              setQuery(s);
                              setIsFocused(false);
                            }}
                            className="block w-full text-left px-3 py-2 text-body text-black/60 hover:text-black hover:bg-black/5 rounded-lg transition-all"
                          >
                            <Clock size={16} className="inline mr-2 opacity-50" />
                            {s}
                          </button>
                        ))}
                      </div>
                    </>
                  )}

                  <p className="text-label text-black/60 mb-3 block">Quick Categories</p>
                  <div className="flex flex-wrap gap-2">
                    {categories.slice(0, 5).map((cat) => (
                      <button
                        key={cat.name}
                        type="button"
                        onClick={() => {
                          handleCategoryClick(cat);
                          setIsFocused(false);
                        }}
                        disabled={cat.count === 0}
                        className={`px-3 py-1 rounded-lg text-sm transition-all ${
                          cat.count > 0
                            ? 'btn-liquid secondary'
                            : 'opacity-50 cursor-not-allowed'
                        }`}
                      >
                        {cat.name} ({cat.count})
                      </button>
                    ))}
                  </div>
                  </motion.div>
                )}
              </div>
            </motion.form>

            <div className="browse-suggestion-row mt-4">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => {
                    setQuery(suggestion);
                    setPage(1);
                  }}
                  className="compact-chip"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
          </div>

          {/* Quick Category Buttons */}
          {categories.length > 0 && query && (
            <motion.div
              variants={itemVariants}
              className="glass-panel mx-auto mb-8 max-w-5xl p-5"
            >
              <p className="text-label mb-4 block text-black/60">Browse By Category</p>
              <div className="grid gap-3 sm:grid-cols-3">
                {categories.slice(0, 3).map((cat) => (
                  <button
                    key={cat.name}
                    type="button"
                    onClick={() => handleCategoryClick(cat)}
                    disabled={cat.count === 0}
                    className={`apple-filter-button justify-center ${
                      cat.count > 0
                        ? ''
                        : 'opacity-50 cursor-not-allowed'
                    }`}
                  >
                      <TrendingUp size={18} className="inline mr-2" />
                    {cat.name} ({cat.count})
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </motion.div>
      </section>

      {/* Search Results */}
      {query && (
        <section className="pb-20">
          <div className="app-page-container">
            {/* Category Filter Bar */}
            {categories.length > 0 && (
              <motion.div
                variants={itemVariants}
                className="glass-panel mb-8 p-5"
              >
                <p className="text-label text-black/60 mb-4 block">FILTER BY CATEGORY</p>
                <div className="flex flex-wrap gap-2">
                  <motion.button
                    type="button"
                    onClick={() => {
                      setCategory('');
                      setPage(1);
                    }}
                    whileHover={{ scale: 1.05 }}
                    className={`px-4 py-2 rounded-lg font-medium transition-all ${
                      !category
                        ? 'btn-liquid primary'
                        : 'btn-liquid secondary'
                    }`}
                  >
                    All
                  </motion.button>
                  {categories.map((cat) => (
                    <motion.button
                      key={cat.name}
                      type="button"
                      onClick={() => handleCategoryClick(cat)}
                      whileHover={{ scale: 1.05 }}
                      disabled={cat.count === 0}
                      className={`px-4 py-2 rounded-lg font-medium transition-all ${
                        category === cat.name
                          ? 'btn-liquid primary'
                          : cat.count > 0
                          ? 'btn-liquid secondary'
                          : 'opacity-50 cursor-not-allowed'
                      }`}
                    >
                      {cat.name} ({cat.count})
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Results Info */}
            <motion.div
              variants={itemVariants}
              className="mb-8"
            >
              <p className="text-h3 font-bold text-black mb-2">
                Found {totalResults} result{totalResults !== 1 ? 's' : ''} for &quot;{query}&quot;
              </p>
              {category && (
                <p className="text-body text-black/60">
                  in <span className="text-blue-600 font-semibold">{category}</span>
                </p>
              )}
            </motion.div>

            {/* Results Grid or Loading/Error States */}
            {isLoading || filterLoading ? (
              <div className="glass-grid">
                {[...Array(12)].map((_, i) => (
                  <ArticleCardSkeleton key={i} />
                ))}
              </div>
            ) : error ? (
              <motion.div
                variants={itemVariants}
                className="glass-panel p-8 text-center border-red-500/50"
              >
                <p className="text-red-600 font-semibold">Error loading results</p>
                <p className="text-red-500 mt-2">{error.toString()}</p>
              </motion.div>
            ) : results.length > 0 ? (
              <>
                <motion.div
                  variants={containerVariants}
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true, amount: 0.1 }}
                  className="glass-grid mb-12"
                >
                  {results.map((article) => (
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
                {totalPages > 1 && (
                  <motion.div
                    variants={itemVariants}
                    className="flex items-center justify-center gap-4"
                  >
                    <button
                      type="button"
                      onClick={() => setPage(Math.max(1, page - 1))}
                      disabled={page === 1}
                      className="btn-liquid secondary p-2"
                      aria-label="Previous page"
                      title="Previous page"
                    >
                      <ChevronLeft size={20} />
                    </button>

                    <div className="flex gap-2">
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        const pageNum = Math.max(1, page - 2) + i;
                        return pageNum <= totalPages ? pageNum : null;
                      }).filter((p): p is number => p !== null).map((p) => (
                        <motion.button
                          key={p}
                          type="button"
                          onClick={() => setPage(p)}
                          whileHover={{ scale: 1.1 }}
                          className={`w-10 h-10 rounded-lg font-bold ${
                            page === p
                              ? 'btn-liquid primary'
                              : 'btn-liquid secondary'
                          }`}
                        >
                          {p}
                        </motion.button>
                      ))}
                    </div>

                    <button
                      type="button"
                      onClick={() => setPage(Math.min(totalPages, page + 1))}
                      disabled={page === totalPages}
                      className="btn-liquid secondary p-2"
                      aria-label="Next page"
                      title="Next page"
                    >
                      <ChevronRight size={20} />
                    </button>
                  </motion.div>
                )}
              </>
            ) : (
              <motion.div
                variants={itemVariants}
                className="glass-panel p-12 text-center"
              >
                <Search size={48} className="mx-auto mb-4 text-black/30 opacity-50" />
                <p className="text-h3 text-black/60 mb-2">No articles found</p>
                <p className="text-body text-black/60">
                  Try adjusting your search terms or category filters
                </p>
              </motion.div>
            )}
          </div>
        </section>
      )}

    </motion.main>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
      <SearchContent />
    </Suspense>
  );
}
