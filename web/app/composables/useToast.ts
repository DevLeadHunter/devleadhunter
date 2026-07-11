import type { Ref } from 'vue'

/**
 * Toast notifications — reactive queue rendered by `UiToastHost` (mounted once
 * in app.vue), styled on the Atelier design tokens (`--app-*`) in both themes.
 * @module composables/useToast
 */

/** Visual family of a toast. */
export type ToastType = 'success' | 'error' | 'info' | 'warning'

/** One toast in the queue. */
export interface ToastItem {
  id: number
  message: string
  type: ToastType
  /** Auto-dismiss delay in ms. */
  duration: number
}

interface ToastOptions {
  duration?: number
  type?: ToastType
}

let nextToastId: number = 1

/**
 * Reactive toast queue shared between callers and the host component.
 * @returns The shared queue state.
 */
function useToastQueue(): Ref<ToastItem[]> {
  return useState<ToastItem[]>('app-toasts', (): ToastItem[] => [])
}

/**
 * Toast notification API (kept stable: `success` / `error` / `info` / `warning`).
 * @returns Toast methods.
 * @example
 * ```typescript
 * const toast = useToast();
 * toast.success('Opération réussie');
 * toast.error('Une erreur est survenue');
 * ```
 */
export function useToast() {
  const queue: Ref<ToastItem[]> = useToastQueue()

  /**
   * Push a toast into the queue (client only — SSR renders nothing).
   * @param message - Text shown to the user.
   * @param options - Type + auto-dismiss duration.
   */
  const showToast = (message: string, options: ToastOptions = {}): void => {
    if (import.meta.server || !import.meta.client) {
      return
    }
    const { type = 'info', duration = 3500 } = options
    queue.value = [...queue.value, { id: nextToastId++, message, type, duration }]
  }

  return {
    success: (message: string): void => showToast(message, { type: 'success' }),
    error: (message: string): void => showToast(message, { type: 'error', duration: 5000 }),
    info: (message: string): void => showToast(message, { type: 'info' }),
    warning: (message: string): void => showToast(message, { type: 'warning' }),
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
