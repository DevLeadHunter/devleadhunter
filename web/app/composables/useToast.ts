/**
 * Toast notification composable
 * @module composables/useToast
 */

interface ToastOptions {
  duration?: number
  type?: 'success' | 'error' | 'info' | 'warning'
}

/**
 * Use toast notification
 * @returns {object} Toast methods
 * @example
 * ```typescript
 * const toast = useToast();
 * toast.success('Operation successful');
 * toast.error('Operation failed');
 * ```
 */
export function useToast() {
  const showToast = (message: string, options: ToastOptions = {}) => {
    // Skip on server-side rendering
    if (import.meta.server || !import.meta.client) {
      return
    }

    // This is a simplified implementation
    // In production, you'd use a proper toast library like vue-toastification

    const { type = 'info', duration = 3000 } = options

    // Create toast element
    const toast = document.createElement('div')
    toast.className = `fixed bottom-4 right-4 px-5 py-4 rounded shadow-xl z-50 border text-sm ${
      type === 'success'
        ? 'bg-[#2BAD5F] text-white border-[#2BAD5F]'
        : type === 'error'
          ? 'bg-[#DC4747] text-white border-[#DC4747]'
          : type === 'warning'
            ? 'bg-[#F8D57E] text-[#050505] border-[#F8D57E]'
            : 'bg-[#1a1a1a] text-[#f9f9f9] border-[#30363d]'
    }`
    toast.style.borderRadius = '4px'
    toast.style.maxWidth = '400px'
    toast.textContent = message

    document.body.appendChild(toast)

    // Remove toast after duration
    setTimeout(() => {
      toast.remove()
    }, duration)
  }

  return {
    success: (message: string) => showToast(message, { type: 'success' }),
    error: (message: string) => showToast(message, { type: 'error' }),
    info: (message: string) => showToast(message, { type: 'info' }),
    warning: (message: string) => showToast(message, { type: 'warning' }),
  }
}
