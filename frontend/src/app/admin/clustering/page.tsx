'use client';

import { useCallback, useEffect, useState } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowLeft, GitBranch, LayoutDashboard, RefreshCw, Sparkles } from 'lucide-react';
import { AppLoadingState } from '@/components/ui/AppLoadingState';
import { apiClient } from '@/lib/api/client';
import type { ClusterListResponse } from '@/types/cluster';

interface EvaluationSummary {
  evaluation_id: string;
  num_articles: number;
  selected_k_value: number;
  weighted_score: number;
  quality_threshold_met: boolean;
}

interface EvaluationsResponse {
  items: EvaluationSummary[];
}

export default function AdminClusteringPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const [latestEvaluation, setLatestEvaluation] = useState<EvaluationSummary | null>(null);
  const [topicCount, setTopicCount] = useState<number | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(true);

  useEffect(() => {
    if (isHydrated && (!isAuthenticated || !user?.is_admin)) {
      router.push('/');
    }
  }, [isAuthenticated, isHydrated, user, router]);

  const fetchSummary = useCallback(async () => {
    if (!isHydrated || !isAuthenticated || !user?.is_admin) return;

    try {
      setLoadingSummary(true);
      const [evaluationsResponse, clustersResponse] = await Promise.all([
        apiClient.get<EvaluationsResponse>('/admin/clustering/evaluations', {
          params: { limit: 1, offset: 0 },
        }),
        apiClient.get<ClusterListResponse>('/clusters', {
          params: { page: 1, page_size: 1, sort_by: 'size' },
        }),
      ]);

      setLatestEvaluation(evaluationsResponse.data.items[0] ?? null);
      setTopicCount(clustersResponse.data.pagination.total_count);
    } finally {
      setLoadingSummary(false);
    }
  }, [isAuthenticated, isHydrated, user]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  if (!isHydrated || !isAuthenticated || !user?.is_admin) {
    return <AppLoadingState />;
  }

  const selectedK = latestEvaluation?.selected_k_value ?? null;
  const hasMismatch = selectedK !== null && topicCount !== null && selectedK !== topicCount;

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_18%_10%,rgba(37,99,235,0.10),transparent_30%),radial-gradient(circle_at_88%_8%,rgba(20,184,166,0.10),transparent_28%),linear-gradient(180deg,#f8fbff_0%,#eef5f8_100%)]">
      <div className="relative z-0 pt-44 md:pt-48">
        <div className="mx-auto max-w-6xl px-4 py-8 md:px-8 md:py-10">
          <motion.button
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            type="button"
            onClick={() => router.back()}
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/60 bg-white/60 px-4 py-2 text-sm font-semibold text-blue-700 shadow-sm backdrop-blur-2xl transition-all hover:bg-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </motion.button>

          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="overflow-hidden rounded-[28px] border border-white/60 border-t-white/90 bg-white/62 p-6 shadow-[0_26px_70px_-42px_rgba(15,23,42,0.55),inset_0_1px_0_rgba(255,255,255,0.9)] backdrop-blur-3xl md:p-8"
          >
            <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
              <div>
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/70 bg-white/60 px-3 py-1 text-xs font-bold text-blue-700">
                  <Sparkles size={14} aria-hidden="true" />
                  Clustering admin
                </div>
                <h1 className="text-4xl font-bold tracking-tight text-slate-950 md:text-5xl">
                  Clustering Control Center
                </h1>
                <p className="mt-3 max-w-2xl text-sm font-medium leading-6 text-slate-600">
                  Monitor the latest stored topic set and jump to the worker-backed article
                  embedding map. The admin page no longer runs ad-hoc PCA/KMeans inside the API,
                  so it will not disagree with the public Topics page.
                </p>
              </div>

              <button
                type="button"
                onClick={() => router.push('/topics')}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-blue-600 px-5 py-3 text-sm font-bold text-white shadow-[0_18px_32px_-18px_rgba(37,99,235,0.65)] transition-all hover:bg-blue-700"
              >
                Open Topics Map
                <LayoutDashboard size={16} aria-hidden="true" />
              </button>
            </div>

            <div className="mt-8 grid gap-3 md:grid-cols-4">
              <SummaryCard
                label="Selected K"
                value={loadingSummary ? '...' : selectedK ?? 'None'}
                helper="Latest evaluation choice"
              />
              <SummaryCard
                label="Stored Topics"
                value={loadingSummary ? '...' : topicCount ?? 'None'}
                helper="Latest visible cluster set"
              />
              <SummaryCard
                label="Articles Evaluated"
                value={loadingSummary ? '...' : latestEvaluation?.num_articles ?? 'None'}
                helper="Latest evaluation sample"
              />
              <SummaryCard
                label="Weighted Score"
                value={
                  loadingSummary || !latestEvaluation
                    ? '...'
                    : latestEvaluation.weighted_score.toFixed(3)
                }
                helper={latestEvaluation?.quality_threshold_met ? 'Threshold met' : 'Review quality'}
              />
            </div>

            {hasMismatch && (
              <div className="mt-5 rounded-2xl border border-amber-200/70 bg-amber-50/70 p-4 text-sm font-medium leading-6 text-amber-900">
                Selected K and stored topic count can differ when the latest persisted cluster
                rows were produced by another clustering strategy, filtering step, or older run.
                The Topics page is the source of truth for what users currently see.
              </div>
            )}

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={fetchSummary}
                className="inline-flex items-center gap-2 rounded-2xl border border-white/70 bg-white/62 px-4 py-2 text-sm font-bold text-slate-700 shadow-sm backdrop-blur-2xl transition-all hover:bg-white"
              >
                <RefreshCw size={15} aria-hidden="true" />
                Refresh status
              </button>
              <button
                type="button"
                onClick={() => router.push('/admin/queue')}
                className="inline-flex items-center gap-2 rounded-2xl border border-white/70 bg-white/62 px-4 py-2 text-sm font-bold text-slate-700 shadow-sm backdrop-blur-2xl transition-all hover:bg-white"
              >
                <GitBranch size={15} aria-hidden="true" />
                Admin dashboard
              </button>
            </div>
          </motion.section>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  helper,
}: {
  label: string;
  value: string | number;
  helper: string;
}) {
  return (
    <div className="rounded-2xl border border-white/65 bg-white/55 p-4 shadow-sm backdrop-blur-2xl">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-black text-slate-950">{value}</p>
      <p className="mt-1 text-xs font-medium text-slate-500">{helper}</p>
    </div>
  );
}
