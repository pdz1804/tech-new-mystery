'use client';

import Link from 'next/link';
import { format } from 'date-fns';
import { motion } from 'framer-motion';
import {
  Eye,
  Bookmark,
  Share2,
  Heart,
  Clock,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';

export interface SavedArticleCardProps {
  id: string;
  title: string;
  slug: string;
  publishedAt: string;
  category?: string;
  views?: number;
  summary?: string;
  featured?: boolean;
  trending?: boolean;
  readingTime?: number;
}

export function SavedArticleCard({
  slug,
  title,
  publishedAt,
  category,
  views,
  summary,
  featured,
  trending,
  readingTime,
}: SavedArticleCardProps) {
  const [isBookmarked, setIsBookmarked] = useState<boolean>(true);
  const [isLiked, setIsLiked] = useState<boolean>(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      whileHover={{ y: -4 }}
      className="h-full"
    >
      <Link href={`/articles/${slug}`}>
        <article
          className={cn(
            'group relative h-full overflow-hidden rounded-xl border transition-all duration-300 bg-white',
            featured
              ? 'border-blue-200 border-t-4 border-t-blue-600 shadow-sm hover:shadow-lg'
              : 'border-slate-200 shadow-sm hover:shadow-lg'
          )}
        >
          {/* Badge Section */}
          <div className="relative p-5">
            <div className="mb-3 flex flex-wrap gap-2">
              {featured && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-600"
                >
                  ⭐ Featured
                </motion.div>
              )}
              {trending && (
                <div className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-600">
                  <TrendingUp size={12} />
                  Trending
                </div>
              )}
              {category && (
                <div className="inline-block rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                  {category}
                </div>
              )}
            </div>

            {/* Title */}
            <h3 className="mb-2 line-clamp-2 text-base font-bold text-slate-900 transition-colors group-hover:text-blue-600">
              {title}
            </h3>

            {/* Description */}
            {summary && (
              <p className="mb-3 line-clamp-2 text-sm text-slate-600">{summary}</p>
            )}

            {/* Meta Information */}
            <div className="mb-4 flex items-center gap-3 text-xs text-slate-500">
              <span>{format(new Date(publishedAt), 'MMM d, yyyy')}</span>
              {views !== undefined && (
                <>
                  <span>•</span>
                  <div className="flex items-center gap-1">
                    <Eye size={12} />
                    <span>{views.toLocaleString()}</span>
                  </div>
                </>
              )}
              {readingTime && readingTime > 0 && (
                <>
                  <span>•</span>
                  <div className="flex items-center gap-1">
                    <Clock size={12} />
                    <span>{readingTime} min</span>
                  </div>
                </>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2 border-t border-slate-100 pt-3 text-slate-400">
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={(e) => {
                  e.preventDefault();
                  setIsLiked(!isLiked);
                }}
                className={cn(
                  'rounded-lg p-2 transition-colors hover:bg-slate-50',
                  isLiked && 'text-red-600'
                )}
              >
                <Heart size={14} fill={isLiked ? 'currentColor' : 'none'} />
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={(e) => {
                  e.preventDefault();
                  setIsBookmarked(!isBookmarked);
                }}
                className={cn(
                  'rounded-lg p-2 transition-colors hover:bg-slate-50',
                  isBookmarked && 'text-blue-600'
                )}
              >
                <Bookmark size={14} fill={isBookmarked ? 'currentColor' : 'none'} />
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                className="rounded-lg p-2 transition-colors hover:bg-slate-50"
              >
                <Share2 size={14} />
              </motion.button>
            </div>
          </div>
        </article>
      </Link>
    </motion.div>
  );
}
