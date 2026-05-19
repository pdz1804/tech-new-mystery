'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchArticleComments, createComment } from '@/lib/api/comments';
import { commentKeys } from '@/lib/queryKeys';
import { format } from 'date-fns';

interface CommentThreadProps {
  articleId: string;
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export function CommentThread({ articleId }: CommentThreadProps) {
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
    <motion.section
      variants={itemVariants}
      className="rounded-2xl bg-white p-8 border border-slate-200"
    >
      <h3 className="mb-8 text-2xl font-bold text-slate-900">Comments</h3>

      {/* Comment Form */}
      <form onSubmit={handleSubmit} className="mb-8">
        <textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Add your comment..."
          rows={4}
          className="w-full resize-none rounded-lg border border-slate-200 bg-white px-4 py-3 text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
        />
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          type="submit"
          disabled={!newComment.trim() || createCommentMutation.isPending}
          className="mt-3 rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-all hover:shadow-button-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {createCommentMutation.isPending ? 'Posting...' : 'Post Comment'}
        </motion.button>
      </form>

      {/* Comments List */}
      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse rounded-lg bg-slate-200 h-24" />
          ))}
        </div>
      ) : comments.length > 0 ? (
        <div className="space-y-4">
          {comments.map((comment: { comment_id: string; author?: string; created_at: string; content: string }) => (
            <motion.div
              key={comment.comment_id}
              variants={itemVariants}
              className="rounded-lg border border-slate-200 bg-slate-50 p-4"
            >
              <div className="mb-2 flex items-center justify-between">
                <p className="font-semibold text-slate-900">
                  {comment.author || 'Anonymous'}
                </p>
                <time className="text-xs text-slate-500">
                  {format(
                    new Date(comment.created_at),
                    'MMM d, yyyy h:mm a'
                  )}
                </time>
              </div>
              <p className="text-slate-700">{comment.content}</p>
            </motion.div>
          ))}
        </div>
      ) : (
        <p className="text-center text-slate-600">
          No comments yet. Be the first to share your thoughts!
        </p>
      )}
    </motion.section>
  );
}
