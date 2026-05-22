'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Sparkles } from 'lucide-react';

interface SearchQueryModalProps {
  isOpen: boolean;
  source: 'tavily' | 'newsapi';
  defaultQueries: string[];
  onConfirm: (queries: string[]) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function SearchQueryModal({
  isOpen,
  source,
  defaultQueries,
  onConfirm,
  onCancel,
  isLoading = false,
}: SearchQueryModalProps) {
  const [queries, setQueries] = React.useState<string[]>(defaultQueries);

  React.useEffect(() => {
    setQueries(defaultQueries);
  }, [defaultQueries]);

  const handleAddQuery = () => {
    setQueries([...queries, '']);
  };

  const handleRemoveQuery = (index: number) => {
    setQueries(queries.filter((_, i) => i !== index));
  };

  const handleUpdateQuery = (index: number, value: string) => {
    const updated = [...queries];
    updated[index] = value;
    setQueries(updated);
  };

  const handleConfirm = () => {
    const filtered = queries.filter((q) => q.trim());
    if (filtered.length > 0) {
      onConfirm(filtered);
    }
  };

  const isModified = JSON.stringify(queries) !== JSON.stringify(defaultQueries);

  return (
    <AnimatePresence mode="wait">
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/40 backdrop-blur-md z-[100] flex items-center justify-center p-4"
          onClick={onCancel}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 20 }}
            transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-2xl bg-white/95 backdrop-blur-xl border border-black/10 rounded-3xl
              shadow-[0_32px_64px_-10px_rgba(0,0,0,0.15)] p-8"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center">
                  <Sparkles size={20} className="text-white" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-black">
                    {source === 'tavily' ? 'Tavily Search' : 'NewsAPI Search'}
                  </h2>
                  <p className="text-sm text-black/60">Review and customize your search queries</p>
                </div>
              </div>
              <button
                type="button"
                onClick={onCancel}
                className="w-8 h-8 rounded-lg hover:bg-black/5 flex items-center justify-center transition-colors"
                aria-label="Close modal"
              >
                <X size={20} className="text-black/60" />
              </button>
            </div>

            {/* Date Info */}
            <div className="mb-6 p-4 bg-blue-50 rounded-xl border border-blue-200/50">
              <p className="text-sm text-black/60">
                <span className="font-semibold text-black">Searching yesterday&apos;s news</span> for latest tech trends, AI, agents, and cloud platform updates
              </p>
            </div>

            {/* Queries List */}
            <div className="space-y-3 mb-8 max-h-64 overflow-y-auto">
              {queries.map((query, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="flex gap-2"
                >
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => handleUpdateQuery(index, e.target.value)}
                    placeholder="Search query..."
                    className="flex-1 bg-white border border-black/10 rounded-lg px-4 py-3 text-black
                      placeholder-black/40 focus:outline-none focus:ring-1 focus:ring-blue-500/50
                      focus:border-blue-500/80 transition-all"
                  />
                  {queries.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveQuery(index)}
                      className="px-3 py-3 rounded-lg bg-red-50 hover:bg-red-100 text-red-600 transition-colors"
                      aria-label="Remove query"
                    >
                      <X size={18} />
                    </button>
                  )}
                </motion.div>
              ))}
            </div>

            {/* Add Query Button */}
            <button
              type="button"
              onClick={handleAddQuery}
              className="w-full mb-6 px-4 py-3 rounded-lg bg-black/5 hover:bg-black/10
                text-black font-medium transition-colors border border-black/10"
            >
              + Add Query
            </button>

            {/* Footer */}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onCancel}
                disabled={isLoading}
                className="flex-1 px-4 py-3 rounded-lg bg-black/5 hover:bg-black/10
                  text-black font-medium transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={isLoading}
                className="flex-1 px-4 py-3 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600
                  text-white font-semibold shadow-lg shadow-blue-500/20 hover:shadow-lg
                  hover:shadow-blue-500/40 hover:-translate-y-0.5 transition-all disabled:opacity-50
                  disabled:hover:translate-y-0"
              >
                {isLoading ? 'Searching...' : 'Search'}
              </button>
            </div>

            {/* Status */}
            {isModified && (
              <p className="text-xs text-black/50 text-center mt-4">
                Modified from defaults
              </p>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
