'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, Plus, Search, Filter } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { apiClient } from '@/lib/api/client';
import { ArticleCard } from '@/components/article/ArticleCard';
import { ArticleCardSkeleton } from '@/components/ui/Skeleton';
import { ArticleCreateModal } from '@/components/article/ArticleCreateModal';
import { useFilterMetadata } from '@/hooks/useFilterMetadata';
import { AppLoadingState } from '@/components/ui/AppLoadingState';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
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
    return <AppLoadingState variant="articles" />;
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
        className="article-list-stage app-page-shell search-stage"
        id="main-content"
      >
        <div className="app-page-container">
        <section className="app-hero-panel mb-8 p-4 sm:p-5">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <motion.div variants={itemVariants} className="min-w-0">
              <h1 className="font-sans text-3xl font-bold text-black sm:text-4xl">Articles</h1>
              <p className="text-sm text-black/60">{allArticles.length} curated articles</p>
            </motion.div>
            <div className="flex min-w-0 flex-1 flex-col gap-3 lg:flex-row lg:items-center lg:justify-end">
              <div className="compact-toolbar">
                  {categories.map((cat) => (
                    <button
                      key={cat.name}
                      type="button"
                      onClick={() => handleCategoryChange(cat.name)}
                      className={`compact-chip ${selectedCategory === cat.name ? 'active' : ''} ${cat.count === 0 ? 'opacity-50 cursor-not-allowed' : ''}`}
                      disabled={cat.count === 0}
                    >
                      <span>{cat.name}</span>
                      <span className="text-xs opacity-70">({cat.count})</span>
                    </button>
                  ))}
              </div>

              <div className="segmented-glass shrink-0">
                  {(['newest', 'oldest', 'popular'] as const).map((sort) => (
                    <button
                      key={sort}
                      type="button"
                      onClick={() => handleSortChange(sort)}
                      className={`segmented-item capitalize ${sortBy === sort ? 'active' : ''}`}
                    >
                      <span>{sort}</span>
                    </button>
                  ))}
              </div>
              <motion.button
                variants={itemVariants}
                onClick={() => setIsArticleModalOpen(true)}
                className="btn-liquid primary flex shrink-0 items-center gap-2"
                aria-label="Create a new article"
              >
                <Plus size={20} />
                Add
              </motion.button>
            </div>
          </div>
        </section>

          {/* RIGHT MAIN CONTENT - Articles */}
          <motion.div
            variants={itemVariants}
            className="min-w-0"
          >

            {/* Results Info */}
            <motion.div variants={itemVariants} className="mb-6">
              <p className="text-black/60 text-sm">
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
              <motion.div variants={itemVariants} className="apple-empty-state p-6 text-center">
                <p className="text-red-700">{error}</p>
              </motion.div>
            ) : currentArticles.length > 0 ? (
              <>
                <motion.div
                  variants={containerVariants}
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true, amount: 0.05 }}
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
                          className={`h-10 w-10 rounded-2xl font-bold transition-all ${page === p ? 'bg-blue-600 text-white shadow-[0_10px_24px_rgba(0,122,255,0.24)]' : 'bg-white/70 text-black hover:bg-white'}`}
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
              </>
            ) : (
              <motion.div
                variants={itemVariants}
                className="apple-empty-state p-12 text-center"
              >
                <Search size={48} className="mx-auto mb-4 text-black/30" />
                <p className="text-black/60">No articles found. Try adjusting your filters.</p>
              </motion.div>
            )}
          </motion.div>
        </div>
      </motion.main>
    </>
  );
}
