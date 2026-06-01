'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ChevronRight, Heart, Layers3, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import type { Cluster } from '@/types/cluster';

export interface ClusterCardProps {
  cluster: Cluster;
  onClick?: (clusterId: string) => void;
  variant?: 'compact' | 'full';
  className?: string;
}

function diversityWidth(score: number) {
  if (score >= 0.9) return 'w-full';
  if (score >= 0.8) return 'w-[80%]';
  if (score >= 0.7) return 'w-[70%]';
  if (score >= 0.6) return 'w-[60%]';
  if (score >= 0.5) return 'w-1/2';
  if (score >= 0.4) return 'w-[40%]';
  if (score >= 0.3) return 'w-[30%]';
  if (score >= 0.2) return 'w-1/5';
  return 'w-[10%]';
}

export function ClusterCard({
  cluster,
  onClick,
  variant = 'full',
  className,
}: ClusterCardProps) {
  const sortedArticles = [...cluster.top_articles]
    .sort((a, b) => (b.engagement_score || 0) - (a.engagement_score || 0))
    .slice(0, 3);

  const handleCardClick = (e: React.MouseEvent) => {
    if (onClick) {
      e.preventDefault();
      onClick(cluster.id);
    }
  };

  const lastUpdated = formatDistanceToNow(new Date(cluster.updated_at * 1000), {
    addSuffix: true,
  });

  if (variant === 'compact') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={{ y: -2, scale: 1.01 }}
        transition={{ duration: 0.2 }}
        className={cn('group relative', className)}
      >
        <Link href={`/topics/${cluster.id}`} onClick={handleCardClick}>
          <div className="relative h-full overflow-hidden rounded-[20px] border border-white/55 bg-white/62 p-4 shadow-[0_18px_40px_-30px_rgba(15,23,42,0.5),inset_0_1px_0_rgba(255,255,255,0.86)] backdrop-blur-3xl transition-all duration-300 hover:bg-white/78 hover:shadow-[0_22px_50px_-32px_rgba(15,23,42,0.58)]">
            <div className="mb-2 flex items-start justify-between gap-2">
              <h3 className="line-clamp-1 flex-1 text-sm font-bold text-slate-950 group-hover:text-blue-700">
                {cluster.label}
              </h3>
              <span className="flex-shrink-0 text-xs font-bold text-blue-700">
                {cluster.article_count}
              </span>
            </div>
            <p className="mb-3 line-clamp-1 text-xs text-slate-600">
              {cluster.description}
            </p>
            <div className="flex flex-wrap gap-1">
              {cluster.keywords.slice(0, 2).map((keyword) => (
                <span
                  key={keyword}
                  className="inline-flex rounded-full border border-blue-100/80 bg-blue-50/70 px-2.5 py-0.5 text-xs font-medium text-blue-700"
                >
                  #{keyword}
                </span>
              ))}
              {cluster.keywords.length > 2 && (
                <span className="text-xs font-medium text-slate-500">+{cluster.keywords.length - 2}</span>
              )}
            </div>
          </div>
        </Link>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, scale: 1.01 }}
      transition={{ duration: 0.25 }}
      className={cn('group relative', className)}
    >
      <Link href={`/topics/${cluster.id}`} onClick={handleCardClick}>
        <div className="relative flex h-full min-h-[360px] flex-col overflow-hidden rounded-[28px] border border-white/55 border-t-white/90 bg-white/58 p-5 shadow-[0_24px_64px_-42px_rgba(15,23,42,0.62),inset_0_1px_0_rgba(255,255,255,0.9)] backdrop-blur-3xl transition-all duration-300 hover:-translate-y-0.5 hover:bg-white/72 hover:shadow-[0_32px_78px_-42px_rgba(15,23,42,0.7)]">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(255,255,255,0.92),transparent_34%),radial-gradient(circle_at_92%_8%,rgba(37,99,235,0.12),transparent_28%)]" />

          <div className="relative mb-4 flex items-start justify-between gap-4">
            <div className="flex min-w-0 items-center gap-2">
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-2xl border border-blue-100/80 bg-blue-50/80 text-blue-600 shadow-sm">
                <Layers3 className="h-4 w-4" aria-hidden="true" />
              </div>
              <span className="rounded-full border border-white/60 bg-white/55 px-2.5 py-1 text-xs font-semibold text-slate-600 backdrop-blur-xl">
                {cluster.size_category.toLowerCase()}
              </span>
            </div>
            <div className="flex items-center gap-1 rounded-full border border-white/60 bg-white/55 px-2.5 py-1 text-xs font-bold text-blue-700 backdrop-blur-xl">
              <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
              {cluster.article_count}
            </div>
          </div>

          <div className="relative mb-4 space-y-2">
            <h3 className="line-clamp-2 text-lg font-bold leading-snug text-slate-950 group-hover:text-blue-700">
              {cluster.label}
            </h3>
            <p className="line-clamp-3 text-sm leading-6 text-slate-600">
              {cluster.description}
            </p>
          </div>

          <div className="relative mb-4 flex flex-wrap gap-1.5">
            {cluster.keywords.slice(0, 5).map((keyword) => (
              <span
                key={keyword}
                className="inline-flex items-center rounded-full border border-blue-100/80 bg-blue-50/70 px-2.5 py-0.5 text-xs font-medium text-blue-700"
              >
                #{keyword}
              </span>
            ))}
            {cluster.keywords.length > 5 && (
              <span className="inline-flex items-center text-xs font-medium text-slate-500">
                +{cluster.keywords.length - 5} more
              </span>
            )}
          </div>

          <div className="relative mb-4 grid grid-cols-2 gap-2 rounded-[20px] border border-white/50 bg-white/38 p-3 backdrop-blur-2xl">
            <div>
              <div className="text-2xl font-bold leading-none text-slate-950">{cluster.article_count}</div>
              <div className="mt-1 text-xs font-semibold text-slate-500">articles</div>
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-500">Diversity</div>
              <div className="mt-1 text-sm font-bold text-slate-800">
                {(cluster.diversity_score * 100).toFixed(0)}%
              </div>
              <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-200/70">
                <div className={cn('h-1.5 rounded-full bg-blue-500', diversityWidth(cluster.diversity_score))} />
              </div>
            </div>
          </div>

          {sortedArticles.length > 0 && (
            <div className="relative mb-4 flex-1 space-y-2">
              <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">
                Top Articles
              </div>
              {sortedArticles.map((article) => (
                <div
                  key={article.id}
                  className="flex items-center justify-between gap-2 rounded-2xl border border-white/45 bg-white/36 px-3 py-2 text-xs leading-snug text-slate-700 backdrop-blur-xl"
                  title={article.title}
                >
                  <span className="line-clamp-1 flex-1">{article.title}</span>
                  <div className="flex flex-shrink-0 items-center gap-1 text-red-500">
                    <Heart className="h-3 w-3" fill="currentColor" />
                    <span className="text-xs font-medium">
                      {article.engagement_score.toFixed(1)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="relative mt-auto flex items-center justify-between border-t border-white/50 pt-4 text-sm font-semibold text-blue-700 transition-colors group-hover:text-blue-800">
            <span className="text-xs font-medium text-slate-500">Updated {lastUpdated}</span>
            <span className="inline-flex items-center gap-1">
              View details
              <ChevronRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />
            </span>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}
