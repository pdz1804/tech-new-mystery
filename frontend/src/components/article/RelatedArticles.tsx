'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { format } from 'date-fns';

interface Article {
  article_id: string;
  title: string;
  slug: string;
  summary?: string;
  published_at?: string;
  created_at: string;
  category?: string;
  view_count: number;
}

interface RelatedArticlesProps {
  articles: Article[];
  title?: string;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export function RelatedArticles({
  articles,
  title = 'Related Articles',
}: RelatedArticlesProps) {
  if (!articles || articles.length === 0) {
    return null;
  }

  return (
    <motion.section
      variants={containerVariants}
      className="mt-16 pt-12 border-t border-slate-200"
    >
      <motion.h2
        variants={itemVariants}
        className="mb-8 text-2xl font-bold text-slate-900"
      >
        {title}
      </motion.h2>

      <motion.div
        variants={containerVariants}
        className="grid gap-6 md:grid-cols-2 lg:grid-cols-3"
      >
        {articles.map((article) => (
          <Link key={article.article_id} href={`/articles/${article.slug}`}>
            <motion.article
              variants={itemVariants}
              whileHover={{ y: -4 }}
              className="group h-full rounded-xl border border-slate-200 bg-white p-6 transition-all hover:shadow-lg"
            >
              {/* Category Badge */}
              {article.category && (
                <div className="mb-3 inline-block rounded-full bg-blue-600/10 px-3 py-1.5 text-xs font-semibold text-blue-600 border border-indigo-500/20">
                  {article.category}
                </div>
              )}

              {/* Title */}
              <h3 className="mb-3 line-clamp-3 text-lg font-bold text-slate-900 transition-colors group-hover:text-blue-600">
                {article.title}
              </h3>

              {/* Summary */}
              {article.summary && (
                <p className="mb-4 line-clamp-2 text-sm text-slate-600">
                  {article.summary}
                </p>
              )}

              {/* Meta */}
              <div className="text-xs text-slate-500">
                {format(
                  new Date(article.published_at || article.created_at),
                  'MMM d, yyyy'
                )} • {article.view_count.toLocaleString()} views
              </div>
            </motion.article>
          </Link>
        ))}
      </motion.div>
    </motion.section>
  );
}
