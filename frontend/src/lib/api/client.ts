/**
 * Axios instance for API calls with automatic auth header injection.
 * This is the single source of truth for all API requests.
 */

import axios from 'axios';
import { useAuthStore } from '@/lib/stores/authStore';

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? '/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 180_000, // 3 minutes for long-running operations like AI processing
});

// Request interceptor: add auth token
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle auth errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().clearAuth();
    }
    return Promise.reject(error);
  }
);
