/**
 * Active product module of the dashboard shell.
 *
 * The module switcher (top-left of the sidebar) writes here; the sidebar reads it to swap
 * its whole navigation. The choice persists per browser so a reload keeps the same module.
 */
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { DlhModule, DlhModuleKey } from '~/types/UiSidebar'
import { DASHBOARD_MODULES, DEFAULT_MODULE_KEY } from '~/utils/dashboardModules'

const STORAGE_KEY: string = 'dlh-active-module'

/**
 * Read the persisted module key, falling back to the default (client-only, failure-safe).
 * @returns The stored module key, or the default.
 */
function readStoredModuleKey(): DlhModuleKey {
  if (!import.meta.client) return DEFAULT_MODULE_KEY
  try {
    const stored: string | null = localStorage.getItem(STORAGE_KEY)
    const match: DlhModule | undefined = DASHBOARD_MODULES.find(
      (module: DlhModule): boolean => !module.locked && module.key === stored,
    )
    return match?.key ?? DEFAULT_MODULE_KEY
  } catch {
    return DEFAULT_MODULE_KEY
  }
}

// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useModuleStore = defineStore('module', () => {
  const activeKey: Ref<DlhModuleKey> = ref(DEFAULT_MODULE_KEY)

  const activeModule: ComputedRef<DlhModule> = computed(
    (): DlhModule =>
      DASHBOARD_MODULES.find((module: DlhModule): boolean => module.key === activeKey.value) ?? DASHBOARD_MODULES[0]!,
  )

  /** Restore the persisted module (called once on the client after hydration). */
  function initFromStorage(): void {
    activeKey.value = readStoredModuleKey()
  }

  /**
   * Switch the active module and persist the choice.
   * @param key - The module to activate (ignored when locked).
   */
  function setModule(key: DlhModuleKey): void {
    const target: DlhModule | undefined = DASHBOARD_MODULES.find((module: DlhModule): boolean => module.key === key)
    if (!target || target.locked) return
    activeKey.value = key
    if (!import.meta.client) return
    try {
      localStorage.setItem(STORAGE_KEY, key)
    } catch {
      // Persistence is best-effort — the in-memory choice still applies for this session.
    }
  }

  return { activeKey, activeModule, initFromStorage, setModule }
})
