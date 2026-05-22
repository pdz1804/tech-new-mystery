/**
 * News sources API functions.
 */

import { apiClient } from './client';

interface NewsSource {
  id: string;
  name: string;
  url?: string;
}

export async function fetchSources(): Promise<{ data: NewsSource[] }> {
  const response = await apiClient.get<{ data: NewsSource[] }>('/sources');
  return response.data;
}
