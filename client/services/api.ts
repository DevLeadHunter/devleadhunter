import type { ApiResponse } from '~/types';

/**
 * Base API service with common HTTP methods
 * @module services/api
 */

/**
 * Get the API base URL from runtime config
 * @returns {string} The API base URL
 */
function getBaseUrl(): string {
  const config = useRuntimeConfig();
  return config.public.apiBase;
}

/**
 * Make authenticated API request
 * @param {string} endpoint - API endpoint
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<T>} Response data
 * @throws {Error} If request fails
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const userStore = useUserStore();
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(userStore.token && { Authorization: `Bearer ${userStore.token}` }),
    ...options.headers
  };

  const response = await fetch(`${getBaseUrl()}${endpoint}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    let errorMessage = `API request failed: ${response.statusText}`;
    
    // Try to parse error message from response
    if (errorText) {
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || errorJson.message || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
    }
    
    throw new Error(errorMessage);
  }

  // Check if response has content
  const contentType = response.headers.get('content-type');
  const contentLength = response.headers.get('content-length');
  
  // For DELETE requests or responses with no content, return undefined
  if (contentLength === '0' || (options.method === 'DELETE' && !contentType?.includes('application/json'))) {
    // Try to get text to verify it's actually empty
    const text = await response.text().catch(() => '');
    if (!text || text.trim() === '') {
      return undefined as T;
    }
    // If there's unexpected content, try to parse it
    try {
      return JSON.parse(text);
    } catch {
      return undefined as T;
    }
  }

  // For normal responses, check if body exists before parsing
  const text = await response.text();
  if (!text || text.trim() === '') {
    return undefined as T;
  }

  try {
    return JSON.parse(text);
  } catch (error) {
    // If it's not JSON, return the text
    return text as T;
  }
}

/**
 * API service with common HTTP methods
 */
export const api = {
  /**
   * GET request
   * @param {string} endpoint - API endpoint
   * @param {object} options - Optional params
   * @returns {Promise<T>} Response data
   */
  get<T>(endpoint: string, options?: { params?: any }): Promise<T> {
    let url = endpoint;
    if (options?.params) {
      const params = new URLSearchParams();
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
          params.append(key, String(value));
        }
      });
      const queryString = params.toString();
      if (queryString) {
        url += `?${queryString}`;
      }
    }
    return request<T>(url, { method: 'GET' });
  },

  /**
   * POST request
   * @param {string} endpoint - API endpoint
   * @param {any} data - Request body
   * @returns {Promise<T>} Response data
   */
  post<T>(endpoint: string, data: any): Promise<T> {
    return request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  /**
   * PUT request
   * @param {string} endpoint - API endpoint
   * @param {any} data - Request body
   * @returns {Promise<T>} Response data
   */
  put<T>(endpoint: string, data: any): Promise<T> {
    return request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  },

  /**
   * PATCH request
   * @param {string} endpoint - API endpoint
   * @param {any} data - Request body
   * @returns {Promise<T>} Response data
   */
  patch<T>(endpoint: string, data: any): Promise<T> {
    return request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  },

  /**
   * DELETE request
   * @param {string} endpoint - API endpoint
   * @returns {Promise<T>} Response data
   */
  delete<T>(endpoint: string): Promise<T> {
    return request<T>(endpoint, { method: 'DELETE' });
  }
};


