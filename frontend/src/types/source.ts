/**
 * News source types.
 */

export interface NewsSource {
  source_id: string;
  name: string;
  url: string;
  category: string | null;
  priority: number;
  enabled: boolean;
  created_at: string;
}
