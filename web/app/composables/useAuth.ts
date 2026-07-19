import type { LoginCredentials, SignupData } from '~/types'

/**
 * Composable for authentication operations
 * @module composables/useAuth
 */

/**
 * Use authentication composable
 * @returns {object} Authentication methods and state
 * @example
 * ```typescript
 * const { login, signup, logout, isAuthenticated } = useAuth();
 * await login({ email: 'user@example.com', password: 'password' });
 * ```
 */
export function useAuth() {
  const userStore = useUserStore()
  const router = useRouter()
  const toast = useToast()

  /**
   * Handle login
   * @param {LoginCredentials} credentials - Login credentials
   * @returns {Promise<void>} Promise that resolves when login is complete
   */
  const login = async (credentials: LoginCredentials): Promise<void> => {
    try {
      await userStore.login(credentials)
      router.push('/dashboard')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Login failed')
      throw error
    }
  }

  /**
   * Handle signup — a brand new account goes through the setup wizard first.
   * @param {SignupData} data - Signup data
   * @returns {Promise<void>} Promise that resolves when signup is complete
   */
  const signup = async (data: SignupData): Promise<void> => {
    try {
      await userStore.signup(data)
      router.push('/configuration')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Signup failed')
      throw error
    }
  }

  /**
   * Handle logout
   * @returns {void}
   */
  const logout = (): void => {
    userStore.logout()
    toast.success('Logged out successfully')
    router.push('/login')
  }

  return {
    login,
    signup,
    logout,
    isAuthenticated: computed(() => userStore.isAuthenticated),
    isLoading: computed(() => userStore.isLoading),
    user: computed(() => userStore.user),
  }
}
