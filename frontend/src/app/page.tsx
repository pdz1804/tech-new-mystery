'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Zap, TrendingUp, Eye, Plus, Sparkles, ArrowRight } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useFeaturedArticles, useTrendingArticles, useLatestArticles } from '@/hooks/useArticles';
import { ArticleCard } from '@/components/article/ArticleCard';
import { ArticleCardSkeleton } from '@/components/ui/Skeleton';
import { ArticleCreateModal } from '@/components/article/ArticleCreateModal';
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
    return <AppLoadingState />;
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
      {/* Hero Section with Background Image */}
      <section className="relative flex min-h-[700px] flex-col items-center justify-center overflow-hidden px-4 pb-12 pt-48">

        {/* Background Image with Overlay */}
        <div className="absolute inset-0 z-0">
          <picture>
            <source media="(max-width: 768px)" srcSet="/img/background-mobile.jpg" />
            <source media="(min-width: 769px)" srcSet="/img/background-web.jpg" />
            <img
              src="/img/background-web.jpg"
              alt="Tech background"
              className="w-full h-full object-cover"
            />
          </picture>
          <div className="hero-photo-shade" />
        </div>

        {/* Content */}
        <motion.div
          initial="hidden"
          animate="visible"
          variants={containerVariants}
          className="hero-glass-lens relative z-10 mx-auto max-w-5xl px-5 py-10 text-center sm:px-10 lg:px-14"
        >
          <motion.div
            variants={itemVariants}
            className="mb-6 inline-block"
          >
            <span className="text-label hero-readable text-white/80 uppercase">AI-Powered Tech News</span>
          </motion.div>

          <motion.h1
            variants={itemVariants}
            className="hero-readable mx-auto mb-6 max-w-4xl font-sans text-5xl font-bold sm:text-6xl lg:text-7xl"
          >
            Stay Informed with Curated Tech News
          </motion.h1>

          <motion.p
            variants={itemVariants}
            className="hero-readable mx-auto mb-10 max-w-3xl text-lg leading-relaxed text-white/90 sm:text-xl lg:text-2xl"
          >
            Discover the latest trends in technology, AI, and innovation. Curated just for you with breaking news, in-depth analysis, and expert insights.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            variants={itemVariants}
            className="flex flex-wrap justify-center gap-4"
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
              className="bg-white/14 hover:bg-white/22 inline-flex items-center rounded-2xl border border-white/25 border-t-white/50 px-8 py-4 font-semibold text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.35)] backdrop-blur-md transition-all duration-300 hover:-translate-y-0.5"
            >
              Browse Articles
              <ArrowRight size={18} className="inline ml-2" />
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = '/profile?tab=saved'; }}
              className="bg-white/10 hover:bg-white/18 inline-flex items-center rounded-2xl border border-white/20 border-t-white/45 px-8 py-4 font-semibold text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.3)] backdrop-blur-md transition-all duration-300 hover:-translate-y-0.5"
            >
              View Saved
            </button>
          </motion.div>
        </motion.div>
      </section>

      {/* Feature Cards - Light Mode Glass */}
      <section className="relative py-14">
        <div className="mx-auto w-full max-w-[1280px] px-4">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.3 }}
            className="grid grid-cols-1 gap-5 md:grid-cols-3"
          >
            {[
              {
                icon: Zap,
                label: 'Real-time Updates',
                value: 'Always Fresh',
                color: 'from-blue-600 to-cyan-600'
              },
              {
                icon: TrendingUp,
                label: 'Trending Topics',
                value: 'Multi-source',
                color: 'from-purple-600 to-pink-600'
              },
              {
                icon: Eye,
                label: 'Community Views',
                value: '1.2K+',
                color: 'from-orange-600 to-red-600'
              },
            ].map((stat, idx) => (
              <motion.div
                key={idx}
                variants={itemVariants}
                whileHover={{ y: -8 }}
                transition={{ type: 'spring', stiffness: 320, damping: 22 }}
                className="feature-glass-card group min-h-[168px]"
              >
                {/* Content */}
                <div className="relative z-10 flex h-full items-center gap-5 p-6 md:block md:p-7">
                  <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br ${stat.color} mb-0 shadow-[0_14px_28px_rgba(0,0,0,0.16)] md:mb-6`}>
                    <stat.icon size={28} className="text-white" />
                  </div>

                  <div>
                  <h3 className="mb-2 text-sm font-bold uppercase text-black/60">
                    {stat.label}
                  </h3>

                  <p className="text-3xl font-bold text-black transition-colors sm:text-4xl">
                    {stat.value}
                  </p>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
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
            <span className="text-label text-blue-600 mb-4 block">Curated Collection</span>
            <h2 className="text-h2 mb-4 text-black">Featured Articles</h2>
            <p className="text-body text-black/60">Handpicked stories you shouldn&apos;t miss</p>
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
              <p className="text-red-600">Failed to load featured articles</p>
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
              <p className="text-slate-500">No featured articles available</p>
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
            <span className="text-label text-purple-600 mb-4 block">Hot Right Now</span>
            <h2 className="text-h2 mb-4 text-black">Trending Now</h2>
            <p className="text-body text-black/60">What everyone is reading today</p>
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
              <p className="text-red-600">Failed to load trending articles</p>
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
              <p className="text-slate-500">No trending articles available</p>
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
            <span className="text-label text-green-600 mb-4 block">Latest Drops</span>
            <h2 className="text-h2 mb-4 text-black">Latest Articles</h2>
            <p className="text-body text-black/60">Fresh updates from around the tech world</p>
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
              <p className="text-red-600">Failed to load latest articles</p>
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
              <p className="text-slate-500">No latest articles available</p>
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
      className="relative min-h-screen"
    >
      <section className="landing-photo-shell">
        <picture>
          <source media="(max-width: 768px)" srcSet="/img/background-mobile-02.jpg" />
          <source media="(min-width: 769px)" srcSet="/img/background-web-02.jpg" />
          <img src="/img/background-web-02.jpg" alt="Tech workspace background" />
        </picture>

        <div className="landing-content-frame">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="hero-glass-lens landing-copy-lens"
          >
            <div className="mb-6 flex items-center justify-center gap-2">
              <Sparkles className="text-blue-300" size={28} />
              <span className="text-label hero-readable text-white/80">WELCOME TO TECH NEWS</span>
            </div>

            <h1 className="hero-readable mx-auto mb-5 max-w-4xl text-5xl font-bold sm:text-6xl lg:text-7xl">
              Your AI-Powered Tech News Hub
            </h1>

            <p className="hero-readable mx-auto mb-8 max-w-2xl text-lg leading-relaxed text-white/90 sm:text-xl">
              Discover curated technology news with AI-powered summaries. Stay ahead of the curve with breaking stories, trend analysis, and expert insights.
            </p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="flex flex-wrap justify-center gap-4"
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
                className="bg-white/12 hover:bg-white/20 rounded-2xl border border-white/25 border-t-white/50 px-7 py-3.5 font-semibold text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.35)] backdrop-blur-md transition-all duration-300 hover:-translate-y-0.5"
              >
                Create Account
              </button>
            </motion.div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.45 }}
            className="landing-card-grid"
          >
            {[
              { icon: Zap, label: 'Real-time Updates', value: 'Always Fresh' },
              { icon: Eye, label: 'Community Powered', value: 'By Thousands' },
              { icon: TrendingUp, label: 'Multi-Source', value: 'Best Coverage' },
            ].map((stat, idx) => (
            <motion.div
              key={idx}
              whileHover={{ y: -7 }}
              transition={{ type: 'spring', stiffness: 320, damping: 22 }}
              className="landing-stat-card"
            >
              <div className="relative z-10 flex h-full flex-col items-center justify-center text-center">
                <div className="landing-stat-icon mb-3">
                  <stat.icon size={22} />
                </div>
                <h3 className="text-label mb-2 text-black/70">{stat.label}</h3>
                <p className="m-0 text-base font-bold text-black">{stat.value}</p>
              </div>
            </motion.div>
            ))}
          </motion.div>
        </div>
      </section>
    </motion.div>
  );
}
