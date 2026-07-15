/**
 * Base API service with common HTTP methods
 * @module services/api
 */

/**
 * Get the API base URL from runtime config
 * @returns {string} The API base URL
 */
function getBaseUrl(): string {
  const config = useRuntimeConfig()
  return config.public.apiBase
}

/**
 * Make authenticated API request
 * @param endpoint - API endpoint
 * @param options - Fetch options
 * @returns Response data
 * @throws {Error} If request fails
 */
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const userStore = useUserStore()

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(userStore.token && { Authorization: `Bearer ${userStore.token}` }),
    ...options.headers,
  }

  const response = await fetch(`${getBaseUrl()}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const errorText = await response.text().catch(() => '')
    let errorMessage = `API request failed: ${response.statusText}`

    // Try to parse error message from response
    if (errorText) {
      try {
        const errorJson = JSON.parse(errorText)
        errorMessage = errorJson.detail || errorJson.message || errorMessage
      } catch {
        errorMessage = errorText || errorMessage
      }
    }

    throw new Error(errorMessage)
  }

  // Check if response has content
  const contentType = response.headers.get('content-type')
  const contentLength = response.headers.get('content-length')

  // For DELETE requests or responses with no content, return undefined
  if (contentLength === '0' || (options.method === 'DELETE' && !contentType?.includes('application/json'))) {
    // Try to get text to verify it's actually empty
    const text = await response.text().catch(() => '')
    if (!text || text.trim() === '') {
      return undefined as T
    }
    // If there's unexpected content, try to parse it
    try {
      return JSON.parse(text)
    } catch {
      return undefined as T
    }
  }

  // For normal responses, check if body exists before parsing
  const text = await response.text()
  if (!text || text.trim() === '') {
    return undefined as T
  }

  try {
    return JSON.parse(text)
  } catch {
    return text as T
  }
}

/**
 * API service with common HTTP methods
 */
export const api = {
  /**
   * GET request
   * @param endpoint - API endpoint
   * @param options - Optional params
   * @returns Response data
   */
  get<T>(
    endpoint: string,
    options?: { params?: Record<string, string | number | boolean | null | undefined> },
  ): Promise<T> {
    let url = endpoint
    if (options?.params) {
      const params = new URLSearchParams()
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
          params.append(key, String(value))
        }
      })
      const queryString = params.toString()
      if (queryString) {
        url += `?${queryString}`
      }
    }
    return request<T>(url, { method: 'GET' })
  },

  /**
   * POST request
   * @param endpoint - API endpoint
   * @param data - Request body
   * @returns Response data
   */
  post<T>(endpoint: string, data: unknown): Promise<T> {
    return request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  /**
   * PUT request
   * @param endpoint - API endpoint
   * @param data - Request body
   * @returns Response data
   */
  put<T>(endpoint: string, data: unknown): Promise<T> {
    return request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  /**
   * PATCH request
   * @param endpoint - API endpoint
   * @param data - Request body
   * @returns Response data
   */
  patch<T>(endpoint: string, data: unknown): Promise<T> {
    return request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  },

  /**
   * DELETE request
   * @param endpoint - API endpoint
   * @returns Response data
   */
  delete<T>(endpoint: string): Promise<T> {
    return request<T>(endpoint, { method: 'DELETE' })
  },
}

type ApiFetchOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
}

/**
 * ofetch-style helper used by legacy services (campaigns, etc.).
 * @param endpoint - Path relative to `/api/v1` (e.g. `/campaigns`).
 * @param options - HTTP method and optional JSON body.
 * @returns Parsed JSON response body.
 */
export async function $api<T>(endpoint: string, options: ApiFetchOptions = {}): Promise<T> {
  const path: string = endpoint.startsWith('/api/')
    ? endpoint
    : `/api/v1${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`
  const method: ApiFetchOptions['method'] = options.method ?? 'GET'

  switch (method) {
    case 'GET':
      return api.get<T>(path)
    case 'POST':
      return api.post<T>(path, options.body)
    case 'PUT':
      return api.put<T>(path, options.body)
    case 'PATCH':
      return api.patch<T>(path, options.body)
    case 'DELETE':
      return api.delete<T>(path)
    default:
      return api.get<T>(path)
  }
}
