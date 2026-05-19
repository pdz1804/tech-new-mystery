'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { User, Settings, Bookmark, Mail, Lock, Bell, Tag, CheckCircle } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchUserPreferences, updateUserPreferences, fetchSavedArticles } from '@/lib/api/user';
import { SavedArticleCard } from '@/components/profile/SavedArticleCard';
import { ProfileHeader } from '@/components/profile/ProfileHeader';
import { SettingsSection } from '@/components/profile/SettingsSection';
import { userKeys } from '@/lib/queryKeys';

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
  hidden: { opacity: 0, x: 20 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.3 } },
  exit: { opacity: 0, x: -20, transition: { duration: 0.2 } },
};

export default function ProfilePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const setIntendedDestination = useAuthStore((s) => s.setIntendedDestination);

  const [activeTab, setActiveTab] = useState<'profile' | 'preferences' | 'saved'>('profile');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([
    'Technology',
    'Science',
  ]);
  const [digestFrequency, setDigestFrequency] = useState('daily');

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

  if (!isHydrated || !isAuthenticated) {
    return null;
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
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'preferences', label: 'Preferences', icon: Settings },
    { id: 'saved', label: 'Saved Articles', icon: Bookmark },
  ] as const;

  return (
    <motion.main
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="min-h-screen bg-white"
    >
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
        className="sticky top-0 z-40 bg-white shadow-sm border-b border-slate-200"
      >
        <div className="mx-auto max-w-6xl px-4">
          <div className="flex gap-0 md:gap-8 overflow-x-auto">
            {tabs.map(({ id, label, icon: Icon }) => (
              <motion.button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-2 border-b-3 px-4 py-4 font-semibold transition-all md:px-0 whitespace-nowrap ${
                  activeTab === id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
                whileHover={{ color: activeTab === id ? '#2563EB' : '#1e293b' }}
              >
                <Icon className="h-5 w-5" />
                <span className="hidden sm:inline">{label}</span>
              </motion.button>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Content Area */}
      <motion.div
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="mx-auto max-w-6xl px-4 py-12"
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
                  <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 px-4 py-3 text-slate-900">
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
                  <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 px-4 py-3 text-slate-900">
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
                  <div className="rounded-lg border border-slate-200 bg-gradient-to-br from-slate-50 to-slate-100 px-4 py-3 font-mono text-sm text-slate-600 break-all">
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
                    className="mt-1 h-5 w-5 rounded border-slate-300 text-blue-600 transition-colors accent-blue-600"
                    aria-label="Enable email notifications"
                  />
                  <div className="flex-1">
                    <div className="font-semibold text-slate-900">Email Notifications</div>
                    <p className="mt-1 text-sm text-slate-600">
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
                      className="h-4 w-4 rounded border-slate-300 text-blue-600 transition-colors accent-blue-600"
                      aria-label={`Select ${category} as a preferred category`}
                    />
                    <span className="font-medium text-slate-700">{category}</span>
                  </motion.label>
                ))}
              </div>
            </SettingsSection>

            {/* Digest Frequency */}
            <SettingsSection title="Digest Frequency">
              <div className="space-y-4">
                <label htmlFor="frequency" className="block font-medium text-slate-900">
                  How often would you like to receive digests?
                </label>
                <select
                  id="frequency"
                  value={digestFrequency}
                  onChange={(e) => setDigestFrequency(e.target.value)}
                  className="w-full md:w-64 rounded-lg border border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 px-4 py-2.5 text-slate-900 font-medium transition-colors focus:border-blue-600 focus:ring-2 focus:ring-blue-600 focus:ring-opacity-20"
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
                className="rounded-lg bg-blue-600 px-8 py-3 font-semibold text-white transition-all hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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
              className="mb-8 text-2xl font-bold text-slate-900"
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
                className="relative overflow-hidden rounded-xl border-2 border-dashed border-slate-300 bg-gradient-to-br from-blue-50 to-indigo-50 p-12 text-center shadow-sm"
              >
                <div>
                  <Bookmark className="mx-auto h-12 w-12 text-blue-600 mb-4" />
                  <p className="text-lg font-bold text-slate-900">No Saved Articles Yet</p>
                  <p className="mt-2 text-slate-600">
                    Start exploring articles and save your favorites to read later.
                  </p>
                  <motion.a
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    href="/articles"
                    className="btn-primary mt-6 inline-flex items-center justify-center"
                  >
                    Explore Articles
                  </motion.a>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </motion.div>
    </motion.main>
  );
}
