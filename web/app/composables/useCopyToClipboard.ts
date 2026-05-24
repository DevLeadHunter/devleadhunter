/**
 * Copy text to the clipboard with toast feedback.
 */
export function useCopyToClipboard() {
  const toast = useToast()
  const copied: Ref<boolean> = ref(false)

  /**
   * Copy the given text to the clipboard.
   */
  async function copy(text: string): Promise<void> {
    if (!import.meta.client || !text) {
      return
    }

    try {
      await navigator.clipboard.writeText(text)
      copied.value = true
      toast.success('Link copied to clipboard')
      window.setTimeout((): void => {
        copied.value = false
      }, 2000)
    } catch {
      toast.error('Failed to copy link')
    }
  }

  return { copy, copied }
}
