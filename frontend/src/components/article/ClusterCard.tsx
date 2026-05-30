'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Heart, TrendingUp, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import type { Cluster } from '@/types/cluster';

export interface ClusterCardProps {
  cluster: Cluster;
  onClick?: (clusterId: string) => void;
  variant?: 'compact' | 'full';
  className?: string;
}

export function ClusterCard({
  cluster,
  onClick,
  variant = 'full',
  className,
}: ClusterCardProps) {
  const truncateText = (text: string, lines: number = 2) => {
    const lineArray = text.split('\n').slice(0, lines);
    return lineArray.join('\n');
  };

  const sortedArticles = [...cluster.top_articles]
    .sort((a, b) => (b.engagement_score || 0) - (a.engagement_score || 0))
    .slice(0, 3);

  const isCompact = variant === 'compact';

  const handleCardClick = (e: React.MouseEvent) => {
    if (onClick) {
      e.preventDefault();
      onClick(cluster.id);
    }
  };

  const lastUpdated = formatDistanceToNow(new Date(cluster.updated_at * 1000), {
    addSuffix: true,
  });

  // Compact variant: simplified view
  if (isCompact) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={{ y: -2, scale: 1.01 }}
        transition={{ duration: 0.2 }}
        className={cn('group relative', className)}
      >
        <Link href={`/topics/${cluster.id}`} onClick={handleCardClick}>
          <div className="relative h-full overflow-hidden rounded-[20px] bg-white/60 backdrop-blur-md border border-white/30 shadow-md p-4 transition-all duration-300 hover:bg-white/80 hover:shadow-xl">
            <div className="flex items-start justify-between gap-2 mb-2">
              <h3 className="flex-1 text-sm font-semibold text-slate-900 line-clamp-1 group-hover:text-slate-950">
                {cluster.label}
              </h3>
              <span className="flex-shrink-0 text-xs font-medium text-slate-500">
                {cluster.article_count}
              </span>
            </div>
            <p className="text-xs text-slate-600 line-clamp-1 mb-3">
              {cluster.description}
            </p>
            <div className="flex flex-wrap gap-1">
              {cluster.keywords.slice(0, 2).map((keyword) => (
                <span
                  key={keyword}
                  className="inline-flex rounded-full bg-blue-50/70 border border-blue-100 px-2.5 py-0.5 text-xs text-blue-700"
                >
                  #{keyword}
                </span>
              ))}
              {cluster.keywords.length > 2 && (
                <span className="text-xs text-slate-500">+{cluster.keywords.length - 2}</span>
              )}
            </div>
          </div>
        </Link>
      </motion.div>
    );
  }

  // Full variant: detailed Liquid Glass view
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, scale: 1.02 }}
      transition={{ duration: 0.3 }}
      className={cn('group relative', className)}
    >
      <Link href={`/topics/${cluster.id}`} onClick={handleCardClick}>
        <div className="relative h-full overflow-hidden rounded-3xl bg-white/60 backdrop-blur-md border border-white/30 shadow-md hover:shadow-xl hover:bg-white/80 transition-all duration-300 p-6">
          {/* Header */}
          <div className="mb-4 space-y-2">
            <div className="flex items-start justify-between gap-3">
              <h3 className="flex-1 text-lg font-semibold text-slate-900 line-clamp-2 group-hover:text-slate-950">
                {cluster.label}
              </h3>
              <div className="flex-shrink-0 text-blue-500 group-hover:text-blue-600 transition-colors">
                <TrendingUp className="w-5 h-5" />
              </div>
            </div>

            <p className="text-sm text-slate-600 line-clamp-2">
              {truncateText(cluster.description)}
            </p>
          </div>

          {/* Keywords/Tags */}
          <div className="mb-4 flex flex-wrap gap-1.5">
            {cluster.keywords.slice(0, 5).map((keyword) => (
              <span
                key={keyword}
                className="inline-flex items-center rounded-full bg-blue-50/70 border border-blue-100 px-2.5 py-0.5 text-xs text-blue-700"
              >
                #{keyword}
              </span>
            ))}
            {cluster.keywords.length > 5 && (
              <span className="inline-flex items-center text-xs text-slate-500">
                +{cluster.keywords.length - 5} more
              </span>
            )}
          </div>

          {/* Stats */}
          <div className="mb-4 grid grid-cols-2 gap-3 py-3 border-y border-white/20">
            {/* Article count */}
            <div className="space-y-0.5">
              <div className="text-2xl font-bold text-slate-900">{cluster.article_count}</div>
              <div className="text-xs text-slate-500 font-medium">articles</div>
            </div>
            {/* Diversity */}
            <div className="space-y-1">
              <div className="text-xs text-slate-500 font-medium">Diversity</div>
              <div className="text-sm font-semibold text-slate-700">
                {(cluster.diversity_score * 100).toFixed(0)}%
              </div>
              <div className="w-full h-1 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-1 rounded-full bg-gradient-to-r from-blue-400 to-purple-400',
                    cluster.diversity_score >= 0.9 ? 'w-full' :
                    cluster.diversity_score >= 0.8 ? 'w-[80%]' :
                    cluster.diversity_score >= 0.7 ? 'w-[70%]' :
                    cluster.diversity_score >= 0.6 ? 'w-[60%]' :
                    cluster.diversity_score >= 0.5 ? 'w-1/2' :
                    cluster.diversity_score >= 0.4 ? 'w-[40%]' :
                    cluster.diversity_score >= 0.3 ? 'w-[30%]' :
                    cluster.diversity_score >= 0.2 ? 'w-1/5' :
                    'w-[10%]'
                  )}
                />
              </div>
            </div>
          </div>

          {/* Top Articles Preview */}
          {sortedArticles.length > 0 && (
            <div className="mb-4 space-y-2 rounded-2xl bg-white/40 border border-white/20 p-3">
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
                Top Articles
              </div>
              {sortedArticles.map((article) => (
                <div
                  key={article.id}
                  className="text-xs text-slate-700 leading-snug flex items-center justify-between gap-2 pb-2 last:pb-0"
                  title={article.title}
                >
                  <span className="line-clamp-1 flex-1">{article.title}</span>
                  <div className="flex items-center gap-1 flex-shrink-0 text-red-500">
                    <Heart className="w-3 h-3" fill="currentColor" />
                    <span className="text-xs font-medium">
                      {article.engagement_score.toFixed(1)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Last Updated */}
          <div className="mb-4 text-xs text-slate-400">
            Updated {lastUpdated}
          </div>

          {/* Footer — view details row */}
          <div className="flex items-center justify-between text-sm font-medium text-blue-600 group-hover:text-blue-700 transition-colors">
            <span>View Details</span>
            <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 translate-x-0 group-hover:translate-x-1 transition-all duration-200" />
          </div>
        </div>
      </Link>
    </motion.div>
  );
}
