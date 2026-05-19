/**
 * Article submission types.
 */

export interface Submission {
  submission_id: string;
  url: string;
  status: 'pending' | 'processing' | 'published' | 'failed';
  submitted_at: string;
  article_id?: string;
  error_message?: string;
}
