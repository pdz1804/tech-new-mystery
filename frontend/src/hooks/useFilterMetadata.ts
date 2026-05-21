import { useQuery } from '@tanstack/react-query';

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
      const response = await fetch('/api/v1/articles/filters');
      if (!response.ok) {
        throw new Error('Failed to fetch filter metadata');
      }
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
  });
}
