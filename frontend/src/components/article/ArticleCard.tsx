'use client';

import Link from 'next/link';
import { format } from 'date-fns';
import { motion } from 'framer-motion';
import {
  Eye,
  Bookmark,
  Share2,
  Clock,
  TrendingUp,
  Heart,
  Edit2,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';
import { saveArticle, unsaveArticle } from '@/lib/api/user';
import { useQueryClient } from '@tanstack/react-query';

export interface ArticleCardProps {
  id: string;
  title: string;
  excerpt?: string;
  content?: string;
  slug: string;
  publishedAt: string;
  source?: string;
  category?: string;
  views?: number;
  summary?: string;
  featured?: boolean;
  trending?: boolean;
  imageUrl?: string;
  commentCount?: number;
  readingTime?: number;
  onEdit?: () => void;
  onDelete?: () => void;
}

interface BadgeProps {
  type: 'featured' | 'trending' | 'category';
  label: string;
  icon?: React.ReactNode;
}

function Badge({ type, label, icon }: BadgeProps) {
  const styles = {
    featured: 'inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 text-xs font-medium border border-amber-200',
    trending: 'inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-orange-50 text-orange-700 text-xs font-medium border border-orange-200',
    category: 'inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-primary-50 text-primary-600 text-xs font-medium border border-primary-100',
  };

  return (
    <div className={styles[type]}>
      {type === 'featured' && <span aria-hidden="true">★</span>}
      {type === 'trending' && icon}
      {label}
    </div>
  );
}

export function ArticleCard({
  id,
  slug,
  title,
  excerpt,
  content,
  publishedAt,
  source,
  category,
  views,
  summary,
  featured,
  trending,
  imageUrl,
  readingTime,
  onEdit,
  onDelete,
}: ArticleCardProps) {
  const [isBookmarked, setIsBookmarked] = useState<boolean>(false);
  const [isLiked, setIsLiked] = useState<boolean>(false);
  const [showActionMenu, setShowActionMenu] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const user = useAuthStore((state) => state.user);
  const queryClient = useQueryClient();

  const description = summary || excerpt || content?.substring(0, 150);
  const estimatedReadingTime = readingTime || Math.ceil((content?.length || 0) / 200);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      whileHover={{ y: -4 }}
      className="h-full"
    >
      <Link href={`/articles/${slug}`}>
        <article
          className={cn(
            'card-interactive group relative h-full overflow-hidden',
            featured && 'md:col-span-2 lg:col-span-2',
          )}
          aria-label={`Article: ${title}`}
        >
          {/* Image Section */}
          {imageUrl && (
            <div className="relative h-40 overflow-hidden bg-slate-200 md:h-48">
              <img
                src={imageUrl}
                alt=""
                className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105 animate-fade-in"
                loading="lazy"
              />
              {featured && <div className="absolute inset-0 bg-gradient-to-t from-slate-900/30 via-transparent to-transparent" />}
            </div>
          )}

          {/* Content Section */}
          <div className="flex flex-col h-full p-4 md:p-5">
            {/* Badges */}
            <div className="mb-3 flex flex-wrap gap-2">
              {featured && <Badge type="featured" label="Featured" />}
              {trending && <Badge type="trending" label="Trending" icon={<TrendingUp size={12} />} />}
              {category && <Badge type="category" label={category} />}
            </div>

            {/* Title */}
            <h3 className="h3 mb-2 line-clamp-3 text-gradient group-hover:text-primary-600 transition-smooth flex-grow">
              {title}
            </h3>

            {/* Description */}
            {(featured || trending) && description && (
              <p className="body-sm mb-3 line-clamp-2 text-slate-600 transition-smooth group-hover:text-primary-600">
                {description}
              </p>
            )}

            {/* Metadata */}
            <div className="mb-3 flex items-center gap-2 text-xs text-slate-500">
              {source && (
                <>
                  <span className="font-semibold text-slate-700">{source}</span>
                  <span className="text-slate-300">•</span>
                </>
              )}
              <time dateTime={publishedAt}>
                {format(new Date(publishedAt), 'MMM d, yyyy')}
              </time>
            </div>

            {/* Stats Row */}
            {(featured || trending) && (
              <div className="mb-3 flex flex-wrap gap-3 text-xs text-slate-600 md:gap-4">
                {views !== undefined && (
                  <div className="flex items-center gap-1">
                    <Eye size={14} className="text-slate-400" aria-hidden="true" />
                    <span>{views.toLocaleString()} views</span>
                  </div>
                )}
                {estimatedReadingTime > 0 && (
                  <div className="flex items-center gap-1">
                    <Clock size={14} className="text-slate-400" aria-hidden="true" />
                    <span>{estimatedReadingTime} min read</span>
                  </div>
                )}
              </div>
            )}

            {/* Action Buttons */}
            {(featured || trending) && (
              <div className="mt-auto flex items-center gap-1 border-t border-slate-100 pt-3">
                <motion.button
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.92 }}
                  onClick={(e) => {
                    e.preventDefault();
                    setIsLiked(!isLiked);
                  }}
                  aria-label={isLiked ? 'Unlike article' : 'Like article'}
                  aria-pressed={isLiked}
                  className={cn(
                    'p-2 rounded-lg transition-all duration-150 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2',
                    isLiked ? 'text-red-500' : 'text-slate-500'
                  )}
                >
                  <Heart size={16} fill={isLiked ? 'currentColor' : 'none'} aria-hidden="true" />
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.92 }}
                  onClick={async (e) => {
                    e.preventDefault();
                    if (isSaving) return;
                    setIsSaving(true);
                    try {
                      if (isBookmarked) {
                        await unsaveArticle(id);
                      } else {
                        await saveArticle(id);
                      }
                      setIsBookmarked(!isBookmarked);
                      queryClient.invalidateQueries({ queryKey: ['user', 'saves'] });
                    } catch (error) {
                      console.error('Error saving article:', error);
                    } finally {
                      setIsSaving(false);
                    }
                  }}
                  disabled={isSaving}
                  aria-label={isBookmarked ? 'Remove from saves' : 'Save article'}
                  aria-pressed={isBookmarked}
                  className={cn(
                    'p-2 rounded-lg transition-all duration-150 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:opacity-50',
                    isBookmarked ? 'text-blue-600' : 'text-slate-500'
                  )}
                >
                  <Bookmark size={16} fill={isBookmarked ? 'currentColor' : 'none'} aria-hidden="true" />
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.92 }}
                  aria-label="Share article"
                  className="p-2 rounded-lg transition-all duration-150 hover:bg-slate-100 text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
                >
                  <Share2 size={16} aria-hidden="true" />
                </motion.button>

                {/* Admin Actions */}
                {user?.is_admin && (onEdit || onDelete) && (
                  <div className="relative ml-auto">
                    <motion.button
                      type="button"
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.92 }}
                      onClick={(e) => {
                        e.preventDefault();
                        setShowActionMenu(!showActionMenu);
                      }}
                      aria-label="Article options"
                      aria-expanded={showActionMenu}
                      aria-haspopup="menu"
                      className="p-2 rounded-lg transition-all duration-150 hover:bg-slate-100 text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-600"
                    >
                      <Edit2 size={16} aria-hidden="true" />
                    </motion.button>

                    {showActionMenu && (
                      <motion.div
                        initial={{ opacity: 0, y: -4, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -4, scale: 0.95 }}
                        transition={{ duration: 0.1 }}
                        role="menu"
                        className="absolute right-0 top-full mt-2 w-40 rounded-lg border border-slate-200 bg-white shadow-lg z-10"
                      >
                        {onEdit && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              setShowActionMenu(false);
                              onEdit();
                            }}
                            className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors border-b border-slate-100 first:rounded-t-lg"
                            role="menuitem"
                          >
                            <Edit2 size={14} aria-hidden="true" />
                            Edit
                          </button>
                        )}
                        {onDelete && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              setShowActionMenu(false);
                              onDelete();
                            }}
                            className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors last:rounded-b-lg"
                            role="menuitem"
                          >
                            <Trash2 size={14} aria-hidden="true" />
                            Delete
                          </button>
                        )}
                      </motion.div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </article>
      </Link>
    </motion.div>
  );
}
