/**
 * Active product module of the dashboard shell.
 *
 * The module switcher (top-left of the sidebar) writes here; the sidebar reads it to swap its
 * whole navigation. The choice persists per browser so a reload keeps the same module.
 */
import type { ComputedRef, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import type { EnabledProductModule } from '~/types/ProductModule'
import type { DashboardModuleDefinition, DlhModule, DlhModuleKey } from '~/types/UiSidebar'
import { WEBSITES_MODULE_KEY } from '~/constants/productModules'
import { ProductModuleService } from '~/services/productModuleService'
import { DashboardModuleRegistry } from '~/utils/dashboardModuleRegistry'
import { DEFAULT_MODULE_KEY, WEBSITES_DASHBOARD_MODULE } from '~/utils/dashboardModules'
import { ModuleNavigation } from '~/utils/moduleNavigation'

const STORAGE_KEY: string = 'dlh-active-module'

/**
 * Read the persisted module key (client-only, failure-safe).
 * @returns The stored key, or null when nothing is stored or the storage is unreadable.
 */
function readStoredModuleKey(): DlhModuleKey | null {
  if (!import.meta.client) {
    return null
  }
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

/**
 * Persist the module choice, or forget it (best-effort).
 * @param key - The module to remember, or null to forget the stored one.
 */
function writeStoredModuleKey(key: DlhModuleKey | null): void {
  if (!import.meta.client) {
    return
  }
  try {
    if (key === null) {
      localStorage.removeItem(STORAGE_KEY)
    } else {
      localStorage.setItem(STORAGE_KEY, key)
    }
  } catch {
    // Persistence is best-effort — the in-memory choice still applies for this session.
  }
}

/**
 * A registered module as the switcher lists it.
 * @param definition - The module a layer registered.
 * @returns Its switcher entry.
 */
function toSwitcherEntry(definition: DashboardModuleDefinition): DlhModule {
  return {
    key: definition.key,
    label: definition.label,
    icon: definition.icon,
    locked: false,
    home: definition.home,
    primaryCta: definition.primaryCta,
    navGroups: ModuleNavigation.removeWebsitesDashboardLink(definition.navGroups),
  }
}

// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useModuleStore = defineStore('module', () => {
  const activeKey: Ref<DlhModuleKey> = ref(DEFAULT_MODULE_KEY)

  /** The modules the API lists as switched on; null until it answered. */
  const enabledModules: Ref<EnabledProductModule[] | null> = ref(null)

  const enabledModuleKeys: ComputedRef<DlhModuleKey[] | null> = computed(
    (): DlhModuleKey[] | null =>
      enabledModules.value?.map((module: EnabledProductModule): DlhModuleKey => module.key) ?? null,
  )

  /** The request under way for the enabled modules, shared by every caller. */
  let enabledModulesRequest: Promise<void> | null = null

  let hasReadStoredModule: boolean = false

  /**
   * Whether a module's drawers, blocks and settings show: a registered module does unless the API lists it as off.
   * @param key - The module key.
   * @returns True when the module can be used.
   */
  function isModuleUsable(key: DlhModuleKey): boolean {
    if (key === WEBSITES_MODULE_KEY) {
      return true
    }

    if (DashboardModuleRegistry.find(key) === null) {
      return false
    }
    return enabledModuleKeys.value === null || enabledModuleKeys.value.includes(key)
  }

  /**
   * What the API says of a module switched on.
   * @param key - The module key.
   * @returns The module, or undefined while the API has not answered or does not list it.
   */
  function findEnabledModule(key: DlhModuleKey): EnabledProductModule | undefined {
    return enabledModules.value?.find((module: EnabledProductModule): boolean => module.key === key)
  }

  /**
   * Whether a module has email templates of its own (the websites module always does).
   * @param key - The module key.
   * @returns What the API says; true while it has not answered, so the pages show as they always did.
   */
  function hasEmailTemplates(key: DlhModuleKey): boolean {
    if (key === WEBSITES_MODULE_KEY) {
      return true
    }
    return findEnabledModule(key)?.has_email_templates ?? true
  }

  /**
   * Whether a module has SMS templates of its own (the websites module always does).
   * @param key - The module key.
   * @returns What the API says; true while it has not answered, so the pages show as they always did.
   */
  function hasSmsTemplates(key: DlhModuleKey): boolean {
    if (key === WEBSITES_MODULE_KEY) {
      return true
    }
    return findEnabledModule(key)?.has_sms_templates ?? true
  }

  /**
   * Whether the SMS settings page of a module only names its sender: the 30-day relance is the websites module's.
   * @param key - The module key.
   * @returns True for another module than the websites one that has SMS templates.
   */
  function isSmsPageLimitedToSenderName(key: DlhModuleKey): boolean {
    return key !== WEBSITES_MODULE_KEY && hasSmsTemplates(key)
  }

  /**
   * Whether the switcher lists a module: usable and confirmed by the API, or already active while the API is silent.
   * @param key - The module key.
   * @returns True when the switcher shows it.
   */
  function isListedInSwitcher(key: DlhModuleKey): boolean {
    if (!isModuleUsable(key)) {
      return false
    }
    return key === WEBSITES_MODULE_KEY || enabledModuleKeys.value !== null || key === activeKey.value
  }

  const availableModules: ComputedRef<DlhModule[]> = computed((): DlhModule[] => [
    WEBSITES_DASHBOARD_MODULE,
    ...DashboardModuleRegistry.list()
      .filter((definition: DashboardModuleDefinition): boolean => isListedInSwitcher(definition.key))
      .map(toSwitcherEntry),
  ])

  const activeModule: ComputedRef<DlhModule> = computed(
    (): DlhModule =>
      availableModules.value.find((module: DlhModule): boolean => module.key === activeKey.value) ??
      WEBSITES_DASHBOARD_MODULE,
  )

  /**
   * Whether a key names a module the dashboard knows (the websites module or a registered one).
   * @param key - The key to test.
   * @returns True when the dashboard can show that module.
   */
  function isKnownModule(key: DlhModuleKey): boolean {
    return key === WEBSITES_MODULE_KEY || DashboardModuleRegistry.find(key) !== null
  }

  /** Fall back to the websites module when the active one is not available any more, and forget it. */
  function dropUnavailableActiveModule(): void {
    if (isModuleUsable(activeKey.value)) {
      return
    }
    activeKey.value = DEFAULT_MODULE_KEY
    writeStoredModuleKey(null)
  }

  /** Restore the persisted module (called once on the client after hydration). */
  function initFromStorage(): void {
    if (!import.meta.client || hasReadStoredModule) {
      return
    }
    hasReadStoredModule = true
    const stored: DlhModuleKey | null = readStoredModuleKey()
    const isStoredUsable: boolean =
      stored !== null &&
      isKnownModule(stored) &&
      (enabledModuleKeys.value === null || stored === WEBSITES_MODULE_KEY || enabledModuleKeys.value.includes(stored))
    activeKey.value = isStoredUsable && stored !== null ? stored : DEFAULT_MODULE_KEY
  }

  /**
   * Switch the active module and persist the choice.
   * @param key - The module to activate (ignored when locked, unknown or switched off).
   */
  function setModule(key: DlhModuleKey): void {
    if (!isKnownModule(key)) {
      return
    }
    if (key !== WEBSITES_MODULE_KEY && enabledModuleKeys.value !== null && !enabledModuleKeys.value.includes(key)) {
      return
    }
    activeKey.value = key
    writeStoredModuleKey(key)
  }

  /**
   * Ask the API which modules are on, then drop an active module that is not.
   * @returns A promise resolved once the answer is applied (an unreachable API leaves the state as it was).
   */
  async function loadEnabledModules(): Promise<void> {
    try {
      enabledModules.value = await ProductModuleService.listEnabled()
    } catch {
      // The API could not tell: the registered modules stay as they are until the next load.
    }
  }

  /**
   * Load the enabled modules once (every caller shares the same request).
   * @returns A promise resolved once they are known, or the attempt failed.
   */
  function ensureEnabledModulesLoaded(): Promise<void> {
    if (enabledModules.value !== null) {
      return Promise.resolve()
    }
    enabledModulesRequest ??= loadEnabledModules().finally((): void => {
      enabledModulesRequest = null
    })
    return enabledModulesRequest
  }

  /**
   * Reload the enabled modules (after the super admin switched one).
   * @returns A promise resolved once the new state is applied.
   */
  async function refreshEnabledModules(): Promise<void> {
    await loadEnabledModules()
  }

  /**
   * Whether a module is switched on, for the guards of its pages.
   * @param key - The module key.
   * @returns True when the API lists it as on, or when the API could not be asked (its own routes then decide).
   */
  async function isModuleEnabled(key: DlhModuleKey): Promise<boolean> {
    if (key === WEBSITES_MODULE_KEY) {
      return true
    }
    await ensureEnabledModulesLoaded()
    return enabledModuleKeys.value === null || enabledModuleKeys.value.includes(key)
  }

  watch(enabledModuleKeys, (): void => {
    dropUnavailableActiveModule()
  })

  return {
    activeKey,
    enabledModuleKeys,
    availableModules,
    switcherModules: availableModules,
    activeModule,
    isModuleUsable,
    hasEmailTemplates,
    hasSmsTemplates,
    isSmsPageLimitedToSenderName,
    initFromStorage,
    setModule,
    ensureEnabledModulesLoaded,
    refreshEnabledModules,
    isModuleEnabled,
  }
})
