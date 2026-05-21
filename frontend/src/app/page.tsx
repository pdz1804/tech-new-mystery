'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Zap, TrendingUp, Eye, Plus, Sparkles, ArrowRight } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useFeaturedArticles, useTrendingArticles, useLatestArticles } from '@/hooks/useArticles';
import { ArticleCard } from '@/components/article/ArticleCard';
import { ArticleCardSkeleton } from '@/components/ui/Skeleton';
import { ArticleCreateModal } from '@/components/article/ArticleCreateModal';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: 'easeOut' } },
};

export default function HomePage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const featuredQuery = useFeaturedArticles(3);
  const trendingQuery = useTrendingArticles(6);
  const latestQuery = useLatestArticles(8);

  if (!isHydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center relative z-10">
        <div className="text-center">
          <div className="inline-block animate-spin">
            <div className="h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
          </div>
          <p className="mt-4 text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LandingPage />;
  }

  return (
    <motion.main
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="relative min-h-screen overflow-hidden"
      id="main-content"
    >
      {/* Hero Section with Liquid Glass */}
      <section className="hero-section pt-24">
        <motion.div
          variants={itemVariants}
          className="hero-content"
        >
          <motion.div
            variants={itemVariants}
            className="mb-6 inline-block"
          >
            <span className="text-label text-blue-400 uppercase tracking-widest">AI-Powered Tech News</span>
          </motion.div>

          <h1 className="text-display mb-6 max-w-4xl mx-auto">
            Stay Informed with Curated Tech News
          </h1>

          <p className="text-h3 font-normal mb-8 max-w-2xl mx-auto text-[rgba(255,255,255,0.65)]">
            Discover the latest trends in technology, AI, and innovation. Curated just for you with breaking news, in-depth analysis, and expert insights.
          </p>

          {/* CTA Buttons */}
          <motion.div
            variants={itemVariants}
            className="hero-cta-group"
          >
            <button
              type="button"
              onClick={() => setShowCreateModal(true)}
              className="btn-liquid primary"
            >
              <Plus size={20} className="inline mr-2" />
              Add Article
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = '/articles'; }}
              className="btn-liquid secondary"
            >
              Browse Articles
              <ArrowRight size={18} className="inline ml-2" />
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = '/profile?tab=saved'; }}
              className="btn-liquid tertiary"
            >
              View Saved
            </button>
          </motion.div>
        </motion.div>
      </section>

      {/* Feature Cards - Stats Section */}
      <section className="section-glass">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }}
          className="glass-grid max-w-1200 mx-auto px-4"
        >
          {[
            { icon: Zap, label: 'Real-time Updates', value: 'Always Fresh', color: 'from-blue-500 to-cyan-400' },
            { icon: TrendingUp, label: 'Trending Topics', value: 'Multi-source', color: 'from-purple-500 to-magenta-400' },
            { icon: Eye, label: 'Community Views', value: '1.2K+', color: 'from-pink-500 to-rose-400' },
          ].map((stat, idx) => (
            <motion.div
              key={idx}
              variants={itemVariants}
              whileHover={{ y: -8 }}
              className="feature-card"
            >
              <div className={`feature-card-icon bg-gradient-to-br ${stat.color}`}>
                <stat.icon size={24} className="text-white" />
              </div>
              <h3 className="text-label mb-3">{stat.label}</h3>
              <p className="text-h2 font-bold text-white">{stat.value}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Featured Articles */}
      <section className="section-glass">
        <div className="container-glass">
          <motion.div
            variants={itemVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="mb-16"
          >
            <span className="text-label text-blue-400 mb-4 block">Curated Collection</span>
            <h2 className="text-h2 mb-4 text-[rgba(255,255,255,0.95)]">Featured Articles</h2>
            <p className="text-body text-[rgba(255,255,255,0.65)]">Handpicked stories you shouldn&apos;t miss</p>
          </motion.div>

          {featuredQuery.isLoading ? (
            <div className="glass-grid">
              {[...Array(3)].map((_, i) => (
                <ArticleCardSkeleton key={i} />
              ))}
            </div>
          ) : featuredQuery.error ? (
            <motion.div
              variants={itemVariants}
              className="glass-panel p-6 border-red-500/50"
            >
              <p className="text-red-300">Failed to load featured articles</p>
            </motion.div>
          ) : featuredQuery.data?.data && featuredQuery.data.data.length > 0 ? (
            <motion.div
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.1 }}
              className="glass-grid"
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
              className="glass-panel p-12 text-center"
            >
              <p className="text-slate-400">No featured articles available</p>
            </motion.div>
          )}
        </div>
      </section>

      {/* Trending Section */}
      <section className="section-glass">
        <div className="container-glass">
          <motion.div
            variants={itemVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="mb-16"
          >
            <span className="text-label text-purple-400 mb-4 block">Hot Right Now</span>
            <h2 className="text-h2 mb-4 text-[rgba(255,255,255,0.95)]">Trending Now</h2>
            <p className="text-body text-[rgba(255,255,255,0.65)]">What everyone is reading today</p>
          </motion.div>

          {trendingQuery.isLoading ? (
            <div className="glass-grid">
              {[...Array(6)].map((_, i) => (
                <ArticleCardSkeleton key={i} />
              ))}
            </div>
          ) : trendingQuery.error ? (
            <motion.div
              variants={itemVariants}
              className="glass-panel p-6 border-red-500/50"
            >
              <p className="text-red-300">Failed to load trending articles</p>
            </motion.div>
          ) : trendingQuery.data?.data && trendingQuery.data.data.length > 0 ? (
            <motion.div
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.1 }}
              className="glass-grid"
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
              className="glass-panel p-12 text-center"
            >
              <p className="text-slate-400">No trending articles available</p>
            </motion.div>
          )}
        </div>
      </section>

      {/* Latest Articles */}
      <section className="section-glass pb-20">
        <div className="container-glass">
          <motion.div
            variants={itemVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="mb-16"
          >
            <span className="text-label text-cyan-400 mb-4 block">Latest Drops</span>
            <h2 className="text-h2 mb-4 text-[rgba(255,255,255,0.95)]">Latest Articles</h2>
            <p className="text-body text-[rgba(255,255,255,0.65)]">Fresh updates from around the tech world</p>
          </motion.div>

          {latestQuery.isLoading ? (
            <div className="glass-grid">
              {[...Array(8)].map((_, i) => (
                <ArticleCardSkeleton key={i} />
              ))}
            </div>
          ) : latestQuery.error ? (
            <motion.div
              variants={itemVariants}
              className="glass-panel p-6 border-red-500/50"
            >
              <p className="text-red-300">Failed to load latest articles</p>
            </motion.div>
          ) : latestQuery.data?.data && latestQuery.data.data.length > 0 ? (
            <motion.div
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.1 }}
              className="glass-grid"
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
              className="glass-panel p-12 text-center"
            >
              <p className="text-slate-400">No latest articles available</p>
            </motion.div>
          )}
        </div>
      </section>

      {showCreateModal && <ArticleCreateModal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} />}
    </motion.main>
  );
}

function LandingPage() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.8 }}
      className="relative min-h-screen flex flex-col items-center justify-center"
    >
      <div className="hero-section">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="hero-content"
        >
          <div className="mb-8 flex items-center justify-center gap-2">
            <Sparkles className="text-blue-400" size={32} />
            <span className="text-label text-blue-400">WELCOME TO TECH NEWS</span>
          </div>

          <h1 className="text-display mb-8">
            Your AI-Powered Tech News Hub
          </h1>

          <p className="text-h3 font-normal mb-12 max-w-2xl mx-auto text-[rgba(255,255,255,0.65)] leading-relaxed">
            Discover curated technology news with AI-powered summaries. Stay ahead of the curve with breaking stories, trend analysis, and expert insights.
          </p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="hero-cta-group"
          >
            <button
              type="button"
              onClick={() => { window.location.href = '/login'; }}
              className="btn-liquid primary"
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = '/register'; }}
              className="btn-liquid secondary"
            >
              Create Account
            </button>
          </motion.div>
        </motion.div>

        {/* Stats Grid for Landing */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="glass-grid max-w-4xl mx-auto px-4 mt-20"
        >
          {[
            { icon: Zap, label: 'Real-time Updates', value: 'Always Fresh' },
            { icon: Eye, label: 'Community Powered', value: 'By Thousands' },
            { icon: TrendingUp, label: 'Multi-Source', value: 'Best Coverage' },
          ].map((stat, idx) => (
            <motion.div
              key={idx}
              whileHover={{ y: -8 }}
              className="feature-card"
            >
              <div className="feature-card-icon bg-gradient-to-br from-blue-500 to-cyan-400">
                <stat.icon size={24} className="text-white" />
              </div>
              <h3 className="text-label mb-2">{stat.label}</h3>
              <p className="text-xl font-bold text-white">{stat.value}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </motion.div>
  );
}
