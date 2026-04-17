import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Create an authenticated API client
 * Automatically includes JWT token in Authorization header
 */
export function createApiClient(token?: string): AxiosInstance {
  const config: AxiosRequestConfig = {
    baseURL: API_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  if (token) {
    config.headers = {
      ...config.headers,
      Authorization: `Bearer ${token}`,
    };
  }

  return axios.create(config);
}

/**
 * API client for server-side requests
 * Use this in Server Components and API routes
 */
export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Add authentication token to existing client
 */
export function setAuthToken(client: AxiosInstance, token: string) {
  client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
}

/**
 * Remove authentication token from client
 */
export function clearAuthToken(client: AxiosInstance) {
  delete client.defaults.headers.common['Authorization'];
}
