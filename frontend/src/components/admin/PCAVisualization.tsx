'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { AlertCircle, Loader, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import { apiClient } from '@/lib/api/client';

interface PCAPoint {
  x: number;
  y: number;
  cluster: number;
  article_id: string;
}

interface ClusterMetadata {
  count: number;
  label: string;
  top_keywords: string[];
}

interface PCAVisualizationData {
  success: boolean;
  points: PCAPoint[];
  clusters: Record<string, ClusterMetadata>;
  best_k: number;
  silhouette_score: number;
  inertia: number;
  variance_explained: number;
  total_articles: number;
  message: string | null;
}

const CLUSTER_COLORS = [
  '#3B82F6', '#8B5CF6', '#10B981', '#F59E0B',
  '#EF4444', '#06B6D4', '#84CC16', '#F97316',
  '#EC4899', '#6366F1', '#14B8A6', '#F43F5E',
];

interface PCAVisualizationProps {
  kMin?: number;
  kMax?: number;
}

export default function PCAVisualization({ kMin = 5, kMax = 10 }: PCAVisualizationProps) {
  const router = useRouter();
  const [data, setData] = useState<PCAVisualizationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [selectedCluster, setSelectedCluster] = useState<number | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<string | null>(null);
  const [showLegend, setShowLegend] = useState(true);

  useEffect(() => {
    const fetchPCAData = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await apiClient.get<PCAVisualizationData>('/admin/clustering/pca', {
          params: { k_min: kMin, k_max: kMax },
        });

        setData(response.data);
      } catch (err) {
        console.error('Failed to fetch PCA visualization:', err);
        setError(
          err instanceof Error ? err.message : 'Failed to load PCA visualization. Please try again.'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchPCAData();
  }, [kMin, kMax]);

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex flex-col items-center justify-center gap-4 rounded-2xl bg-gradient-to-br from-white/60 to-white/40 border border-white/30 backdrop-blur-xl p-12 shadow-lg"
      >
        <Loader className="h-8 w-8 animate-spin text-blue-600" />
        <p className="text-sm font-medium text-slate-600">Loading PCA visualization...</p>
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex flex-col items-center justify-center gap-3 rounded-2xl bg-red-50/60 border border-red-200/60 backdrop-blur-xl p-6 shadow-lg"
      >
        <AlertCircle className="h-6 w-6 text-red-600" />
        <p className="text-sm font-medium text-red-700">{error}</p>
      </motion.div>
    );
  }

  if (!data) {
    return null;
  }

  // Normalize points for visualization
  const allX = data.points.map((p) => p.x);
  const allY = data.points.map((p) => p.y);
  const minX = Math.min(...allX);
  const maxX = Math.max(...allX);
  const minY = Math.min(...allY);
  const maxY = Math.max(...allY);
  const rangeX = maxX - minX || 1;
  const rangeY = maxY - minY || 1;

  const normalizeX = (x: number) => ((x - minX) / rangeX) * 100;
  const normalizeY = (y: number) => ((y - minY) / rangeY) * 100;

  const maxArticlesInCluster = Math.max(
    ...Object.values(data.clusters).map((c) => c.count)
  );

  const radiusScale = (count: number) => {
    return Math.max(4, Math.min(16, (count / maxArticlesInCluster) * 16));
  };

  const handlePointClick = (articleId: string) => {
    router.push(`/articles/${articleId}`);
  };

  const handleReset = () => {
    setZoom(1);
    setSelectedCluster(null);
    setHoveredPoint(null);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Header with stats */}
      <div className="space-y-2">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">PCA Visualization</h2>
            <p className="text-sm text-slate-600 mt-1">
              {data.total_articles} articles · {data.best_k} clusters · Silhouette: {data.silhouette_score.toFixed(3)}
            </p>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setZoom(Math.max(1, zoom - 0.2))}
              className="p-2 rounded-lg bg-white/60 border border-white/40 hover:bg-white/80 transition-all text-slate-600"
              aria-label="Zoom out"
            >
              <ZoomOut className="h-4 w-4" />
            </button>
            <span className="text-xs font-medium text-slate-600 w-8 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              type="button"
              onClick={() => setZoom(Math.min(3, zoom + 0.2))}
              className="p-2 rounded-lg bg-white/60 border border-white/40 hover:bg-white/80 transition-all text-slate-600"
              aria-label="Zoom in"
            >
              <ZoomIn className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="p-2 rounded-lg bg-white/60 border border-white/40 hover:bg-white/80 transition-all text-slate-600"
              aria-label="Reset view"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-lg bg-white/40 border border-white/30 p-3">
            <p className="text-xs font-medium text-slate-600 uppercase">Variance</p>
            <p className="text-lg font-bold text-slate-900">{(data.variance_explained * 100).toFixed(1)}%</p>
          </div>
          <div className="rounded-lg bg-white/40 border border-white/30 p-3">
            <p className="text-xs font-medium text-slate-600 uppercase">Inertia</p>
            <p className="text-lg font-bold text-slate-900">{data.inertia.toFixed(0)}</p>
          </div>
          <div className="rounded-lg bg-white/40 border border-white/30 p-3">
            <p className="text-xs font-medium text-slate-600 uppercase">Optimal K</p>
            <p className="text-lg font-bold text-slate-900">{data.best_k}</p>
          </div>
          <div className="rounded-lg bg-white/40 border border-white/30 p-3">
            <p className="text-xs font-medium text-slate-600 uppercase">Articles</p>
            <p className="text-lg font-bold text-slate-900">{data.total_articles}</p>
          </div>
        </div>
      </div>

      {/* Main visualization container */}
      <div className="space-y-3">
        {/* Chart */}
        <div className="relative rounded-2xl bg-gradient-to-br from-white/60 to-white/40 border border-white/30 backdrop-blur-xl shadow-lg overflow-hidden">
          <svg
            viewBox="0 0 800 500"
            className="w-full h-auto"
            role="img"
            aria-label="PCA scatter plot showing article clusters"
          >
            {/* Grid background */}
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path
                  d="M 40 0 L 0 0 0 40"
                  fill="none"
                  stroke="#e2e8f0"
                  strokeWidth="0.5"
                />
              </pattern>
            </defs>
            <rect width="800" height="500" fill="url(#grid)" />

            {/* Axes */}
            <line x1="50" y1="450" x2="750" y2="450" stroke="#94a3b8" strokeWidth="2" />
            <line x1="50" y1="450" x2="50" y2="20" stroke="#94a3b8" strokeWidth="2" />

            {/* Axis labels */}
            <text x="775" y="465" fontSize="12" fill="#64748b" fontWeight="500">
              PC1
            </text>
            <text x="20" y="30" fontSize="12" fill="#64748b" fontWeight="500">
              PC2
            </text>

            {/* Data points */}
            {data.points.map((point) => {
              const px = 50 + (normalizeX(point.x) / 100) * 700;
              const py = 450 - (normalizeY(point.y) / 100) * 430;
              const radius = radiusScale(data.clusters[String(point.cluster)]?.count || 1);
              const color = CLUSTER_COLORS[point.cluster % CLUSTER_COLORS.length];
              const isSelected = selectedCluster === null || selectedCluster === point.cluster;
              const isHovered = hoveredPoint === point.article_id;

              return (
                <g key={point.article_id}>
                  <circle
                    cx={px}
                    cy={py}
                    r={radius}
                    fill={color}
                    opacity={isSelected ? 0.8 : 0.2}
                    className="transition-all duration-200 cursor-pointer hover:opacity-95"
                    style={{
                      filter: isHovered ? 'drop-shadow(0 0 8px rgba(0,0,0,0.3))' : 'none',
                      transform: isHovered ? `scale(${1.3})` : 'scale(1)',
                      transformOrigin: `${px}px ${py}px`,
                    }}
                    onMouseEnter={() => setHoveredPoint(point.article_id)}
                    onMouseLeave={() => setHoveredPoint(null)}
                    onClick={() => handlePointClick(point.article_id)}
                  />
                  {/* Labels on hover */}
                  {isHovered && (
                    <text
                      x={px}
                      y={py - radius - 8}
                      textAnchor="middle"
                      fontSize="10"
                      fill="#1e293b"
                      fontWeight="bold"
                      pointerEvents="none"
                    >
                      Cluster {point.cluster}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>

        {/* Legend and cluster info */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          {/* Legend */}
          <div className="lg:col-span-2 rounded-2xl bg-gradient-to-br from-white/60 to-white/40 border border-white/30 backdrop-blur-xl shadow-lg p-4">
            <button
              type="button"
              onClick={() => setShowLegend(!showLegend)}
              className="w-full flex items-center justify-between mb-2"
            >
              <h3 className="text-sm font-semibold text-slate-900">Clusters</h3>
              <span className="text-xs text-slate-500">{showLegend ? '−' : '+'}</span>
            </button>

            <AnimatePresence>
              {showLegend && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-2"
                >
                  {Array.from({ length: data.best_k }).map((_, idx) => {
                    const clusterId = String(idx);
                    const meta = data.clusters[clusterId];
                    if (!meta) return null;

                    const isSelected = selectedCluster === null || selectedCluster === idx;
                    const color = CLUSTER_COLORS[idx % CLUSTER_COLORS.length];

                    return (
                      <button
                        key={clusterId}
                        type="button"
                        onClick={() => setSelectedCluster(selectedCluster === idx ? null : idx)}
                        className={`w-full flex items-center gap-3 p-2 rounded-lg transition-all ${
                          isSelected
                            ? 'bg-white/60 border border-white/40'
                            : 'bg-white/20 border border-white/10'
                        }`}
                      >
                        <div
                          className="h-4 w-4 rounded-full flex-shrink-0"
                          style={{ backgroundColor: color }}
                        />
                        <div className="min-w-0 flex-1 text-left">
                          <p className="text-xs font-medium text-slate-900">
                            Cluster {idx} · {meta.count} articles
                          </p>
                          <p className="text-xs text-slate-600 truncate">
                            {meta.top_keywords.join(', ') || 'No keywords'}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Instructions */}
          <div className="rounded-2xl bg-blue-50/60 border border-blue-200/60 backdrop-blur-xl shadow-lg p-4">
            <h3 className="text-sm font-semibold text-blue-900 mb-2">Tips</h3>
            <ul className="text-xs text-blue-800 space-y-1 list-disc list-inside">
              <li>Click a point to view article</li>
              <li>Hover to highlight clusters</li>
              <li>Use zoom to inspect dense areas</li>
              <li>Filter by cluster legend</li>
            </ul>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
