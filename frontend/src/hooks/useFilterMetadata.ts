import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export interface FilterCategory {
  name: string;
  count: number;
}

export interface FilterMetadata {
  categories: FilterCategory[];
  sources: FilterCategory[];
}

/**
 * Hook to fetch dynamic filter metadata (category and source counts)
 * from the API. Results are cached for 5 minutes.
 */
export function useFilterMetadata() {
  return useQuery<{ success: boolean; data: FilterMetadata }>({
    queryKey: ['filterMetadata'],
    queryFn: async () => {
      const { data } = await apiClient.get('/articles/filters');
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
  });
}
