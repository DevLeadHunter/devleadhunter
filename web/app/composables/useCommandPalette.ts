import type { Ref } from 'vue'

/**
 * Global Ctrl+K command palette open/close state.
 * @returns Palette visibility ref plus open/close/toggle helpers.
 */
export function useCommandPalette(): {
  isOpen: Ref<boolean>
  open: () => void
  close: () => void
  toggle: () => void
} {
  const isOpen: Ref<boolean> = useState('command-palette-open', (): boolean => false)

  /** Show the palette. */
  function open(): void {
    isOpen.value = true
  }

  /** Hide the palette. */
  function close(): void {
    isOpen.value = false
  }

  /** Flip the palette visibility. */
  function toggle(): void {
    isOpen.value = !isOpen.value
  }

  return { isOpen, open, close, toggle }
}
