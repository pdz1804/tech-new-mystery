'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowLeft, Save, X } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useArticleBySlug } from '@/hooks/useArticles';
import { apiClient } from '@/lib/api/client';

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

export default function EditArticlePage({ params }: { params: { slug: string } }) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const setIntendedDestination = useAuthStore((s) => s.setIntendedDestination);
  const { data, isLoading, error } = useArticleBySlug(params.slug);

  const [title, setTitle] = useState('');
  const [summary, setSummary] = useState('');
  const [content, setContent] = useState('');
  const [category, setCategory] = useState('');
  const [tags, setTags] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!isHydrated) return;
    if (!isAuthenticated) {
      setIntendedDestination(`/articles/${params.slug}/edit`);
      router.push('/login');
    }
  }, [isAuthenticated, isHydrated, router, setIntendedDestination, params.slug]);

  useEffect(() => {
    if (data?.data) {
      setTitle(data.data.title);
      setSummary(data.data.summary || '');
      setContent(data.data.content || '');
      setCategory(data.data.category || '');
      setTags(data.data.tags?.join(', ') || '');
    }
  }, [data]);

  if (!isHydrated || !isAuthenticated) {
    return null;
  }

  if (isLoading) {
    return (
      <motion.main
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 py-12"
      >
        <div className="mx-auto max-w-2xl px-4">
          <motion.div variants={itemVariants} className="animate-pulse space-y-6">
            <div className="h-8 w-32 rounded-lg bg-slate-300" />
            <div className="h-12 w-full rounded-lg bg-slate-300" />
            <div className="h-32 w-full rounded-lg bg-slate-300" />
          </motion.div>
        </div>
      </motion.main>
    );
  }

  if (error || !data?.data) {
    return (
      <motion.main
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center"
      >
        <motion.div variants={itemVariants} className="text-center">
          <p className="text-lg font-semibold text-slate-900 mb-4">Failed to load article</p>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => router.back()}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2 font-semibold text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Go Back
          </motion.button>
        </motion.div>
      </motion.main>
    );
  }

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const updateData: any = {};
      if (title) updateData.title = title;
      if (summary) updateData.summary = summary;
      if (content) updateData.content = content;
      if (category) updateData.category = category;
      if (tags) updateData.tags = tags.split(',').map(t => t.trim()).filter(t => t);

      await apiClient.put(`/articles/${params.slug}`, updateData);
      alert('Article updated successfully!');
      router.push(`/articles/${params.slug}`);
    } catch (err: any) {
      console.error('Save failed:', err);
      alert(err.response?.data?.detail || 'Failed to save article');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <motion.main
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 py-12"
    >
      <div className="mx-auto max-w-2xl px-4">
        {/* Header */}
        <motion.div
          variants={itemVariants}
          className="mb-8 flex items-center justify-between"
        >
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => router.back()}
            className="flex items-center gap-2 rounded-lg bg-white px-4 py-2 font-semibold text-slate-900 border border-slate-200 hover:bg-slate-50"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </motion.button>
          <h1 className="text-3xl font-bold text-slate-900">Edit Article</h1>
          <div className="w-24" />
        </motion.div>

        {/* Edit Form */}
        <motion.div
          variants={containerVariants}
          className="space-y-6 rounded-xl bg-white p-8 border border-slate-200 shadow-sm"
        >
          {/* Title */}
          <motion.div variants={itemVariants}>
            <label className="block text-sm font-semibold text-slate-900 mb-2">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Article title"
            />
          </motion.div>

          {/* Summary */}
          <motion.div variants={itemVariants}>
            <label className="block text-sm font-semibold text-slate-900 mb-2">
              Summary
            </label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              rows={3}
              className="w-full px-4 py-2 rounded-lg border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Brief summary of the article"
            />
          </motion.div>

          {/* Category */}
          <motion.div variants={itemVariants}>
            <label className="block text-sm font-semibold text-slate-900 mb-2">
              Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select category</option>
              <option value="AI">AI</option>
              <option value="Web Development">Web Development</option>
              <option value="DevOps">DevOps</option>
              <option value="Security">Security</option>
              <option value="Mobile">Mobile</option>
              <option value="Cloud Computing">Cloud Computing</option>
              <option value="Data Science">Data Science</option>
              <option value="Infrastructure">Infrastructure</option>
              <option value="Blockchain">Blockchain</option>
              <option value="Other">Other</option>
            </select>
          </motion.div>

          {/* Tags */}
          <motion.div variants={itemVariants}>
            <label className="block text-sm font-semibold text-slate-900 mb-2">
              Tags (comma-separated)
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="tag1, tag2, tag3"
            />
          </motion.div>

          {/* Content */}
          <motion.div variants={itemVariants}>
            <label className="block text-sm font-semibold text-slate-900 mb-2">
              Content
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={10}
              className="w-full px-4 py-2 rounded-lg border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
              placeholder="Article content"
            />
          </motion.div>

          {/* Actions */}
          <motion.div
            variants={itemVariants}
            className="flex gap-3 justify-end pt-4 border-t border-slate-200"
          >
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => router.back()}
              className="flex items-center gap-2 rounded-lg bg-slate-100 px-6 py-2.5 font-semibold text-slate-900 hover:bg-slate-200"
            >
              <X className="h-4 w-4" />
              Cancel
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="h-4 w-4" />
              {isSaving ? 'Saving...' : 'Save Changes'}
            </motion.button>
          </motion.div>
        </motion.div>
      </div>
    </motion.main>
  );
}
