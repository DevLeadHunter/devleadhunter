import type { User, LoginCredentials, SignupPayload, TokenResponse, ProfileUpdate } from '~/types'

/** Resolve the API base URL from runtime config. */
function getApiUrl(): string {
  const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
  return config.public.apiBase
}

/** Answers by which the API turns a token down: invalid or expired (401, 403), account deactivated (400). */
const TOKEN_REJECTION_STATUSES: number[] = [400, 401, 403]

/**
 * The API answered and refused the token, as opposed to an API out of reach (no network yet, a restart).
 */
export class TokenRejectedError extends Error {}

export class AuthService {
  /**
   * Login user
   * @param credentials - Login credentials
   * @returns Token response
   * @throws If login fails
   */
  static async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const response: Response = await fetch(`${getApiUrl()}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    })

    if (!response.ok) {
      const error: { detail: string } = await response.json().catch(() => ({ detail: 'Login failed' }))
      throw new Error(error.detail || 'Login failed')
    }

    return response.json()
  }

  /**
   * Signup new user
   * @param data - Signup data
   * @returns Created user
   * @throws If signup fails
   */
  static async signup(data: SignupPayload): Promise<User> {
    const response: Response = await fetch(`${getApiUrl()}/api/v1/auth/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error: { detail: string } = await response.json().catch(() => ({ detail: 'Signup failed' }))
      throw new Error(error.detail || 'Signup failed')
    }

    return response.json()
  }

  /**
   * Get current user information
   * @param token - JWT token
   * @returns Current user
   * @throws TokenRejectedError when the API refuses the token, Error when it cannot be reached
   */
  static async getCurrentUser(token: string): Promise<User> {
    const response: Response = await fetch(`${getApiUrl()}/api/v1/auth/me`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })

    if (TOKEN_REJECTION_STATUSES.includes(response.status)) {
      throw new TokenRejectedError('Token rejected')
    }
    if (!response.ok) {
      throw new Error('Failed to get current user')
    }

    return response.json()
  }

  /**
   * Trade a still valid token for a new one with the full lifetime again.
   * @param token - JWT token.
   * @returns The new token.
   * @throws TokenRejectedError when the API refuses the token, Error when it cannot be reached.
   */
  static async refreshToken(token: string): Promise<TokenResponse> {
    const response: Response = await fetch(`${getApiUrl()}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })

    if (TOKEN_REJECTION_STATUSES.includes(response.status)) {
      throw new TokenRejectedError('Token rejected')
    }
    if (!response.ok) {
      throw new Error('Failed to refresh the token')
    }

    return response.json()
  }

  /**
   * Mark the post-signup setup wizard (`/configuration`) as completed.
   * @param token - JWT token.
   * @returns The updated user.
   * @throws If the request fails.
   */
  static async completeOnboarding(token: string): Promise<User> {
    const response: Response = await fetch(`${getApiUrl()}/api/v1/auth/me/complete-onboarding`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const error: { detail: string } = await response.json().catch(() => ({ detail: 'Onboarding completion failed' }))
      throw new Error(error.detail || 'Onboarding completion failed')
    }

    return response.json()
  }

  /**
   * Update the current user's profile (name and/or email) server-side.
   * @param token - JWT token.
   * @param data - Fields to update (name and/or email).
   * @returns The updated user as returned by the API.
   * @throws If the update fails (e.g. email already registered).
   */
  static async updateProfile(token: string, data: ProfileUpdate): Promise<User> {
    const response: Response = await fetch(`${getApiUrl()}/api/v1/auth/me`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error: { detail: string } = await response.json().catch(() => ({ detail: 'Profile update failed' }))
      throw new Error(error.detail || 'Profile update failed')
    }

    return response.json()
  }
}
