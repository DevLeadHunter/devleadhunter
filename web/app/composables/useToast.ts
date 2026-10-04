import type { ToastAction, ToastCallOptions, UseToastReturn } from '~/types/Composables'
import type { Ref } from 'vue'

/** Toast queue shared between `useToast` callers and `UiToastHost`. */

/** Visual family of a toast. */
export type ToastType = 'success' | 'error' | 'info' | 'warning'

/** One toast in the queue. */
export type ToastItem = {
  id: number
  message: string
  type: ToastType
  duration: number
  action?: ToastAction
}

const DEFAULT_DURATION_MS: number = 3500

const ERROR_DURATION_MS: number = 5000

const TOAST_WITH_BUTTON_DURATION_MS: number = 7000

let nextToastId: number = 1

/**
 * Reactive toast queue shared between callers and the host component.
 * @returns The shared queue state.
 */
function useToastQueue(): Ref<ToastItem[]> {
  return useState('app-toasts', (): ToastItem[] => [])
}

/**
 * Toast notification API (kept stable: `success` / `error` / `info` / `warning`).
 * @returns Toast methods.
 */
export function useToast(): UseToastReturn {
  const queue: Ref<ToastItem[]> = useToastQueue()

  /**
   * Choose how long a toast stays on screen.
   * @param type - Visual family of the toast.
   * @param options - Optional button and auto-dismiss duration.
   * @returns The duration asked for, else the one of a toast with a button, of an error, or the default one.
   */
  function resolveDuration(type: ToastType, options: ToastCallOptions): number {
    if (options.duration !== undefined) return options.duration
    if (options.action) return TOAST_WITH_BUTTON_DURATION_MS
    if (type === 'error') return ERROR_DURATION_MS
    return DEFAULT_DURATION_MS
  }

  /**
   * Push a toast into the queue (client only — SSR renders nothing).
   * @param message - Text shown to the user.
   * @param type - Visual family of the toast.
   * @param options - Optional button and auto-dismiss duration.
   */
  function showToast(message: string, type: ToastType, options: ToastCallOptions = {}): void {
    if (import.meta.server || !import.meta.client) {
      return
    }
    const duration: number = resolveDuration(type, options)
    queue.value = [...queue.value, { id: nextToastId++, message, type, duration, action: options.action }]
  }

  return {
    success: (message: string, options?: ToastCallOptions): void => showToast(message, 'success', options),
    error: (message: string, options?: ToastCallOptions): void => showToast(message, 'error', options),
    info: (message: string, options?: ToastCallOptions): void => showToast(message, 'info', options),
    warning: (message: string, options?: ToastCallOptions): void => showToast(message, 'warning', options),
  }
}

/**
 * Host-side API: the shared queue and the dismiss action.
 * @returns Queue state + dismiss.
 */
export function useToastHost(): { toasts: Ref<ToastItem[]>; dismiss: (id: number) => void } {
  const queue: Ref<ToastItem[]> = useToastQueue()

  /**
   * Remove a toast from the queue.
   * @param id - Toast identifier.
   */
  function dismiss(id: number): void {
    queue.value = queue.value.filter((toast: ToastItem): boolean => toast.id !== id)
  }

  return { toasts: queue, dismiss }
}
