import type { UseAuthReturn, UseToastReturn } from '~/types/Composables'
import type { LoginCredentials, SignupPayload } from '~/types'
import { useToast } from '~/composables/useToast'

/**
 * Auth facade over `useUserStore` — handles navigation and toasts after login/signup/logout.
 * @returns Store-backed auth actions and reactive session state.
 */
export function useAuth(): UseAuthReturn {
  const userStore: ReturnType<typeof useUserStore> = useUserStore()
  const router: ReturnType<typeof useRouter> = useRouter()
  const toast: UseToastReturn = useToast()

  /**
   * Log in and redirect to the dashboard.
   * @param credentials - Email and password.
   */
  const login: (credentials: LoginCredentials) => Promise<void> = async (
    credentials: LoginCredentials,
  ): Promise<void> => {
    try {
      await userStore.login(credentials)
      router.push('/dashboard')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Login failed')
      throw error
    }
  }

  /**
   * Sign up and redirect to the setup wizard.
   * @param data - Registration fields.
   */
  const signup: (data: SignupPayload) => Promise<void> = async (data: SignupPayload): Promise<void> => {
    try {
      await userStore.signup(data)
      router.push('/configuration')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Signup failed')
      throw error
    }
  }

  /** Log out, toast, and redirect to the login page. */
  const logout: () => void = (): void => {
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
