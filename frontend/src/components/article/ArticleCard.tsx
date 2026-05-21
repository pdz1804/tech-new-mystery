'use client';

import Link from 'next/link';
import { format } from 'date-fns';
import { motion } from 'framer-motion';
import {
  ArrowUpRight,
  Bookmark,
  Calendar,
  Edit2,
  Eye,
  Heart,
  Share2,
  Trash2,
  TrendingUp,
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
  return (
    <span className={`article-card-badge ${type}`}>
      {type === 'trending' && icon}
      {label}
    </span>
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
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [isLiked, setIsLiked] = useState(false);
  const [showActionMenu, setShowActionMenu] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const user = useAuthStore((state) => state.user);
  const queryClient = useQueryClient();

  const description = summary || excerpt || content?.substring(0, 180);
  const estimatedReadingTime = readingTime || Math.max(1, Math.ceil((content?.length || description?.length || 200) / 900));
  const formattedDate = publishedAt ? format(new Date(publishedAt), 'MMM d, yyyy') : 'Recently';

  return (
    <motion.article
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: 'easeOut' }}
      whileHover={{ y: -6 }}
      className="h-full"
      aria-label={`Article: ${title}`}
    >
      <Link href={`/articles/${slug}`} className="block h-full">
        <div
          className={cn(
            'article-glass-card group',
            featured && 'md:col-span-2 lg:col-span-2',
          )}
        >
          {imageUrl ? (
            <div className="article-card-media">
              <img
                src={imageUrl}
                alt=""
                loading="lazy"
                className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
              />
            </div>
          ) : null}

          <div className="article-card-content">
            <div className="article-card-topline">
              <div className="article-card-orb" aria-hidden="true">
                <span>{(category || title).slice(0, 1).toUpperCase()}</span>
              </div>

              <div className="flex min-w-0 flex-wrap items-center justify-end gap-2">
                {featured && <Badge type="featured" label="Featured" />}
                {trending && <Badge type="trending" label="Trending" icon={<TrendingUp size={12} />} />}
                {category && <Badge type="category" label={category} />}
              </div>
            </div>

            <h3 className="article-card-title line-clamp-3">{title}</h3>

            {description && (
              <p className="article-card-summary line-clamp-3">{description}</p>
            )}

            <div className="article-card-meta">
              {source && <span className="font-semibold text-black/70">{source}</span>}
              <span>
                <Calendar size={14} aria-hidden="true" />
                <time dateTime={publishedAt}>{formattedDate}</time>
              </span>
              {views !== undefined && (
                <span>
                  <Eye size={14} aria-hidden="true" />
                  {views.toLocaleString()}
                </span>
              )}
              <span>{estimatedReadingTime} min read</span>
            </div>

            <div className="article-card-footer">
              <span className="article-card-cta">
                Read article
                <ArrowUpRight size={16} aria-hidden="true" />
              </span>

              {(featured || trending || user?.is_admin) && (
                <div className="article-card-actions">
                  <motion.button
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.94 }}
                    onClick={(e) => {
                      e.preventDefault();
                      setIsLiked(!isLiked);
                    }}
                    aria-label={isLiked ? 'Unlike article' : 'Like article'}
                    aria-pressed={isLiked}
                    className={cn('article-card-icon-button', isLiked && 'active-red')}
                  >
                    <Heart size={16} fill={isLiked ? 'currentColor' : 'none'} aria-hidden="true" />
                  </motion.button>

                  <motion.button
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.94 }}
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
                    className={cn('article-card-icon-button', isBookmarked && 'active-blue')}
                  >
                    <Bookmark size={16} fill={isBookmarked ? 'currentColor' : 'none'} aria-hidden="true" />
                  </motion.button>

                  <motion.button
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.94 }}
                    onClick={(e) => e.preventDefault()}
                    aria-label="Share article"
                    className="article-card-icon-button"
                  >
                    <Share2 size={16} aria-hidden="true" />
                  </motion.button>

                  {user?.is_admin && (onEdit || onDelete) && (
                    <div className="relative">
                      <motion.button
                        type="button"
                        whileHover={{ scale: 1.08 }}
                        whileTap={{ scale: 0.94 }}
                        onClick={(e) => {
                          e.preventDefault();
                          setShowActionMenu(!showActionMenu);
                        }}
                        aria-label="Article options"
                        aria-expanded={showActionMenu}
                        aria-haspopup="menu"
                        className="article-card-icon-button"
                      >
                        <Edit2 size={16} aria-hidden="true" />
                      </motion.button>

                      {showActionMenu && (
                        <motion.div
                          initial={{ opacity: 0, y: -4, scale: 0.96 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          role="menu"
                          className="absolute right-0 top-full z-20 mt-2 w-40 rounded-2xl border border-black/10 bg-white/85 py-2 shadow-[0_16px_40px_rgba(0,0,0,0.16)] backdrop-blur-2xl"
                        >
                          {onEdit && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.preventDefault();
                                setShowActionMenu(false);
                                onEdit();
                              }}
                              className="flex w-full items-center gap-2 px-4 py-2.5 text-sm font-semibold text-black/70 hover:bg-black/5"
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
                              className="flex w-full items-center gap-2 px-4 py-2.5 text-sm font-semibold text-red-600 hover:bg-red-50"
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
          </div>
        </div>
      </Link>
    </motion.article>
  );
}
