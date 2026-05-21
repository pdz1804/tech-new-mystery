'use client';

import { useState, useCallback } from 'react';
import { X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Alert } from '@/components/ui/Alert';
import { useCreateArticle, useCreateArticleFromUrl } from '@/hooks/useArticles';
import type { CreateArticleRequest, CreateArticleFromUrlRequest } from '@/lib/api/articles';

interface ArticleCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type TabType = 'url' | 'manual';

export function ArticleCreateModal({ isOpen, onClose }: ArticleCreateModalProps) {
  const [activeTab, setActiveTab] = useState<TabType>('url');
  const [successMessage, setSuccessMessage] = useState<string>('');

  // URL Tab State
  const [urlInput, setUrlInput] = useState('');
  const [urlTitle, setUrlTitle] = useState('');
  const [urlAuthor, setUrlAuthor] = useState('');
  const [urlAutoSummarize, setUrlAutoSummarize] = useState(true);

  // Manual Tab State
  const [manualTitle, setManualTitle] = useState('');
  const [manualUrl, setManualUrl] = useState('');
  const [manualContent, setManualContent] = useState('');
  const [manualAuthor, setManualAuthor] = useState('');
  const [manualCategory, setManualCategory] = useState('');
  const [manualTags, setManualTags] = useState('');

  // Validation Errors
  const [errors, setErrors] = useState<Record<string, string>>({});

  const createFromUrlMutation = useCreateArticleFromUrl();
  const createArticleMutation = useCreateArticle();

  // URL validation helper
  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const handleUrlTabSubmit = useCallback(async () => {
    const newErrors: Record<string, string> = {};

    // Validate URL
    if (!urlInput.trim()) {
      newErrors.url = 'URL is required';
    } else if (!isValidUrl(urlInput)) {
      newErrors.url = 'Please enter a valid URL (e.g., https://example.com)';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});

    const payload: CreateArticleFromUrlRequest = {
      url: urlInput,
      auto_summarize: urlAutoSummarize,
    };

    if (urlTitle.trim()) {
      payload.title = urlTitle;
    }

    if (urlAuthor.trim()) {
      payload.author = urlAuthor;
    }

    try {
      await createFromUrlMutation.mutateAsync(payload);
      setSuccessMessage('Article created successfully from URL!');
      setTimeout(() => {
        setUrlInput('');
        setUrlTitle('');
        setUrlAuthor('');
        setSuccessMessage('');
        onClose();
      }, 1500);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to create article from URL';
      setErrors({ submit: errorMsg });
    }
  }, [urlInput, urlTitle, urlAuthor, urlAutoSummarize, createFromUrlMutation, onClose]);

  const handleManualTabSubmit = useCallback(async () => {
    const newErrors: Record<string, string> = {};

    // Validate required fields
    if (!manualTitle.trim()) {
      newErrors.title = 'Title is required';
    } else if (manualTitle.length > 500) {
      newErrors.title = 'Title must be 500 characters or less';
    }

    if (!manualUrl.trim()) {
      newErrors.url = 'URL is required';
    } else if (!isValidUrl(manualUrl)) {
      newErrors.url = 'Please enter a valid URL';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});

    const tagsArray = manualTags
      .split(',')
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0);

    const payload: CreateArticleRequest = {
      title: manualTitle,
      url: manualUrl,
    };

    if (manualContent.trim()) {
      payload.content = manualContent;
    }

    if (manualAuthor.trim()) {
      payload.author = manualAuthor;
    }

    if (manualCategory) {
      payload.category = manualCategory;
    }

    if (tagsArray.length > 0) {
      payload.tags = tagsArray;
    }

    try {
      await createArticleMutation.mutateAsync(payload);
      setSuccessMessage('Article created successfully!');
      setTimeout(() => {
        setManualTitle('');
        setManualUrl('');
        setManualContent('');
        setManualAuthor('');
        setManualCategory('');
        setManualTags('');
        setSuccessMessage('');
        onClose();
      }, 1500);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to create article';
      setErrors({ submit: errorMsg });
    }
  }, [manualTitle, manualUrl, manualContent, manualAuthor, manualCategory, manualTags, createArticleMutation, onClose]);

  const isUrlLoading = createFromUrlMutation.isPending;
  const isManualLoading = createArticleMutation.isPending;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-md p-4">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-3xl bg-white backdrop-blur-3xl backdrop-saturate-200 border border-black/8 glass-modal">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 text-black/60 hover:text-black transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg p-1"
          aria-label="Close modal"
        >
          <X size={24} />
        </button>

        {/* Header */}
        <div className="border-b border-black/8 px-8 py-6">
          <h2 className="text-3xl font-bold text-black">Create Article</h2>
        </div>

        {/* Content */}
        <div className="px-8 py-6">

        {/* Success Message */}
        {successMessage && <Alert variant="success">{successMessage}</Alert>}

        {/* Error Message */}
        {errors.submit && <Alert variant="error">{errors.submit}</Alert>}

        {/* Tabs */}
        <div className="mb-6 flex gap-0 border-b border-black/8">
          <button
            type="button"
            onClick={() => {
              setActiveTab('url');
              setErrors({});
            }}
            className={`px-6 py-3 font-semibold transition-all text-sm ${
              activeTab === 'url'
                ? 'border-b-2 border-blue-600 text-black'
                : 'text-black/60 hover:text-black'
            }`}
          >
            From URL
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab('manual');
              setErrors({});
            }}
            className={`px-6 py-3 font-semibold transition-all text-sm ${
              activeTab === 'manual'
                ? 'border-b-2 border-blue-600 text-black'
                : 'text-black/60 hover:text-black'
            }`}
          >
            Manual Entry
          </button>
        </div>

        {/* URL Tab Content */}
        {activeTab === 'url' && (
          <div className="space-y-4">
            <Input
              label="Article URL"
              type="url"
              placeholder="https://example.com/article"
              value={urlInput}
              onChange={(e) => {
                setUrlInput(e.target.value);
                if (errors.url) {
                  setErrors({ ...errors, url: '' });
                }
              }}
              error={errors.url}
              disabled={isUrlLoading}
            />

            <Input
              label="Title (Optional)"
              placeholder="Auto-filled if left empty"
              value={urlTitle}
              onChange={(e) => setUrlTitle(e.target.value)}
              disabled={isUrlLoading}
              helperText="If left empty, the title will be extracted from the article"
            />

            <Input
              label="Author (Optional)"
              placeholder="Auto-filled if left empty"
              value={urlAuthor}
              onChange={(e) => setUrlAuthor(e.target.value)}
              disabled={isUrlLoading}
              helperText="If left empty, the author will be extracted from the article"
            />

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="autoSummarize"
                checked={urlAutoSummarize}
                onChange={(e) => setUrlAutoSummarize(e.target.checked)}
                disabled={isUrlLoading}
                className="h-4 w-4 cursor-pointer accent-blue-500"
              />
              <label htmlFor="autoSummarize" className="text-sm font-medium text-black/60 cursor-pointer">
                Generate AI summary automatically
              </label>
            </div>

            <Button
              onClick={handleUrlTabSubmit}
              disabled={isUrlLoading || !urlInput.trim()}
              className="w-full btn-primary mt-2"
              aria-busy={isUrlLoading}
            >
              {isUrlLoading ? (
                <>
                  <Loader2 size={16} className="mr-2 animate-spin" aria-hidden="true" />
                  Creating Article...
                </>
              ) : (
                'Parse Article'
              )}
            </Button>
          </div>
        )}

        {/* Manual Tab Content */}
        {activeTab === 'manual' && (
          <div className="space-y-4">
            <Input
              label="Title"
              placeholder="Article title..."
              value={manualTitle}
              onChange={(e) => {
                setManualTitle(e.target.value);
                if (errors.title) {
                  setErrors({ ...errors, title: '' });
                }
              }}
              error={errors.title}
              disabled={isManualLoading}
              maxLength={500}
              helperText={`${manualTitle.length}/500 characters`}
            />

            <Input
              label="URL"
              type="url"
              placeholder="https://example.com/article"
              value={manualUrl}
              onChange={(e) => {
                setManualUrl(e.target.value);
                if (errors.url) {
                  setErrors({ ...errors, url: '' });
                }
              }}
              error={errors.url}
              disabled={isManualLoading}
            />

            <Input
              label="Author (Optional)"
              placeholder="Author name"
              value={manualAuthor}
              onChange={(e) => setManualAuthor(e.target.value)}
              disabled={isManualLoading}
            />

            <div>
              <label htmlFor="manualCategory" className="block text-sm font-medium text-black/60 mb-1.5">
                Category (Optional)
              </label>
              <select
                id="manualCategory"
                value={manualCategory}
                onChange={(e) => setManualCategory(e.target.value)}
                disabled={isManualLoading}
                className="w-full px-4 py-2.5 text-sm bg-white/80 border border-black/10 rounded-lg transition-all duration-150 placeholder-black/40 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-500/20 hover:border-black/15 disabled:opacity-50 disabled:cursor-not-allowed text-black"
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
              <label htmlFor="manualContent" className="block text-sm font-medium text-black/60 mb-1.5">
                Content (Optional)
              </label>
              <textarea
                id="manualContent"
                placeholder="Paste article content here..."
                value={manualContent}
                onChange={(e) => setManualContent(e.target.value)}
                disabled={isManualLoading}
                rows={6}
                className="w-full px-4 py-2.5 text-sm bg-white/80 border border-black/10 rounded-lg transition-all duration-150 placeholder-black/40 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-500/20 hover:border-black/15 disabled:opacity-50 disabled:cursor-not-allowed resize-none text-black"
              />
            </div>

            <Input
              label="Tags (Optional)"
              placeholder="Enter tags separated by commas (e.g., AI, Python, Tutorial)"
              value={manualTags}
              onChange={(e) => setManualTags(e.target.value)}
              disabled={isManualLoading}
              helperText="Separate multiple tags with commas"
            />

            <Button
              onClick={handleManualTabSubmit}
              disabled={isManualLoading || !manualTitle.trim() || !manualUrl.trim()}
              className="w-full btn-primary mt-2"
            >
              {isManualLoading ? (
                <>
                  <Loader2 size={16} className="mr-2 animate-spin" />
                  Creating Article...
                </>
              ) : (
                'Create Article'
              )}
            </Button>
          </div>
        )}
        </div>
      </div>
    </div>
  );
}
