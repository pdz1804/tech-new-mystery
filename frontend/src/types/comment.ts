/**
 * Comment types.
 */

export interface CommentResponse {
  comment_id: string;
  user_id: string;
  content: string;
  created_at: string;
}

export interface CommentListResponse {
  success: boolean;
  data: CommentResponse[];
  meta: {
    page: number;
    limit: number;
    total: number | null;
  };
}
