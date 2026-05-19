'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Zap,
  Bookmark,
  Search,
  Users,
  ChevronRight,
  ArrowRight,
} from 'lucide-react';

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

export default function LandingPage() {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="min-h-screen bg-white"
    >
      {/* Navigation */}
      <motion.nav
        variants={itemVariants}
        className="sticky top-0 z-50 bg-white border-b border-slate-200 shadow-sm"
      >
        <div className="mx-auto max-w-7xl px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white font-bold">
                T
              </div>
              <span className="text-lg font-bold text-slate-900">Tech News</span>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/login"
                className="text-sm font-medium text-slate-600 transition-colors hover:text-slate-900"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="btn-primary text-sm px-4 py-2"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </motion.nav>

      {/* Hero Section */}
      <motion.section
        variants={itemVariants}
        className="px-4 py-24 md:py-32"
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
            className="text-xl text-slate-600 mb-8 max-w-2xl mx-auto"
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
              className="btn-primary justify-center gap-2"
            >
              Get Started
              <ArrowRight size={18} />
            </Link>
            <button
              onClick={() => {
                const element = document.getElementById('features');
                element?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="btn-secondary justify-center gap-2"
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
        className="px-4 py-24 bg-gradient-to-b from-white/50 to-slate-50/50 dark:from-slate-900/50 dark:to-slate-950/50"
      >
        <div className="mx-auto max-w-6xl">
          <motion.div variants={itemVariants} className="text-center mb-16">
            <h2 className="text-4xl font-bold text-slate-900 mb-4">
              Why Choose Tech News?
            </h2>
            <p className="text-xl text-slate-600 max-w-2xl mx-auto">
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
                icon: Bookmark,
                title: 'Save & Read Later',
                description: 'Build your personal library of articles for future reference',
              },
              {
                icon: Search,
                title: 'Easy Discovery',
                description: 'Advanced search and filtering to find exactly what you need',
              },
              {
                icon: Users,
                title: 'Community',
                description: 'Share and discuss articles with fellow tech enthusiasts',
              },
            ].map((feature, idx) => (
              <motion.div
                key={idx}
                variants={itemVariants}
                className="card-interactive"
              >
                <div className="mb-4 inline-flex items-center justify-center rounded-lg bg-primary-50 p-3">
                  <feature.icon size={24} className="text-primary-600" />
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

      {/* How It Works Section */}
      <motion.section
        variants={containerVariants}
        className="px-4 py-24"
      >
        <div className="mx-auto max-w-6xl">
          <motion.div variants={itemVariants} className="text-center mb-16">
            <h2 className="text-4xl font-bold text-slate-900 mb-4">
              How It Works
            </h2>
            <p className="text-xl text-slate-600 max-w-2xl mx-auto">
              Get started in three simple steps
            </p>
          </motion.div>

          <motion.div
            variants={containerVariants}
            className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-4"
          >
            {[
              {
                step: '1',
                title: 'Browse Curated News',
                description: 'Explore tech articles curated from trusted sources around the world',
              },
              {
                step: '2',
                title: 'Save Articles',
                description: 'Save your favorite articles to your personal library for reading later',
              },
              {
                step: '3',
                title: 'Get Recommendations',
                description: 'Receive personalized recommendations based on your reading history',
              },
            ].map((item, idx) => (
              <motion.div
                key={idx}
                variants={itemVariants}
                className="relative"
              >
                {/* Connecting line (hidden on mobile) */}
                {idx < 2 && (
                  <div className="hidden md:block absolute top-12 -right-4 w-8 h-1 bg-gradient-to-r from-blue-200 to-transparent" />
                )}

                <div className="flex flex-col items-center text-center">
                  <div className="mb-4 inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-600 text-white font-bold text-lg">
                    {item.step}
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-2">
                    {item.title}
                  </h3>
                  <p className="text-slate-600">{item.description}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </motion.section>

      {/* Social Proof Section */}
      <motion.section
        variants={containerVariants}
        className="px-4 py-24 bg-gradient-to-b from-white/50 to-slate-50/50 dark:from-slate-900/50 dark:to-slate-950/50"
      >
        <div className="mx-auto max-w-6xl">
          <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { stat: '50K+', label: 'Active Users' },
              { stat: '100K+', label: 'Articles Curated' },
              { stat: '98%', label: 'Satisfaction Rate' },
            ].map((item, idx) => (
              <motion.div
                key={idx}
                variants={itemVariants}
                className="text-center"
              >
                <div className="text-4xl font-bold text-blue-600 mb-2">
                  {item.stat}
                </div>
                <div className="text-lg text-slate-600">{item.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </motion.section>

      {/* CTA Section */}
      <motion.section
        variants={itemVariants}
        className="px-4 py-24"
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
            className="text-xl text-slate-600 mb-8 max-w-2xl mx-auto"
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
              className="btn-primary justify-center gap-2"
            >
              Create Your Account
              <ArrowRight size={18} />
            </Link>
            <Link
              href="/login"
              className="btn-secondary justify-center gap-2"
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
        className="px-4 py-12 bg-white/30 backdrop-blur-sm border-t border-white/20 dark:bg-slate-900/30 dark:border-slate-700/20"
      >
        <div className="mx-auto max-w-6xl">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <motion.div variants={itemVariants}>
              <div className="flex items-center gap-2 mb-4">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white font-bold text-sm">
                  T
                </div>
                <span className="font-bold text-slate-900">Tech News</span>
              </div>
              <p className="text-sm text-slate-600">
                Your source for curated tech news and insights.
              </p>
            </motion.div>

            <motion.div variants={itemVariants}>
              <h4 className="font-semibold text-slate-900 mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li>
                  <Link href="/landing" className="hover:text-slate-900">
                    Home
                  </Link>
                </li>
                <li>
                  <Link href="/search" className="hover:text-slate-900">
                    Browse
                  </Link>
                </li>
                <li>
                  <Link href="/profile" className="hover:text-slate-900">
                    Profile
                  </Link>
                </li>
              </ul>
            </motion.div>

            <motion.div variants={itemVariants}>
              <h4 className="font-semibold text-slate-900 mb-4">Company</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li>
                  <Link href="/" className="hover:text-slate-900">
                    About
                  </Link>
                </li>
                <li>
                  <Link href="/" className="hover:text-slate-900">
                    Contact
                  </Link>
                </li>
              </ul>
            </motion.div>

            <motion.div variants={itemVariants}>
              <h4 className="font-semibold text-slate-900 mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-slate-600">
                <li>
                  <Link href="/" className="hover:text-slate-900">
                    Terms of Service
                  </Link>
                </li>
                <li>
                  <Link href="/" className="hover:text-slate-900">
                    Privacy Policy
                  </Link>
                </li>
              </ul>
            </motion.div>
          </div>

          <motion.div
            variants={itemVariants}
            className="border-t border-slate-200 pt-8 text-center text-sm text-slate-600"
          >
            <p>
              &copy; {new Date().getFullYear()} Tech News. All rights reserved.
            </p>
          </motion.div>
        </div>
      </motion.footer>
    </motion.div>
  );
}
