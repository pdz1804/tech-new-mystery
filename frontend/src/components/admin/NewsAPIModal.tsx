'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Loader2, Zap } from 'lucide-react';
import { apiClient } from '@/lib/api/client';

interface NewsAPIModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SOURCES = [
  { name: 'TechCrunch', desc: 'Startup & AI news' },
  { name: 'The Verge', desc: 'Consumer tech + AI' },
  { name: 'Google News', desc: 'Main aggregator' },
];

const DEFAULT_QUERY_PURPOSE = "Discover the latest breakthroughs in artificial intelligence, machine learning, cloud infrastructure, and tech innovation.";

export function NewsAPIModal({ isOpen, onClose }: NewsAPIModalProps) {
  const [customQuery, setCustomQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSearch = async () => {
    setIsSearching(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const query = customQuery.trim() || undefined;
      const { data } = await apiClient.post('/admin/newsapi/trigger', {
        ...(query && { query }),
      });

      if (data.success) {
        setSuccessMessage(data.message || 'Search triggered successfully!');
        setTimeout(() => {
          onClose();
          setCustomQuery('');
          setSuccessMessage(null);
        }, 2000);
      } else {
        setErrorMessage(data.message || 'Failed to trigger search');
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to trigger search';
      setErrorMessage(msg);
    } finally {
      setIsSearching(false);
    }
  };

  const handleClose = () => {
    if (!isSearching) {
      setCustomQuery('');
      setSuccessMessage(null);
      setErrorMessage(null);
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-md p-4"
          onClick={handleClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 400 }}
            className="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="relative bg-gradient-to-br from-blue-50 to-slate-50 px-6 pt-4 pb-4">
              <button
                type="button"
                onClick={handleClose}
                disabled={isSearching}
                className="absolute right-3 top-3 text-slate-400 hover:text-slate-600 disabled:opacity-50 transition-colors"
                aria-label="Close"
              >
                <X size={20} />
              </button>

              <div className="flex items-start gap-2 pr-8">
                <div className="rounded-lg bg-blue-600 p-1.5 flex-shrink-0 mt-0.5">
                  <Zap size={16} className="text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="text-lg font-bold text-slate-900">NewsAPI Search</h2>
                  <p className="text-xs text-slate-600 mt-0.5">
                    Fetch from TechCrunch, The Verge, Google News
                  </p>
                </div>
              </div>
            </div>

            {/* Content */}
            <div className="px-6 py-4 space-y-3">
              {/* Info */}
              <div className="rounded-lg bg-blue-50 border border-blue-100 p-3">
                <p className="text-xs text-blue-900 leading-snug">
                  <span className="font-semibold">Searches yesterday&apos;s news</span> for latest tech trends, AI, and cloud innovations
                </p>
              </div>

              {/* Sources */}
              <div>
                <h3 className="text-xs font-semibold text-slate-900 mb-2">Sources (5 articles each)</h3>
                <div className="space-y-1.5">
                  {SOURCES.map((source) => (
                    <div
                      key={source.name}
                      className="flex items-center gap-2 p-2 rounded-lg border border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50/30 transition-all"
                    >
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-600 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-900 text-sm">{source.name}</p>
                        <p className="text-xs text-slate-500">{source.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Default Query */}
              <div>
                <h3 className="text-xs font-semibold text-slate-900 mb-1">Default Coverage</h3>
                <p className="text-xs text-slate-600 leading-snug">
                  {DEFAULT_QUERY_PURPOSE}
                </p>
              </div>

              {/* Custom Query */}
              <div>
                <label htmlFor="custom-query" className="block text-xs font-semibold text-slate-900 mb-1.5">
                  Custom Query <span className="font-normal text-slate-500">(optional)</span>
                </label>
                <textarea
                  id="custom-query"
                  value={customQuery}
                  onChange={(e) => setCustomQuery(e.target.value)}
                  disabled={isSearching}
                  placeholder="Leave empty to use default..."
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed resize-none"
                  rows={2}
                  aria-label="Custom search query"
                />
              </div>

              {/* Messages */}
              {successMessage && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm font-medium"
                >
                  ✓ {successMessage}
                </motion.div>
              )}

              {errorMessage && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm font-medium"
                >
                  ✕ {errorMessage}
                </motion.div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-slate-200 px-6 py-3 bg-slate-50 flex gap-2 justify-end">
              <button
                type="button"
                onClick={handleClose}
                disabled={isSearching}
                className="px-4 py-2 rounded-lg border border-slate-300 text-slate-900 font-medium text-sm hover:bg-slate-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSearch}
                disabled={isSearching}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 text-white font-medium text-sm hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md"
              >
                {isSearching ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <Zap size={16} />
                    <span>Search</span>
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
