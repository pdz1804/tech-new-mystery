'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Loader2, CheckCircle, AlertCircle, Plus } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useRouter } from 'next/navigation';
import { Alert } from '@/components/ui/Alert';

interface SearchResult {
  id: string;
  title: string;
  snippet: string;
  source: string;
  date: string;
  url: string;
}

interface CreateResponse {
  success: boolean;
  article_id?: string;
  message?: string;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

export default function AdminSearchPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const userRole = useAuthStore((s) => s.user?.role);
  const setIntendedDestination = useAuthStore((s) => s.setIntendedDestination);

  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [creatingArticleIds, setCreatingArticleIds] = useState<Set<string>>(new Set());
  const [successMessages, setSuccessMessages] = useState<Record<string, string>>({});
  const [errorMessages, setErrorMessages] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);

  // Protect route - redirect if not admin
  if (isHydrated && (!isAuthenticated || userRole !== 'admin')) {
    setIntendedDestination('/admin/search');
    router.push('/login');
    return null;
  }

  if (!isHydrated) {
    return null;
  }

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    if (!searchQuery.trim()) {
      setGeneralError('Please enter a search topic');
      return;
    }

    setIsSearching(true);
    setGeneralError(null);
    setSearchResults([]);

    try {
      const response = await fetch('/api/v1/admin/search/tavily', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ topic: searchQuery }),
      });

      if (!response.ok) {
        throw new Error('Failed to search articles');
      }

      const data = await response.json();
      setSearchResults(data.results || []);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to search articles';
      setGeneralError(errorMsg);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [searchQuery]);

  const handleApproveAndCreate = useCallback(async (result: SearchResult) => {
    setCreatingArticleIds((prev) => new Set([...prev, result.id]));
    setErrorMessages((prev) => ({ ...prev, [result.id]: '' }));

    try {
      const response = await fetch('/api/v1/admin/search/approve-and-create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: result.title,
          url: result.url,
          snippet: result.snippet,
          source: result.source,
        }),
      });

      const data: CreateResponse = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.message || 'Failed to create article');
      }

      setSuccessMessages((prev) => ({
        ...prev,
        [result.id]: 'Article created successfully!',
      }));

      // Auto-dismiss success message after 3 seconds
      setTimeout(() => {
        setSuccessMessages((prev) => {
          const updated = { ...prev };
          delete updated[result.id];
          return updated;
        });
      }, 3000);

      // Remove from results
      setSearchResults((prev) => prev.filter((r) => r.id !== result.id));
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to create article';
      setErrorMessages((prev) => ({
        ...prev,
        [result.id]: errorMsg,
      }));
    } finally {
      setCreatingArticleIds((prev) => {
        const updated = new Set(prev);
        updated.delete(result.id);
        return updated;
      });
    }
  }, []);

  return (
    <motion.main
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="min-h-screen bg-gradient-to-b from-slate-50 to-white"
    >
      {/* Header Section */}
      <motion.section
        variants={itemVariants}
        className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-blue-500 to-indigo-600 px-4 py-20 md:py-28"
      >
        <div className="absolute inset-0 opacity-20">
          <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-white blur-3xl"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-blue-400 blur-3xl"></div>
        </div>

        <div className="relative mx-auto max-w-4xl">
          <motion.div variants={itemVariants} className="text-center mb-8">
            <h1 className="text-5xl md:text-6xl font-bold mb-4 text-white">
              Admin Search
            </h1>
            <p className="text-lg md:text-xl text-blue-100 max-w-2xl mx-auto">
              Search for articles and approve them for publication
            </p>
          </motion.div>

          {/* Search Form */}
          <motion.form
            variants={itemVariants}
            onSubmit={handleSearch}
            className="flex flex-col sm:flex-row gap-3 mx-auto max-w-3xl"
          >
            <div className="relative flex-1">
              <div className="relative flex items-center rounded-xl bg-white/95 shadow-lg hover:shadow-xl transition-all duration-300">
                <Search
                  size={24}
                  className="absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-400 pointer-events-none flex-shrink-0"
                />
                <input
                  type="text"
                  placeholder="Enter a topic to search..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-14 pr-4 py-4 text-lg text-slate-900 placeholder-slate-500 bg-transparent outline-none font-medium"
                  aria-label="Search articles by topic"
                />
              </div>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              type="submit"
              disabled={isSearching || !searchQuery.trim()}
              className="flex items-center justify-center gap-2 px-6 py-4 bg-white text-blue-600 font-semibold rounded-xl shadow-lg hover:shadow-xl hover:bg-blue-50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-300 whitespace-nowrap"
              aria-busy={isSearching}
            >
              {isSearching ? (
                <>
                  <Loader2 size={20} className="animate-spin" aria-hidden="true" />
                  <span className="hidden sm:inline">Searching...</span>
                </>
              ) : (
                <>
                  <Search size={20} aria-hidden="true" />
                  <span className="hidden sm:inline">Search</span>
                </>
              )}
            </motion.button>
          </motion.form>
        </div>
      </motion.section>

      {/* Results Section */}
      <motion.section
        variants={itemVariants}
        className="mx-auto max-w-6xl px-4 py-16"
      >
        {/* General Error Alert */}
        {generalError && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mb-8"
          >
            <Alert variant="error">{generalError}</Alert>
          </motion.div>
        )}

        {/* Results */}
        {searchResults.length > 0 ? (
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-6"
          >
            <motion.div variants={itemVariants} className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-2">
                Search Results
              </h2>
              <p className="text-slate-600">
                Found {searchResults.length} article{searchResults.length !== 1 ? 's' : ''} for "{searchQuery}"
              </p>
            </motion.div>

            <AnimatePresence mode="popLayout">
              {searchResults.map((result) => (
                <motion.div
                  key={result.id}
                  variants={cardVariants}
                  layout
                  exit={{ opacity: 0, height: 0 }}
                  className="group relative rounded-lg border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition-all duration-200"
                >
                  {/* Success Message */}
                  {successMessages[result.id] && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="mb-4 flex items-center gap-2 text-green-700 bg-green-50 px-4 py-3 rounded-lg"
                    >
                      <CheckCircle size={18} aria-hidden="true" />
                      {successMessages[result.id]}
                    </motion.div>
                  )}

                  {/* Error Message */}
                  {errorMessages[result.id] && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="mb-4 flex items-center gap-2 text-red-700 bg-red-50 px-4 py-3 rounded-lg"
                    >
                      <AlertCircle size={18} aria-hidden="true" />
                      {errorMessages[result.id]}
                    </motion.div>
                  )}

                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      {/* Title */}
                      <h3 className="text-lg font-bold text-slate-900 mb-2 line-clamp-2 group-hover:text-blue-600 transition-colors">
                        {result.title}
                      </h3>

                      {/* Snippet */}
                      <p className="text-slate-600 text-sm mb-4 line-clamp-2">
                        {result.snippet}
                      </p>

                      {/* Metadata */}
                      <div className="flex flex-col gap-2 text-xs text-slate-500">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-700">Source:</span>
                          {result.source}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-700">Date:</span>
                          {result.date}
                        </div>
                      </div>
                    </div>

                    {/* Action Button */}
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => handleApproveAndCreate(result)}
                      disabled={creatingArticleIds.has(result.id)}
                      className="flex items-center gap-2 px-4 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 whitespace-nowrap flex-shrink-0"
                      aria-busy={creatingArticleIds.has(result.id)}
                    >
                      {creatingArticleIds.has(result.id) ? (
                        <>
                          <Loader2 size={16} className="animate-spin" aria-hidden="true" />
                          <span className="hidden sm:inline">Creating...</span>
                        </>
                      ) : (
                        <>
                          <Plus size={16} aria-hidden="true" />
                          <span className="hidden sm:inline">Approve & Create</span>
                        </>
                      )}
                    </motion.button>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        ) : searchQuery && !isSearching ? (
          <motion.div
            variants={itemVariants}
            className="rounded-2xl border-2 border-dashed border-slate-300 bg-gradient-to-br from-slate-50 to-slate-100 p-16 text-center"
          >
            <div className="inline-block mb-4 rounded-full bg-slate-200 p-6">
              <Search size={40} className="text-slate-500" aria-hidden="true" />
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-2">No Articles Found</h3>
            <p className="text-lg text-slate-600 mb-8">
              Try a different search term or topic
            </p>
          </motion.div>
        ) : !searchQuery ? (
          <motion.div
            variants={itemVariants}
            className="rounded-2xl border-2 border-dashed border-slate-300 bg-gradient-to-br from-slate-50 to-slate-100 p-16 text-center"
          >
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 3, repeat: Infinity }}
              className="inline-block mb-4"
            >
              <div className="rounded-full bg-blue-100 p-6">
                <Search size={40} className="text-blue-600" aria-hidden="true" />
              </div>
            </motion.div>
            <h3 className="text-2xl font-bold text-slate-900 mb-2">Start Searching</h3>
            <p className="text-lg text-slate-600">
              Enter a topic above to search for articles and approve them for publication
            </p>
          </motion.div>
        ) : null}
      </motion.section>
    </motion.main>
  );
}
