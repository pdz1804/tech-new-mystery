'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Search, ChevronLeft, ChevronRight, Zap, Clock, TrendingUp } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useSearchArticles } from '@/hooks/useSearch';
import { useFilterMetadata } from '@/hooks/useFilterMetadata';
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
    return null;
  }

  return (
    <motion.main
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="relative min-h-screen"
      id="main-content"
    >
      {/* Hero Search Section */}
      <section className="section-glass pt-24">
        <motion.div
          variants={itemVariants}
          className="container-glass"
        >
          <div className="text-center mb-12">
            <span className="text-label text-blue-400 mb-4 block">DISCOVERY</span>
            <h1 className="text-display mb-6 text-[rgba(255,255,255,0.95)]">Find Your Tech Stories</h1>
            <p className="text-h3 font-normal mb-8 max-w-2xl mx-auto text-[rgba(255,255,255,0.65)]">
              Search across curated technology articles
            </p>
          </div>

          {/* Search Input */}
          <motion.form
            variants={itemVariants}
            onSubmit={handleSearch}
            className="max-w-2xl mx-auto mb-16"
          >
            <div className="relative">
              <input
                type="text"
                placeholder="Search articles..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setTimeout(() => setIsFocused(false), 200)}
                className="w-full input-glass pl-14 pr-6 py-4 text-lg"
              />
              <Search size={24} className="absolute left-4 top-1/2 -translate-y-1/2 text-blue-400 pointer-events-none" />
              <button
                type="submit"
                className="absolute right-2 top-1/2 -translate-y-1/2 btn-liquid primary px-6 py-2"
                aria-label="Search articles"
                title="Search articles"
              >
                <Zap size={18} />
              </button>

              {/* Dropdown: Recent Searches & Quick Categories */}
              {isFocused && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute top-full left-0 right-0 mt-2 glass-panel p-6 z-50"
                >
                  {recentSearches.length > 0 && (
                    <>
                      <p className="text-label text-[rgba(255,255,255,0.65)] mb-3 block">Recent Searches</p>
                      <div className="space-y-2 mb-6">
                        {recentSearches.map((s) => (
                          <button
                            key={s}
                            type="button"
                            onClick={() => {
                              setQuery(s);
                              setIsFocused(false);
                            }}
                            className="block w-full text-left px-3 py-2 text-body text-[rgba(255,255,255,0.65)] hover:text-white hover:bg-white/10 rounded-lg transition-all"
                          >
                            <Clock size={16} className="inline mr-2 opacity-50" />
                            {s}
                          </button>
                        ))}
                      </div>
                    </>
                  )}

                  <p className="text-label text-[rgba(255,255,255,0.65)] mb-3 block">Quick Categories</p>
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

          {/* Quick Category Buttons */}
          {categories.length > 0 && !query && (
            <motion.div
              variants={itemVariants}
              className="text-center"
            >
              <p className="text-label text-[rgba(255,255,255,0.65)] mb-4 block">OR BROWSE BY CATEGORY</p>
              <div className="flex flex-wrap justify-center gap-3">
                {categories.slice(0, 3).map((cat) => (
                  <button
                    key={cat.name}
                    type="button"
                    onClick={() => handleCategoryClick(cat)}
                    disabled={cat.count === 0}
                    className={`px-6 py-3 rounded-lg font-semibold transition-all ${
                      cat.count > 0
                        ? 'btn-liquid primary'
                        : 'opacity-50 cursor-not-allowed'
                    }`}
                  >
                    <TrendingUp size={18} className="inline mr-2" />
                    Explore {cat.name} ({cat.count})
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </motion.div>
      </section>

      {/* Search Results */}
      {query && (
        <section className="section-glass pb-20">
          <div className="container-glass">
            {/* Category Filter Bar */}
            {categories.length > 0 && (
              <motion.div
                variants={itemVariants}
                className="glass-panel p-6 mb-12"
              >
                <p className="text-label text-[rgba(255,255,255,0.65)] mb-4 block">FILTER BY CATEGORY</p>
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
              <p className="text-h3 font-bold text-[rgba(255,255,255,0.95)] mb-2">
                Found {totalResults} result{totalResults !== 1 ? 's' : ''} for &quot;{query}&quot;
              </p>
              {category && (
                <p className="text-body text-[rgba(255,255,255,0.65)]">
                  in <span className="text-blue-400 font-semibold">{category}</span>
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
                <p className="text-red-300 font-semibold">Error loading results</p>
                <p className="text-red-200 mt-2">{error.toString()}</p>
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
                <Search size={48} className="mx-auto mb-4 text-[rgba(255,255,255,0.45)] opacity-50" />
                <p className="text-h3 text-[rgba(255,255,255,0.65)] mb-2">No articles found</p>
                <p className="text-body text-[rgba(255,255,255,0.65)]">
                  Try adjusting your search terms or category filters
                </p>
              </motion.div>
            )}
          </div>
        </section>
      )}

      {/* Empty State: Suggestions */}
      {!query && (
        <section className="section-glass pb-20">
          <div className="container-glass">
            <motion.div
              variants={itemVariants}
              className="text-center"
            >
              <Search size={64} className="mx-auto mb-6 text-[rgba(255,255,255,0.45)] opacity-30" />
              <h2 className="text-h2 mb-4 text-[rgba(255,255,255,0.95)]">Start Exploring</h2>
              <p className="text-body text-[rgba(255,255,255,0.65)] max-w-2xl mx-auto">
                Enter a search term above or choose a category to discover amazing tech articles
              </p>
            </motion.div>
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
