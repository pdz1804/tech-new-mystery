'use client';

import { motion } from 'framer-motion';
import { Calendar, User, Eye } from 'lucide-react';
import { format } from 'date-fns';

interface ArticleHeaderProps {
  category?: string;
  title: string;
  publishedAt: string;
  author?: string;
  views: number;
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export function ArticleHeader({
  category,
  title,
  publishedAt,
  author,
  views,
}: ArticleHeaderProps) {
  return (
    <header className="mb-12">
      {/* Category Badge */}
      {category && (
        <motion.div variants={itemVariants}>
          <span className="inline-block rounded-full px-3 py-1.5 text-sm font-semibold mb-4 border border-indigo-500/20 bg-blue-600/10 text-blue-600">
            {category}
          </span>
        </motion.div>
      )}

      {/* Title */}
      <motion.h1
        variants={itemVariants}
        className="mb-6 text-5xl font-bold text-slate-900 leading-tight"
      >
        {title}
      </motion.h1>

      {/* Meta Information */}
      <motion.div
        variants={itemVariants}
        className="flex flex-wrap gap-6 border-b border-slate-200 pb-6"
      >
        {publishedAt && (
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-blue-600" />
            <time
              dateTime={publishedAt}
              className="text-sm text-slate-600"
            >
              {format(new Date(publishedAt), 'MMMM d, yyyy')}
            </time>
          </div>
        )}
        {author && (
          <div className="flex items-center gap-2">
            <User className="h-5 w-5 text-blue-600" />
            <span className="text-sm text-slate-600">By {author}</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <Eye className="h-5 w-5 text-blue-600" />
          <span className="text-sm text-slate-600">
            {views.toLocaleString()} views
          </span>
        </div>
      </motion.div>
    </header>
  );
}
