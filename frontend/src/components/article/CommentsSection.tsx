'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchArticleComments, createComment } from '@/lib/api/comments';
import { commentKeys } from '@/lib/queryKeys';
import { format } from 'date-fns';

interface CommentsSectionProps {
  articleId: string;
}

export function CommentsSection({ articleId }: CommentsSectionProps) {
  const queryClient = useQueryClient();
  const [newComment, setNewComment] = useState('');

  const { data: commentsData, isLoading } = useQuery({
    queryKey: commentKeys.byArticle(articleId),
    queryFn: () => fetchArticleComments(articleId),
  });

  const createCommentMutation = useMutation({
    mutationFn: (content: string) => createComment(articleId, content),
    onSuccess: () => {
      setNewComment('');
      queryClient.invalidateQueries({ queryKey: commentKeys.byArticle(articleId) });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newComment.trim()) {
      createCommentMutation.mutate(newComment);
    }
  };

  const comments = commentsData?.data || [];

  return (
    <section className="mt-8 border-t border-slate-200 pt-8">
      <h3 className="mb-6 text-2xl font-bold text-slate-900">Comments</h3>

      {/* Comment Form */}
      <form onSubmit={handleSubmit} className="mb-8" aria-label="Add a new comment">
        <label htmlFor="comment-textarea" className="block mb-2 text-sm font-medium text-slate-900">
          Share your thoughts
        </label>
        <textarea
          id="comment-textarea"
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Share your thoughts..."
          rows={4}
          aria-invalid={createCommentMutation.error ? 'true' : 'false'}
          className="w-full rounded-lg border border-slate-300 px-4 py-3 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
        />
        <button
          type="submit"
          disabled={!newComment.trim() || createCommentMutation.isPending}
          aria-busy={createCommentMutation.isPending ? 'true' : 'false'}
          className="mt-2 rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
        >
          {createCommentMutation.isPending ? 'Posting...' : 'Post Comment'}
        </button>
      </form>

      {/* Comments List */}
      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse rounded-lg bg-slate-100 p-4 h-24"></div>
          ))}
        </div>
      ) : comments.length > 0 ? (
        <ol className="space-y-6">
          {comments.map((comment: { comment_id: string; author?: string; created_at: string; content: string }) => (
            <li
              key={comment.comment_id}
              className="rounded-lg bg-slate-50 p-4"
            >
              <div className="mb-2 flex items-center justify-between">
                <p className="font-semibold text-slate-900">{comment.author || 'Anonymous'}</p>
                <time className="text-xs text-slate-500">
                  {format(new Date(comment.created_at), 'MMM d, yyyy h:mm a')}
                </time>
              </div>
              <p className="text-slate-700">{comment.content}</p>
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-center text-slate-600">No comments yet. Be the first to share your thoughts!</p>
      )}
    </section>
  );
}
