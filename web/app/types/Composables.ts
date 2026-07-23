import type { ComputedRef, Ref } from 'vue'
import type { LoginCredentials, Prospect, SignupPayload, User } from '~/types'
import type {
  ScrapingJobHydrationPayload,
  ScrapingJobProgressState,
  ScrapingJobStreamHandlers,
} from '~/composables/useScrapingJobStream'

export type UseAuthReturn = {
  login: (credentials: LoginCredentials) => Promise<void>
  signup: (payload: SignupPayload) => Promise<void>
  logout: () => void
  isAuthenticated: ComputedRef<boolean>
  isLoading: ComputedRef<boolean>
  user: ComputedRef<User | null>
}

export type UseCopyToClipboardReturn = {
  copy: (text: string) => Promise<void>
  copied: Ref<boolean>
}

export type UseDesktopRuntimeReturn = {
  isDesktopApp: ComputedRef<boolean>
  isLocalDev: boolean
  isDesktopDev: ComputedRef<boolean>
  isProdDesktop: ComputedRef<boolean>
  syncDevDatabaseFromProd: () => Promise<string>
}

export type UseOpenExternalUrlReturn = {
  openExternalUrl: (url: string) => Promise<void>
}

export type UseScrapingJobStreamReturn = {
  logs: Ref<string[]>
  prospects: Ref<Prospect[]>
  progress: Ref<ScrapingJobProgressState>
  skippedDuplicates: Ref<number>
  isConnected: Ref<boolean>
  connect: (jobId: string, token: string, streamHandlers?: ScrapingJobStreamHandlers) => void
  disconnect: () => void
  hydrateFromJob: (job: ScrapingJobHydrationPayload) => void
  reset: () => void
}

export type UseToastReturn = {
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
  warning: (message: string) => void
}
