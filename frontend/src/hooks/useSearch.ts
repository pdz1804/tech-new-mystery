/**
 * Hooks for searching articles.
 */

import { useQuery } from '@tanstack/react-query';
import { searchKeys } from '@/lib/queryKeys';
import { searchArticles, type SearchParams } from '@/lib/api/search';

export function useSearchArticles(params: SearchParams, enabled: boolean = true) {
  return useQuery({
    queryKey: searchKeys.results(params.q),
    queryFn: () => searchArticles(params),
    staleTime: 1000 * 60 * 2,
    enabled: enabled && !!params.q,
  });
}
