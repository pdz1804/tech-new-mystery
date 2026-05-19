'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Zap, TrendingUp, Eye, Plus, ArrowRight, ChevronRight } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useFeaturedArticles, useTrendingArticles, useLatestArticles } from '@/hooks/useArticles';
import { ArticleCard } from '@/components/article/ArticleCard';
import { ArticleCardSkeleton } from '@/components/ui/Skeleton';
import { ArticleCreateModal } from '@/components/article/ArticleCreateModal';
import Link from 'next/link';

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

export default function HomePage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const featuredQuery = useFeaturedArticles(3);
  const trendingQuery = useTrendingArticles(6);
  const latestQuery = useLatestArticles(8);

  // Show landing page if not hydrated yet (loading state)
  if (!isHydrated) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin">
            <div className="h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full"></div>
          </div>
          <p className="mt-4 text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Show landing page for unauthenticated users
  if (!isAuthenticated) {
    return <LandingPage />;
  }

  return (
    <motion.main
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="min-h-screen bg-white"
      id="main-content"
    >
      {/* Hero Section */}
      <motion.section
        variants={itemVariants}
        className="relative overflow-hidden bg-gradient-to-br from-white via-slate-50 to-white border-b border-slate-200 px-4 py-20 md:py-28"
      >
        <div className="mx-auto max-w-5xl">
          <motion.div variants={itemVariants} className="space-y-6">
            <div className="space-y-3">
              <motion.div
                variants={itemVariants}
                className="inline-block"
              >
                <span className="text-sm font-semibold text-blue-600 uppercase tracking-wide">Welcome back</span>
              </motion.div>
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-slate-900">
                Stay informed with curated tech news
              </h1>
            </div>
            <motion.p
              variants={itemVariants}
              className="max-w-2xl text-lg text-slate-700 leading-relaxed"
            >
              Discover the latest trends in technology, curated just for you. Get breaking news, in-depth analysis, and expert insights.
            </motion.p>
            <motion.div
              variants={itemVariants}
              className="flex flex-wrap gap-3 pt-6"
            >
              <motion.button
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-all duration-200 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
                aria-label="Add a new article"
              >
                <Plus size={18} aria-hidden="true" />
                Add Article
              </motion.button>
              <motion.a
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
                href="/articles"
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-6 py-3 font-semibold text-slate-900 transition-all duration-200 hover:bg-slate-50 hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
              >
                Browse All Articles
              </motion.a>
              <motion.a
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
                href="/profile?tab=saved"
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-6 py-3 font-semibold text-slate-900 transition-all duration-200 hover:bg-slate-50 hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
              >
                View Saved
              </motion.a>
            </motion.div>
          </motion.div>
        </div>
      </motion.section>

      {/* Stats Section */}
      <motion.section
        variants={itemVariants}
        className="border-b border-slate-200 bg-slate-50 px-4 py-16"
      >
        <div className="mx-auto max-w-5xl">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { icon: Zap, label: 'Real-time Updates', value: 'Always Fresh' },
              { icon: TrendingUp, label: 'Trending Topics', value: 'Multi-source' },
              { icon: Eye, label: 'Community Views', value: '1.2K+' },
            ].map((stat, idx) => (
              <motion.div
                key={idx}
                variants={itemVariants}
                className="card-base p-5 md:p-6"
                whileHover={{ y: -4 }}
              >
                <div className="mb-4 inline-flex items-center justify-center h-12 w-12 rounded-lg bg-blue-100 text-blue-600">
                  <stat.icon size={24} aria-hidden="true" />
                </div>
                <p className="text-sm font-medium text-slate-600 mb-2">{stat.label}</p>
                <p className="text-2xl md:text-3xl font-bold text-slate-900">{stat.value}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.section>

      <div className="mx-auto max-w-5xl px-4">
        {/* Featured Articles Section */}
        <motion.section variants={itemVariants} className="mb-20">
          <motion.div variants={itemVariants} className="mb-10">
            <div className="space-y-2">
              <h2 className="text-3xl md:text-4xl font-bold text-slate-900">Featured Articles</h2>
              <p className="text-base text-slate-600">Handpicked stories you shouldn&apos;t miss</p>
            </div>
          </motion.div>

          {featuredQuery.isLoading ? (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {[...Array(3)].map((_, i) => (
                <ArticleCardSkeleton key={i} />
              ))}
            </div>
          ) : featuredQuery.error ? (
            <motion.div
              variants={itemVariants}
              className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700"
            >
              Failed to load featured articles
            </motion.div>
          ) : featuredQuery.data?.data && featuredQuery.data.data.length > 0 ? (
            <motion.div
              variants={containerVariants}
              className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3"
            >
              {featuredQuery.data.data.map((article) => (
                <ArticleCard
                  key={article.article_id}
                  id={article.article_id}
                  title={article.title}
                  slug={article.slug}
                  publishedAt={article.published_at || article.created_at}
                  category={article.category || undefined}
                  views={article.view_count}
                  summary={article.summary || undefined}
                  featured
                />
              ))}
            </motion.div>
          ) : (
            <motion.div
              variants={itemVariants}
              className="text-center text-slate-500 py-12"
            >
              No featured articles available
            </motion.div>
          )}
        </motion.section>

        {/* Trending Articles Section */}
        <motion.section variants={itemVariants} className="mb-20">
          <motion.div variants={itemVariants} className="mb-10">
            <div className="space-y-2">
              <h2 className="text-3xl md:text-4xl font-bold text-slate-900">Trending Now</h2>
              <p className="text-base text-slate-600">What everyone is reading today</p>
            </div>
          </motion.div>

          {trendingQuery.isLoading ? (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {[...Array(6)].map((_, i) => (
                <ArticleCardSkeleton key={i} />
              ))}
            </div>
          ) : trendingQuery.error ? (
            <motion.div
              variants={itemVariants}
              className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700"
            >
              Failed to load trending articles
            </motion.div>
          ) : trendingQuery.data?.data && trendingQuery.data.data.length > 0 ? (
            <motion.div
              variants={containerVariants}
              className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3"
            >
              {trendingQuery.data.data.map((article) => (
                <ArticleCard
                  key={article.article_id}
                  id={article.article_id}
                  title={article.title}
                  slug={article.slug}
                  publishedAt={article.published_at || article.created_at}
                  category={article.category || undefined}
                  views={article.view_count}
                  summary={article.summary || undefined}
                  trending
                />
              ))}
            </motion.div>
          ) : (
            <motion.div
              variants={itemVariants}
              className="text-center text-slate-500 py-12"
            >
              No trending articles available
            </motion.div>
          )}
        </motion.section>

        {/* Latest Articles Section */}
        <motion.section variants={itemVariants} className="mb-20">
          <motion.div variants={itemVariants} className="mb-10">
            <div className="space-y-2">
              <h2 className="text-3xl md:text-4xl font-bold text-slate-900">Latest News</h2>
              <p className="text-base text-slate-600">Fresh content added every hour</p>
            </div>
          </motion.div>

          {latestQuery.isLoading ? (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
              {[...Array(8)].map((_, i) => (
                <ArticleCardSkeleton key={i} />
              ))}
            </div>
          ) : latestQuery.error ? (
            <motion.div
              variants={itemVariants}
              className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700"
            >
              Failed to load latest articles
            </motion.div>
          ) : latestQuery.data?.data && latestQuery.data.data.length > 0 ? (
            <motion.div
              variants={containerVariants}
              className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4"
            >
              {latestQuery.data.data.map((article) => (
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
          ) : (
            <motion.div
              variants={itemVariants}
              className="text-center text-slate-500 py-12"
            >
              No latest articles available
            </motion.div>
          )}
        </motion.section>
      </div>

      {/* Footer CTA Section */}
      <motion.section
        variants={itemVariants}
        className="px-4 py-16 md:py-20 bg-slate-50 border-t border-slate-200"
      >
        <motion.div
          variants={itemVariants}
          className="mx-auto max-w-3xl card-base p-8 md:p-12 text-center"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-3">Stay in the Loop</h2>
          <p className="text-base md:text-lg text-slate-700 max-w-2xl mx-auto mb-8">
            Get personalized news recommendations and never miss important updates from the tech world.
          </p>
          <motion.button
            whileHover={{ scale: 1.02, y: -2 }}
            whileTap={{ scale: 0.98 }}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-8 py-3 font-semibold text-white transition-all duration-200 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
          >
            Subscribe Now
          </motion.button>
        </motion.div>
      </motion.section>

      {/* Article Create Modal */}
      <ArticleCreateModal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} />
    </motion.main>
  );
}

function LandingPage() {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="min-h-screen bg-white"
    >
      {/* Hero Section */}
      <motion.section
        variants={itemVariants}
        className="px-4 py-24 md:py-32 bg-gradient-to-br from-blue-50 via-white to-indigo-50"
      >
        <div className="mx-auto max-w-4xl text-center">
          <motion.h1
            variants={itemVariants}
            className="text-5xl md:text-6xl font-bold text-slate-900 mb-6"
          >
            Discover Tech News That Matters
          </motion.h1>
          <motion.p
            variants={itemVariants}
            className="text-xl text-slate-700 mb-8 max-w-2xl mx-auto"
          >
            Stay updated with AI-curated tech articles from trusted sources.
            Get personalized recommendations tailored to your interests.
          </motion.p>
          <motion.div
            variants={itemVariants}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <Link
              href="/register"
              className="btn-primary justify-center gap-2 inline-flex"
            >
              Get Started
              <ArrowRight size={18} />
            </Link>
            <button
              type="button"
              onClick={() => {
                const element = document.getElementById('features');
                element?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="btn-secondary justify-center gap-2 inline-flex"
            >
              Learn More
              <ChevronRight size={18} />
            </button>
          </motion.div>
        </div>
      </motion.section>

      {/* Features Section */}
      <motion.section
        id="features"
        variants={containerVariants}
        className="px-4 py-24 bg-gradient-to-b from-slate-50 to-white"
      >
        <div className="mx-auto max-w-6xl">
          <motion.div variants={itemVariants} className="text-center mb-16">
            <h2 className="text-4xl font-bold text-slate-900 mb-4">
              Why Choose Tech News?
            </h2>
            <p className="text-xl text-slate-700 max-w-2xl mx-auto">
              Everything you need to stay informed about the technology industry
            </p>
          </motion.div>

          <motion.div
            variants={containerVariants}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
          >
            {[
              {
                icon: Zap,
                title: 'Smart Curation',
                description: 'AI-powered article recommendations tailored to your interests',
              },
              {
                icon: TrendingUp,
                title: 'Save & Read Later',
                description: 'Build your personal library of articles for future reference',
              },
              {
                icon: Eye,
                title: 'Easy Discovery',
                description: 'Advanced search and filtering to find exactly what you need',
              },
              {
                icon: Plus,
                title: 'Community',
                description: 'Share and discuss articles with fellow tech enthusiasts',
              },
            ].map((feature, idx) => (
              <motion.div
                key={idx}
                variants={itemVariants}
                className="card-interactive p-6"
              >
                <div className="mb-4 inline-flex items-center justify-center rounded-lg bg-blue-50 p-3">
                  <feature.icon size={24} className="text-blue-600" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-slate-600">{feature.description}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </motion.section>

      {/* CTA Section */}
      <motion.section
        variants={itemVariants}
        className="px-4 py-24 bg-white"
      >
        <div className="mx-auto max-w-4xl text-center">
          <motion.h2
            variants={itemVariants}
            className="text-4xl font-bold text-slate-900 mb-6"
          >
            Ready to Stay Updated?
          </motion.h2>
          <motion.p
            variants={itemVariants}
            className="text-xl text-slate-700 mb-8 max-w-2xl mx-auto"
          >
            Join thousands of tech professionals who trust Tech News for their
            daily technology updates.
          </motion.p>
          <motion.div
            variants={itemVariants}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <Link
              href="/register"
              className="btn-primary justify-center gap-2 inline-flex"
            >
              Create Your Account
              <ArrowRight size={18} />
            </Link>
            <Link
              href="/login"
              className="btn-secondary justify-center gap-2 inline-flex"
            >
              Sign In
              <ChevronRight size={18} />
            </Link>
          </motion.div>
        </div>
      </motion.section>

      {/* Footer */}
      <motion.footer
        variants={itemVariants}
        className="px-4 py-12 bg-slate-50 border-t border-slate-200"
      >
        <div className="mx-auto max-w-6xl text-center text-sm text-slate-600">
          <p>
            &copy; {new Date().getFullYear()} Tech News. All rights reserved.
          </p>
        </div>
      </motion.footer>
    </motion.div>
  );
}
