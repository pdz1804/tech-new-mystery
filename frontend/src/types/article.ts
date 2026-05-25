/**
 * Article types matching backend schemas.
 */

export interface ArticleResponse {
  article_id: string;
  title: string;
  slug: string;
  summary: string | null;
  original_url: string;
  source_id: string;
  category: string | null;
  categories?: string[];
  tags: string[];
  quality_score?: number | null;
  view_count: number;
  is_published: boolean;
  published_at: string | null;
  created_at: string;
}

export interface ArticleDetailResponse {
  success: boolean;
  data: ArticleResponse & {
    content: string;
    markdown_content: string | null;
    author: string | null;
    related_articles?: ArticleResponse[];
  };
}

export interface ArticleListResponse {
  success: boolean;
  data: ArticleResponse[];
  meta: {
    limit: number;
    last_key: string | null;
    page?: number;
    total?: number | null;
    count?: number;
  };
}

export interface ArticleListParams {
  category?: string;
  source_id?: string;
  page?: number;
  limit?: number;
  last_key?: string;
}
