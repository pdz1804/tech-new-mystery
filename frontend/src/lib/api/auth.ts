/**
 * Authentication API functions.
 */

import { apiClient } from './client';
import type { TokenResponse, UserResponse } from '@/types/auth';

export async function register(
  username: string,
  email: string,
  password: string
): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/register', {
    username,
    email,
    password,
  });
  return response.data;
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/login', { username, password });
  return response.data;
}

export async function getCurrentUser(): Promise<{ data: UserResponse }> {
  const response = await apiClient.get<UserResponse>('/auth/me');
  return { data: response.data };
}

export function logout(): void {
  // Logout is handled client-side (clear token and redirect)
  // This is a stub for API consistency
}
