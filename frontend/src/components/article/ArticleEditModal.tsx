'use client';

import { useState, useCallback } from 'react';
import { X, Loader2, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Alert } from '@/components/ui/Alert';
import { useUpdateArticle, useDeleteArticle } from '@/hooks/useArticles';
import type { UpdateArticleRequest } from '@/lib/api/articles';
import type { ArticleResponse } from '@/types/article';

interface ArticleEditModalProps {
  isOpen: boolean;
  article: ArticleResponse & { content?: string; author?: string };
  onClose: () => void;
  onDeleteSuccess?: () => void;
}

export function ArticleEditModal({
  isOpen,
  article,
  onClose,
  onDeleteSuccess,
}: ArticleEditModalProps) {
  const [title, setTitle] = useState(article.title);
  const [content, setContent] = useState(article.content || '');
  const [author, setAuthor] = useState(article.author || '');
  const [category, setCategory] = useState(article.category || '');
  const [tags, setTags] = useState(article.tags?.join(', ') || '');
  const [successMessage, setSuccessMessage] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const updateMutation = useUpdateArticle();
  const deleteMutation = useDeleteArticle();

  const handleSave = useCallback(async () => {
    const newErrors: Record<string, string> = {};

    if (!title.trim()) {
      newErrors.title = 'Title is required';
    } else if (title.length > 500) {
      newErrors.title = 'Title must be 500 characters or less';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});

    const tagsArray = tags
      .split(',')
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0);

    const updateData: UpdateArticleRequest = {
      title,
    };

    if (content.trim()) {
      updateData.content = content;
    }

    if (author.trim()) {
      updateData.author = author;
    }

    if (category) {
      updateData.category = category;
    }

    if (tagsArray.length > 0) {
      updateData.tags = tagsArray;
    }

    try {
      await updateMutation.mutateAsync({ slug: article.slug, data: updateData });
      setSuccessMessage('Article updated successfully!');
      setTimeout(() => {
        setSuccessMessage('');
        onClose();
      }, 1500);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to update article';
      setErrors({ submit: errorMsg });
    }
  }, [title, content, author, category, tags, article.slug, updateMutation, onClose]);

  const handleDelete = useCallback(async () => {
    try {
      await deleteMutation.mutateAsync(article.slug);
      setSuccessMessage('Article deleted successfully!');
      setTimeout(() => {
        setSuccessMessage('');
        setShowDeleteConfirm(false);
        onClose();
        onDeleteSuccess?.();
      }, 1500);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to delete article';
      setErrors({ submit: errorMsg });
    }
  }, [article.slug, deleteMutation, onClose, onDeleteSuccess]);

  const isLoading = updateMutation.isPending || deleteMutation.isPending;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-md p-4">
      <div className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white/5 backdrop-blur-3xl backdrop-saturate-200 border border-white/20 glass-modal p-6">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 text-white/65 hover:text-white transition-colors"
          aria-label="Close modal"
        >
          <X size={24} />
        </button>

        {/* Header */}
        <h2 className="mb-6 text-2xl font-bold text-white">Edit Article</h2>

        {/* Success Message */}
        {successMessage && <Alert variant="success">{successMessage}</Alert>}

        {/* Error Message */}
        {errors.submit && <Alert variant="error">{errors.submit}</Alert>}

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 p-4">
            <p className="mb-4 text-sm text-white/80">
              Are you sure you want to delete this article? This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleDelete}
                disabled={isLoading}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {deleteMutation.isPending ? (
                  <>
                    <Loader2 size={14} className="mr-2 inline animate-spin" />
                    Deleting...
                  </>
                ) : (
                  'Delete Article'
                )}
              </button>
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isLoading}
                className="rounded-lg border border-white/20 px-4 py-2 text-sm font-semibold text-white/80 hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Form */}
        {!showDeleteConfirm && (
          <div className="space-y-4">
            <Input
              label="Title"
              placeholder="Article title..."
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                if (errors.title) {
                  setErrors({ ...errors, title: '' });
                }
              }}
              error={errors.title}
              disabled={isLoading}
              maxLength={500}
              helperText={`${title.length}/500 characters`}
            />

            <Input
              label="Author"
              placeholder="Author name"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              disabled={isLoading}
            />

            <div>
              <label htmlFor="category" className="block text-sm font-medium text-white/65 mb-1.5">
                Category
              </label>
              <select
                id="category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                disabled={isLoading}
                className="w-full rounded-lg border border-white/20 px-3 py-2 bg-black/20 text-white transition-colors focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20"
              >
                <option value="">Select category...</option>
                <option value="AI & ML">AI & ML</option>
                <option value="Security">Security</option>
                <option value="Cloud">Cloud</option>
                <option value="DevOps">DevOps</option>
                <option value="Frontend">Frontend</option>
                <option value="Backend">Backend</option>
                <option value="Data Science">Data Science</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-white/65 mb-1.5">
                Content
              </label>
              <textarea
                placeholder="Article content..."
                value={content}
                onChange={(e) => setContent(e.target.value)}
                disabled={isLoading}
                rows={6}
                className="w-full rounded-lg border border-white/20 px-3 py-2 bg-black/20 text-white placeholder-white/45 transition-colors focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 disabled:opacity-50"
              />
            </div>

            <Input
              label="Tags"
              placeholder="Enter tags separated by commas (e.g., AI, Python, Tutorial)"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              disabled={isLoading}
              helperText="Separate multiple tags with commas"
            />

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              <Button
                onClick={handleSave}
                disabled={isLoading}
                className="flex-1"
              >
                {updateMutation.isPending ? (
                  <>
                    <Loader2 size={16} className="mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save Changes'
                )}
              </Button>
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(true)}
                disabled={isLoading}
                className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-red-400 font-semibold hover:bg-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Trash2 size={16} />
                Delete
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
