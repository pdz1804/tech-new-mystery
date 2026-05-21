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
    <header className="article-reading-header">
      {/* Category Badge */}
      {category && (
        <motion.div variants={itemVariants}>
          <span className="article-reading-category">
            {category}
          </span>
        </motion.div>
      )}

      {/* Title */}
      <motion.h1
        variants={itemVariants}
        className="article-reading-title"
      >
        {title}
      </motion.h1>

      {/* Meta Information */}
      <motion.div
        variants={itemVariants}
        className="article-reading-meta"
      >
        {publishedAt && (
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-[#007AFF]" />
            <time
              dateTime={publishedAt}
              className="text-sm text-black/62"
            >
              {format(new Date(publishedAt), 'MMMM d, yyyy')}
            </time>
          </div>
        )}
        {author && (
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-[#007AFF]" />
            <span className="text-sm text-black/62">By {author}</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <Eye className="h-4 w-4 text-[#007AFF]" />
          <span className="text-sm text-black/62">
            {views.toLocaleString()} views
          </span>
        </div>
      </motion.div>
    </header>
  );
}
