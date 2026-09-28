import type { Ref } from 'vue'
import type { UseCopyToClipboardReturn, UseToastReturn } from '~/types/Composables'
import { ref } from 'vue'
import { useToast } from '~/composables/useToast'
import { ClipboardCopy } from '~/utils/clipboardCopy'

/**
 * Copy text to the clipboard with toast feedback.
 */
export function useCopyToClipboard(): UseCopyToClipboardReturn {
  const toast: UseToastReturn = useToast()
  const copied: Ref<boolean> = ref(false)

  /**
   * Copy the given text to the clipboard.
   * @param text - The text to copy.
   * @returns Whether the clipboard received the text.
   */
  async function copy(text: string): Promise<boolean> {
    if (!import.meta.client || !text) {
      return false
    }

    if (!(await ClipboardCopy.copyText(text))) {
      toast.error('Copie refusée par le navigateur.')
      return false
    }

    copied.value = true
    toast.success('Copié dans le presse-papiers.')
    window.setTimeout((): void => {
      copied.value = false
    }, 2000)
    return true
  }

  return { copy, copied }
}
