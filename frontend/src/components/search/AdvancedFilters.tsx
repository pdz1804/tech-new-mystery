'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Filter } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface FilterOptions {
  category?: string;
  dateRange?: {
    from: string;
    to: string;
  };
  sortBy?: 'newest' | 'trending' | 'most-viewed';
  source?: string;
}

interface AdvancedFiltersProps {
  filters: FilterOptions;
  onFiltersChange: (filters: FilterOptions) => void;
  categories?: string[];
  sources?: string[];
}

const CATEGORIES = [
  'Technology',
  'AI & Machine Learning',
  'Web Development',
  'Mobile',
  'Cloud Computing',
  'Security',
  'DevOps',
  'Data Science',
];

const SOURCES = [
  'TechCrunch',
  'The Verge',
  'ArsTechnica',
  'Wired',
  'Forbes',
  'MIT Technology Review',
];

interface SortOption {
  value: 'newest' | 'trending' | 'most-viewed';
  label: string;
}

const SORT_OPTIONS: SortOption[] = [
  { value: 'newest', label: 'Newest First' },
  { value: 'trending', label: 'Trending' },
  { value: 'most-viewed', label: 'Most Viewed' },
];

export function AdvancedFilters({ filters, onFiltersChange }: AdvancedFiltersProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'category' | 'date' | 'sort' | 'source'>('category');

  const updateFilter = (key: keyof FilterOptions, value: string | { from: string; to: string } | 'newest' | 'trending' | 'most-viewed' | undefined) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const clearFilters = () => {
    onFiltersChange({});
  };

  const hasActiveFilters = Object.values(filters).some((v) => v !== undefined && v !== null);

  return (
    <div className="mb-6">
      <motion.button
        type="button"
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls="filters-panel"
        className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 font-medium text-slate-700 transition-all hover:border-blue-500 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
      >
        <Filter size={18} aria-hidden="true" />
        Advanced Filters
        {hasActiveFilters && (
          <span className="ml-2 rounded-full bg-blue-600 px-2 py-0.5 text-xs text-white" aria-label={`${Object.values(filters).filter((v) => v !== undefined && v !== null).length} filters applied`}>
            {Object.values(filters).filter((v) => v !== undefined && v !== null).length}
          </span>
        )}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            id="filters-panel"
            className="mt-4 rounded-lg border border-slate-200 bg-white p-6 shadow-lg"
          >
            {/* Tabs */}
            <div className="mb-6 flex gap-2 border-b border-slate-200" role="tablist">
              {['category', 'date', 'sort', 'source'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab as 'category' | 'date' | 'sort' | 'source')}
                  role="tab"
                  aria-selected={activeTab === tab ? 'true' : 'false'}
                  className={cn(
                    'px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2',
                    activeTab === tab
                      ? 'border-b-2 border-blue-600 text-blue-600'
                      : 'text-slate-600 hover:text-slate-900'
                  )}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>

            {/* Category Filter */}
            {activeTab === 'category' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
                <h3 className="font-semibold text-slate-900">Select Category</h3>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                  {CATEGORIES.map((cat) => (
                    <motion.button
                      key={cat}
                      whileHover={{ scale: 1.02 }}
                      onClick={() => updateFilter('category', filters.category === cat ? undefined : cat)}
                      className={cn(
                        'rounded-lg px-3 py-2 text-sm font-medium transition-all',
                        filters.category === cat
                          ? 'bg-blue-600 text-white'
                          : 'border border-slate-300 text-slate-700 hover:border-blue-500'
                      )}
                    >
                      {cat}
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Date Range Filter */}
            {activeTab === 'date' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
                <h3 className="font-semibold text-slate-900">Date Range</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="date-from" className="block text-sm font-medium text-slate-700 mb-2">From</label>
                    <input
                      id="date-from"
                      type="date"
                      value={filters.dateRange?.from || ''}
                      onChange={(e) =>
                        updateFilter('dateRange', {
                          from: e.target.value,
                          to: filters.dateRange?.to || '',
                        })
                      }
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
                    />
                  </div>
                  <div>
                    <label htmlFor="date-to" className="block text-sm font-medium text-slate-700 mb-2">To</label>
                    <input
                      id="date-to"
                      type="date"
                      value={filters.dateRange?.to || ''}
                      onChange={(e) =>
                        updateFilter('dateRange', {
                          from: filters.dateRange?.from || '',
                          to: e.target.value,
                        })
                      }
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
                    />
                  </div>
                </div>
              </motion.div>
            )}

            {/* Sort Filter */}
            {activeTab === 'sort' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
                <h3 className="font-semibold text-slate-900">Sort By</h3>
                <div className="space-y-2">
                  {SORT_OPTIONS.map((option) => (
                    <motion.button
                      key={option.value}
                      whileHover={{ x: 4 }}
                      onClick={() => updateFilter('sortBy', filters.sortBy === option.value ? undefined : option.value)}
                      className={cn(
                        'w-full rounded-lg px-4 py-2 text-left text-sm font-medium transition-all',
                        filters.sortBy === option.value
                          ? 'bg-blue-600 text-white'
                          : 'border border-slate-300 text-slate-700 hover:border-blue-500'
                      )}
                    >
                      {option.label}
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Source Filter */}
            {activeTab === 'source' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
                <h3 className="font-semibold text-slate-900">Select Source</h3>
                <div className="grid grid-cols-2 gap-3">
                  {SOURCES.map((src) => (
                    <motion.button
                      key={src}
                      whileHover={{ scale: 1.02 }}
                      onClick={() => updateFilter('source', filters.source === src ? undefined : src)}
                      className={cn(
                        'rounded-lg px-3 py-2 text-sm font-medium transition-all',
                        filters.source === src
                          ? 'bg-blue-600 text-white'
                          : 'border border-slate-300 text-slate-700 hover:border-blue-500'
                      )}
                    >
                      {src}
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Clear Filters Button */}
            {hasActiveFilters && (
              <motion.button
                type="button"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={clearFilters}
                className="mt-6 flex items-center gap-2 rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
              >
                <X size={16} aria-hidden="true" />
                Clear All Filters
              </motion.button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
