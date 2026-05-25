'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Settings, Bookmark, Mail, Lock, Bell, Tag, CheckCircle, Gauge, Zap, Loader2, Save } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchUserPreferences, updateUserPreferences, fetchSavedArticles } from '@/lib/api/user';
import { apiClient } from '@/lib/api/client';
import { SavedArticleCard } from '@/components/profile/SavedArticleCard';
import { ProfileHeader } from '@/components/profile/ProfileHeader';
import { SettingsSection } from '@/components/profile/SettingsSection';
import { userKeys } from '@/lib/queryKeys';
import { AppLoadingState } from '@/components/ui/AppLoadingState';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

const tabVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.18 } },
  exit: { opacity: 0, transition: { duration: 0.12 } },
};

export default function ProfilePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const setIntendedDestination = useAuthStore((s) => s.setIntendedDestination);

  const [activeTab, setActiveTab] = useState<'profile' | 'preferences' | 'saved' | 'settings'>('profile');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([
    'Technology',
    'Science',
  ]);
  const [digestFrequency, setDigestFrequency] = useState('daily');
  const [threshold, setThreshold] = useState(8.0);
  const [originalThreshold, setOriginalThreshold] = useState(8.0);
  const [savingThreshold, setSavingThreshold] = useState(false);
  const [backfilling, setBackfilling] = useState(false);
  const [forceBackfilling, setForceBackfilling] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const { data: preferencesData } = useQuery({
    queryKey: userKeys.preferences(),
    queryFn: fetchUserPreferences,
    enabled: isAuthenticated,
  });

  const { data: savedArticlesData } = useQuery({
    queryKey: userKeys.saves(),
    queryFn: fetchSavedArticles,
    enabled: isAuthenticated,
  });

  const updatePreferencesMutation = useMutation({
    mutationFn: updateUserPreferences,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.preferences() });
    },
  });

  useEffect(() => {
    if (!isHydrated) return;
    if (!isAuthenticated) {
      setIntendedDestination('/profile');
      router.push('/login');
    }
  }, [isAuthenticated, isHydrated, router, setIntendedDestination]);

  // Fetch threshold for admin users
  useEffect(() => {
    if (!user?.is_admin) return;
    const fetchThreshold = async () => {
      try {
        const { data } = await apiClient.get<{ success: boolean; threshold: number }>('/admin/settings/threshold');
        if (data?.success) {
          setThreshold(data.threshold);
          setOriginalThreshold(data.threshold);
        }
      } catch (err) {
        console.error('Error fetching threshold:', err);
      }
    };
    fetchThreshold();
  }, [user?.is_admin]);

  const handleLogout = () => {
    clearAuth();
    router.push('/login');
  };

  const handleSavePreferences = () => {
    const preferences = preferencesData || {};
    updatePreferencesMutation.mutate({
      ...preferences,
      notification_enabled: notificationsEnabled,
      preferred_categories: selectedCategories,
      digest_frequency: digestFrequency,
    });
  };

  const handleSaveThreshold = async () => {
    try {
      setSavingThreshold(true);
      const { data } = await apiClient.put<{ success: boolean; threshold: number }>('/admin/settings/threshold', {
        threshold: parseFloat(threshold.toString()),
      });
      if (data?.success) {
        setOriginalThreshold(data.threshold);
        setMessage({ type: 'success', text: `Threshold updated to ${data.threshold.toFixed(1)}/10` });
        setTimeout(() => setMessage(null), 5000);
      }
    } catch {
      setMessage({ type: 'error', text: 'Failed to save threshold' });
    } finally {
      setSavingThreshold(false);
    }
  };

  const handleBackfillScores = async () => {
    if (!window.confirm('Evaluate all articles without scores? This may take a few minutes.')) return;
    try {
      setBackfilling(true);
      const { data } = await apiClient.post<{ success: boolean }>('/admin/articles/backfill-scores');
      if (data?.success) {
        setMessage({ type: 'success', text: `Backfill queued. Check back in a few minutes...` });
        setTimeout(() => setMessage(null), 8000);
      }
    } catch {
      setMessage({ type: 'error', text: 'Failed to start backfill' });
    } finally {
      setBackfilling(false);
    }
  };

  const handleForceBackfillScores = async () => {
    if (!window.confirm('Re-evaluate ALL articles (including those with existing scores)? This may take several minutes.')) return;
    try {
      setForceBackfilling(true);
      const { data } = await apiClient.post<{ success: boolean }>('/admin/articles/backfill-scores-force');
      if (data?.success) {
        setMessage({ type: 'success', text: `Force backfill queued. Check back in a few minutes...` });
        setTimeout(() => setMessage(null), 8000);
      }
    } catch {
      setMessage({ type: 'error', text: 'Failed to start force backfill' });
    } finally {
      setForceBackfilling(false);
    }
  };

  if (!isHydrated || !isAuthenticated) {
    return <AppLoadingState variant="profile" />;
  }

  const savedArticles = savedArticlesData || [];
  const categories = [
    'Technology',
    'Science',
    'Business',
    'Health',
    'Entertainment',
    'AI/ML',
  ];

  const tabs = [
    { id: 'profile' as const, label: 'Profile', icon: User },
    { id: 'preferences' as const, label: 'Preferences', icon: Settings },
    { id: 'saved' as const, label: 'Saved Articles', icon: Bookmark },
    ...(user?.is_admin ? [{ id: 'settings' as const, label: 'Quality Settings', icon: Gauge }] : []),
  ];

  return (
    <motion.main
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="app-page-shell search-stage"
      id="main-content"
    >
      <div className="app-page-container">
      {/* Profile Header */}
      <ProfileHeader
        username={user?.username || 'User'}
        email={user?.email || ''}
        onLogout={handleLogout}
      />

      {/* Tab Navigation */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="my-6 flex justify-center"
      >
        <div className="segmented-glass max-w-full overflow-x-auto">
            {tabs.map(({ id, label, icon: Icon }) => (
              <motion.button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`segmented-item whitespace-nowrap ${
                  activeTab === id
                    ? 'active'
                    : ''
                }`}
              >
                <Icon className="h-5 w-5" />
                <span className="hidden sm:inline">{label}</span>
              </motion.button>
            ))}
        </div>
      </motion.div>

      {/* Content Area */}
      <motion.div
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="py-4"
      >
        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <motion.div
            variants={tabVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="space-y-6"
          >
            <SettingsSection title="Account Information">
              <div className="grid gap-6 md:grid-cols-2">
                {/* Username Field */}
                <motion.div variants={itemVariants}>
                  <label className="flex items-center gap-2 text-sm font-semibold text-slate-900 mb-3">
                    <User className="h-4 w-4 text-blue-600" />
                    Username
                  </label>
                  <div className="profile-field-glass">
                    <span className="text-base font-semibold">{user?.username}</span>
                    <CheckCircle className="h-4 w-4 text-green-600 ml-auto" />
                  </div>
                </motion.div>

                {/* Email Field */}
                <motion.div variants={itemVariants}>
                  <label className="flex items-center gap-2 text-sm font-semibold text-slate-900 mb-3">
                    <Mail className="h-4 w-4 text-blue-600" />
                    Email Address
                  </label>
                  <div className="profile-field-glass">
                    <span className="text-base font-semibold">{user?.email}</span>
                    <CheckCircle className="h-4 w-4 text-green-600 ml-auto" />
                  </div>
                </motion.div>

                {/* User ID Field */}
                <motion.div variants={itemVariants} className="md:col-span-2">
                  <label className="flex items-center gap-2 text-sm font-semibold text-slate-900 mb-3">
                    <Lock className="h-4 w-4 text-blue-600" />
                    User ID
                  </label>
                  <div className="profile-field-glass break-all font-mono text-sm text-black/60">
                    {user?.user_id}
                  </div>
                </motion.div>
              </div>
            </SettingsSection>
          </motion.div>
        )}

        {/* Preferences Tab */}
        {activeTab === 'preferences' && (
          <motion.div
            variants={tabVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="space-y-6"
          >
            {/* Notification Preferences */}
            <SettingsSection
              title="Notification Preferences"
              subtitle="Manage how and when you receive updates"
              icon={<Bell className="h-5 w-5" />}
            >
              <div className="space-y-4">
                <motion.label
                  variants={itemVariants}
                  className="flex items-start gap-4 cursor-pointer"
                  htmlFor="notifications-checkbox"
                >
                  <input
                    id="notifications-checkbox"
                    type="checkbox"
                    checked={notificationsEnabled}
                    onChange={(e) => setNotificationsEnabled(e.target.checked)}
                    className="mt-1 h-5 w-5 rounded border-black/20 bg-white/70 text-blue-600 transition-colors accent-blue-600"
                    aria-label="Enable email notifications"
                  />
                  <div className="flex-1">
                    <div className="font-semibold text-black">Email Notifications</div>
                    <p className="mt-1 text-sm text-black/60">
                      Receive email updates about new articles and trending topics
                    </p>
                  </div>
                </motion.label>
              </div>
            </SettingsSection>

            {/* Category Preferences */}
            <SettingsSection
              title="Preferred Categories"
              subtitle="Select topics you're interested in"
              icon={<Tag className="h-5 w-5" />}
            >
              <div className="grid gap-3 grid-cols-2 md:grid-cols-3">
                {categories.map((category) => (
                  <motion.label
                    key={category}
                    variants={itemVariants}
                    className="flex items-center gap-3 cursor-pointer"
                    htmlFor={`category-${category.toLowerCase().replace(/\//g, '-')}`}
                  >
                    <input
                      id={`category-${category.toLowerCase().replace(/\//g, '-')}`}
                      type="checkbox"
                      checked={selectedCategories.includes(category)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedCategories([...selectedCategories, category]);
                        } else {
                          setSelectedCategories(
                            selectedCategories.filter((c) => c !== category)
                          );
                        }
                      }}
                      className="h-4 w-4 rounded border-black/20 bg-white/70 text-blue-600 transition-colors accent-blue-600"
                      aria-label={`Select ${category} as a preferred category`}
                    />
                    <span className="font-medium text-black/70">{category}</span>
                  </motion.label>
                ))}
              </div>
            </SettingsSection>

            {/* Digest Frequency */}
            <SettingsSection title="Digest Frequency">
              <div className="space-y-4">
                <label htmlFor="frequency" className="block font-medium text-black">
                  How often would you like to receive digests?
                </label>
                <select
                  id="frequency"
                  value={digestFrequency}
                  onChange={(e) => setDigestFrequency(e.target.value)}
                  className="auth-field w-full bg-white/70 text-black md:w-64"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
            </SettingsSection>

            {/* Save Button */}
            <motion.div variants={itemVariants}>
              <motion.button
                whileHover={{ scale: 1.02, boxShadow: '0 4px 12px rgba(37, 99, 235, 0.4)' }}
                whileTap={{ scale: 0.98 }}
                onClick={handleSavePreferences}
                disabled={updatePreferencesMutation.isPending}
                className="btn-liquid primary flex items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {updatePreferencesMutation.isPending ? (
                  <>
                    <div className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <span>Save Preferences</span>
                )}
              </motion.button>
            </motion.div>
          </motion.div>
        )}

        {/* Saved Articles Tab */}
        {activeTab === 'saved' && (
          <motion.div
            variants={tabVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <motion.h2
              variants={itemVariants}
              className="mb-8 text-2xl font-bold text-black"
            >
              Saved Articles
            </motion.h2>

            {savedArticles.length > 0 ? (
              <motion.div
                variants={containerVariants}
                className="grid gap-6 md:grid-cols-2 lg:grid-cols-3"
              >
                {savedArticles.map((article: { article_id: string; title: string; slug: string; published_at?: string; created_at: string; category?: string; view_count?: number; summary?: string }) => (
                  <SavedArticleCard
                    key={article.article_id}
                    id={article.article_id}
                    title={article.title}
                    slug={article.slug}
                    publishedAt={article.published_at || article.created_at}
                    category={article.category || undefined}
                    views={article.view_count}
                    summary={article.summary || undefined}
                  />
                ))}
              </motion.div>
            ) : (
              <motion.div
                variants={itemVariants}
                className="apple-empty-state p-12 text-center"
              >
                <div>
                  <Bookmark className="mx-auto h-12 w-12 text-blue-600 mb-4" />
                  <p className="text-lg font-bold text-black">No Saved Articles Yet</p>
                  <p className="mt-2 text-black/60">
                    Start exploring articles and save your favorites to read later.
                  </p>
                  <motion.a
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    href="/articles"
                    className="btn-liquid primary mt-6 inline-flex items-center justify-center"
                  >
                    Explore Articles
                  </motion.a>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* Settings Tab (Admin Only) */}
        {activeTab === 'settings' && user?.is_admin && (
          <motion.div
            variants={tabVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="space-y-6"
          >
            {/* Success/Error Messages */}
            <AnimatePresence>
              {message && (
                <motion.div
                  variants={itemVariants}
                  initial="hidden"
                  animate="visible"
                  exit={{ opacity: 0, y: -20 }}
                  className={`glass-panel p-4 flex items-center gap-3 border-l-4 ${
                    message.type === 'success'
                      ? 'border-green-500/30 bg-green-50/50'
                      : 'border-red-500/30 bg-red-50/50'
                  }`}
                >
                  <div className={`w-2 h-2 rounded-full ${message.type === 'success' ? 'bg-green-500' : 'bg-red-500'}`} />
                  <p className={`text-sm font-semibold ${message.type === 'success' ? 'text-green-700' : 'text-red-700'}`}>
                    {message.text}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Threshold Setting */}
            <motion.div variants={itemVariants}>
              <SettingsSection title="Quality Threshold" subtitle="Control what non-admin users see">
                <div className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2 items-end">
                    <div>
                      <label htmlFor="threshold" className="flex items-center gap-2 text-sm font-semibold text-black/80 mb-3">
                        <Gauge className="h-4 w-4 text-blue-600" />
                        Score (0.0 - 10.0)
                      </label>
                      <input
                        id="threshold"
                        type="number"
                        min="0"
                        max="10"
                        step="0.1"
                        value={threshold}
                        onChange={(e) => setThreshold(parseFloat(e.target.value) || 0)}
                        disabled={savingThreshold}
                        className="w-full px-4 py-3 rounded-lg border border-black/10 bg-white/50 text-black
                          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                          disabled:opacity-50 transition-all"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleSaveThreshold}
                      disabled={savingThreshold || threshold === originalThreshold}
                      className="btn-liquid primary"
                    >
                      {savingThreshold ? (
                        <>
                          <Loader2 size={16} className="animate-spin inline mr-2" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Save size={16} className="inline mr-2" />
                          Save
                        </>
                      )}
                    </button>
                  </div>
                  <div className="text-xs text-black/50">
                    Current: <span className="font-semibold text-black/70">{originalThreshold.toFixed(1)}/10</span>
                  </div>
                </div>
              </SettingsSection>
            </motion.div>

            {/* Backfill Scores */}
            <motion.div variants={itemVariants}>
              <SettingsSection title="Score Backfill" subtitle="Evaluate articles quality scores">
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-2">
                      <p className="text-xs text-black/60">
                        Articles without scores
                      </p>
                      <button
                        type="button"
                        onClick={handleBackfillScores}
                        disabled={backfilling || forceBackfilling}
                        className="w-full bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold
                          px-4 py-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-green-500/20
                          hover:shadow-lg hover:shadow-green-500/40 hover:-translate-y-1 transition-all
                          disabled:opacity-50 disabled:hover:translate-y-0 text-sm"
                      >
                        {backfilling ? (
                          <>
                            <Loader2 size={16} className="animate-spin" />
                            <span>Starting...</span>
                          </>
                        ) : (
                          <>
                            <Zap size={16} />
                            <span>Backfill</span>
                          </>
                        )}
                      </button>
                    </div>

                    <div className="space-y-2">
                      <p className="text-xs text-black/60">
                        Re-evaluate all articles
                      </p>
                      <button
                        type="button"
                        onClick={handleForceBackfillScores}
                        disabled={forceBackfilling || backfilling}
                        className="w-full bg-gradient-to-r from-orange-600 to-red-600 text-white font-semibold
                          px-4 py-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-orange-500/20
                          hover:shadow-lg hover:shadow-orange-500/40 hover:-translate-y-1 transition-all
                          disabled:opacity-50 disabled:hover:translate-y-0 text-sm"
                      >
                        {forceBackfilling ? (
                          <>
                            <Loader2 size={16} className="animate-spin" />
                            <span>Starting...</span>
                          </>
                        ) : (
                          <>
                            <Zap size={16} />
                            <span>Force Re-eval</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </SettingsSection>
            </motion.div>
          </motion.div>
        )}
      </motion.div>
      </div>
    </motion.main>
  );
}
