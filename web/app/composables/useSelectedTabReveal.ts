import type { Ref } from 'vue'
import { nextTick, ref, watch } from 'vue'

/**
 * Keep the selected tab of a sideways-scrolling row in view, without moving the page.
 * @param readSelectedTabKey - Reads the key of the selected tab.
 * @param selectedTabSelector - How the selected tab is marked inside the row.
 * @returns The template ref to put on the row.
 */
export function useSelectedTabReveal(
  readSelectedTabKey: () => string,
  selectedTabSelector: string = '[aria-selected="true"]',
): Ref<HTMLElement | null> {
  const tabRowElement: Ref<HTMLElement | null> = ref(null)

  /**
   * Slide the row so the selected tab is fully visible.
   * @returns A promise resolved once the row is in place.
   */
  async function revealSelectedTab(): Promise<void> {
    await nextTick()
    const tabRow: HTMLElement | null = tabRowElement.value
    const selectedTab: HTMLElement | null = tabRow?.querySelector<HTMLElement>(selectedTabSelector) ?? null

    if (tabRow === null || selectedTab === null) {
      return
    }
    const rowBox: DOMRect = tabRow.getBoundingClientRect()
    const tabBox: DOMRect = selectedTab.getBoundingClientRect()

    if (tabBox.left < rowBox.left) {
      tabRow.scrollBy({ left: tabBox.left - rowBox.left, behavior: 'smooth' })
    } else if (tabBox.right > rowBox.right) {
      tabRow.scrollBy({ left: tabBox.right - rowBox.right, behavior: 'smooth' })
    }
  }

  watch([readSelectedTabKey, (): HTMLElement | null => tabRowElement.value], (): void => {
    revealSelectedTab()
  })

  return tabRowElement
}
