'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, Filter, Plus } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { apiClient } from '@/lib/api/client';
import { ArticleCard } from '@/components/article/ArticleCard';
import { ArticleCardSkeleton } from '@/components/ui/Skeleton';
import { ArticleCreateModal } from '@/components/article/ArticleCreateModal';
import { useFilterMetadata } from '@/hooks/useFilterMetadata';

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

interface ArticleResponse {
  success: boolean;
  data: Array<{
    article_id: string;
    title: string;
    slug: string;
    summary?: string;
    category?: string;
    preview_image?: string;
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

export default function ArticlesPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const setIntendedDestination = useAuthStore((s) => s.setIntendedDestination);

  const { data: filterData, isLoading: filterLoading } = useFilterMetadata();

  const [page, setPage] = useState(1);
  const [allArticles, setAllArticles] = useState<ArticleResponse['data']>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [sortBy, setSortBy] = useState<SortOption>('newest');
  const [isArticleModalOpen, setIsArticleModalOpen] = useState(false);

  const categories = [
    { name: 'All', count: allArticles.length },
    ...(filterData?.data?.categories || []),
  ];

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

  let filteredArticles = allArticles;
  if (selectedCategory !== 'All') {
    filteredArticles = filteredArticles.filter(
      (a) => a.category === selectedCategory
    );
  }

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

  const totalPages = Math.ceil(sortedArticles.length / itemsPerPage);
  const startIdx = (page - 1) * itemsPerPage;
  const endIdx = startIdx + itemsPerPage;
  const currentArticles = sortedArticles.slice(startIdx, endIdx);

  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    setPage(1);
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
        className="relative min-h-screen"
        id="main-content"
      >
        {/* Hero Header with Liquid Glass */}
        <section className="section-glass pt-24">
          <motion.div
            variants={itemVariants}
            className="container-glass text-center mb-16"
          >
            <span className="text-label text-blue-400 mb-4 block uppercase">Article Library</span>
            <h1 className="text-display mb-6 text-[rgba(255,255,255,0.95)]">Latest Articles</h1>
            <p className="text-h3 font-normal mb-8 max-w-2xl mx-auto text-[rgba(255,255,255,0.65)]">
              Explore {allArticles.length} curated articles on technology and innovation
            </p>
            <button
              type="button"
              onClick={() => setIsArticleModalOpen(true)}
              className="btn-liquid primary"
              aria-label="Create a new article"
            >
              <Plus size={20} className="inline mr-2" />
              Add Article
            </button>
          </motion.div>
        </section>

        {/* Content Section */}
        <section className="section-glass pb-20">
          <div className="container-glass">
            {/* Filter & Sort Controls */}
            <motion.div
              variants={itemVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              className="mb-12"
            >
              {/* Filter Bar */}
              <div className="glass-panel p-6 mb-8">
                <div className="flex items-center gap-4 mb-6">
                  <Filter size={20} className="text-blue-400" />
                  <h3 className="text-h3 text-[rgba(255,255,255,0.95)]">Filter & Sort</h3>
                </div>

                {/* Categories */}
                <div className="mb-8">
                  <p className="text-label text-[rgba(255,255,255,0.65)] mb-4 block">Categories</p>
                  <div className="flex flex-wrap gap-2">
                    {categories.map((cat) => (
                      <motion.button
                        key={cat.name}
                        type="button"
                        onClick={() => handleCategoryChange(cat.name)}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        className={`px-4 py-2 rounded-lg font-medium transition-all ${
                          selectedCategory === cat.name
                            ? 'btn-liquid primary'
                            : 'btn-liquid secondary'
                        } ${cat.count === 0 ? 'opacity-50 cursor-not-allowed' : ''}`}
                        disabled={cat.count === 0}
                      >
                        {cat.name} ({cat.count})
                      </motion.button>
                    ))}
                  </div>
                </div>

                {/* Sort Options */}
                <div>
                  <p className="text-label text-[rgba(255,255,255,0.65)] mb-4 block">Sort By</p>
                  <div className="flex flex-wrap gap-2">
                    {(['newest', 'oldest', 'popular'] as const).map((sort) => (
                      <motion.button
                        key={sort}
                        type="button"
                        onClick={() => handleSortChange(sort)}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        className={`px-4 py-2 rounded-lg font-medium transition-all capitalize ${
                          sortBy === sort
                            ? 'btn-liquid primary'
                            : 'btn-liquid secondary'
                        }`}
                      >
                        {sort}
                      </motion.button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Results Count */}
              <p className="text-body text-[rgba(255,255,255,0.65)]">
                Showing {currentArticles.length} of {sortedArticles.length} articles
              </p>
            </motion.div>

            {/* Articles Grid */}
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
                <p className="text-red-300">{error}</p>
              </motion.div>
            ) : currentArticles.length > 0 ? (
              <motion.div
                variants={containerVariants}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, amount: 0.1 }}
                className="glass-grid mb-12"
              >
                {currentArticles.map((article) => (
                  <ArticleCard
                    key={article.article_id}
                    id={article.article_id}
                    title={article.title}
                    slug={article.slug}
                    publishedAt={article.published_at || article.created_at || ''}
                    category={article.category || undefined}
                    views={article.view_count}
                    summary={article.summary || undefined}
                  />
                ))}
              </motion.div>
            ) : (
              <motion.div
                variants={itemVariants}
                className="glass-panel p-12 text-center"
              >
                <p className="text-[rgba(255,255,255,0.65)]">No articles found. Try adjusting your filters.</p>
              </motion.div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <motion.div
                variants={itemVariants}
                className="flex items-center justify-center gap-4 mt-12"
              >
                <button
                  type="button"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="btn-liquid secondary p-2"
                  aria-label="Previous page"
                >
                  <ChevronLeft size={20} />
                </button>

                <div className="flex gap-2">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                    <motion.button
                      key={p}
                      type="button"
                      onClick={() => setPage(p)}
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.95 }}
                      className={`w-10 h-10 rounded-lg font-bold transition-all ${
                        page === p
                          ? 'btn-liquid primary'
                          : 'btn-liquid secondary'
                      }`}
                      aria-label={`Go to page ${p}`}
                      aria-current={page === p ? 'page' : undefined}
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
                >
                  <ChevronRight size={20} />
                </button>
              </motion.div>
            )}
          </div>
        </section>
      </motion.main>
    </>
  );
}
