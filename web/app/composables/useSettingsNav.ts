import type { ComputedRef, Ref } from 'vue'
import { WEBSITES_MODULE_KEY } from '~/constants/productModules'
import { SETTINGS_NAV_GROUPS } from '~/constants/settingsNav'
import type { SettingsNavGroup, SettingsNavLink } from '~/types/SettingsNav'
import { useModuleStore } from '~/stores/moduleStore'
import { PresenterVideoAdapterRegistry } from '~/utils/presenterVideoAdapterRegistry'
import { SettingsNavRegistry } from '~/utils/settingsNavRegistry'
import { isPlatformAdmin, isSuperAdmin } from '~/utils/userRoles'

export type SettingsNav = {
  isAdmin: ComputedRef<boolean>
  isSuperAdmin: ComputedRef<boolean>
  showSettingsPanel: Ref<boolean>
  settingsGroups: ComputedRef<SettingsNavGroup[]>
  openSettingsPanel: () => void
  closeSettingsPanel: () => void
  isLinkActive: (path: string) => boolean
}

/**
 * Paramètres sub-panel state; auto-opens on settings routes.
 * @returns Panel state, the groups the user's role and open module show, and route helpers.
 */
export function useSettingsNav(): SettingsNav {
  const route: ReturnType<typeof useRoute> = useRoute()
  const userStore: ReturnType<typeof useUserStore> = useUserStore()
  const moduleStore: ReturnType<typeof useModuleStore> = useModuleStore()

  const isAdmin: ComputedRef<boolean> = computed((): boolean => isPlatformAdmin(userStore.user?.role))
  const isSuperAdminUser: ComputedRef<boolean> = computed((): boolean => isSuperAdmin(userStore.user?.role))
  const showSettingsPanel: Ref<boolean> = useState('settings-nav-open', (): boolean => false)

  const allSettingsGroups: ComputedRef<SettingsNavGroup[]> = computed((): SettingsNavGroup[] =>
    SettingsNavRegistry.groupsWith(SETTINGS_NAV_GROUPS, moduleStore.isModuleUsable),
  )

  const settingsGroups: ComputedRef<SettingsNavGroup[]> = computed((): SettingsNavGroup[] =>
    allSettingsGroups.value
      .filter((group: SettingsNavGroup): boolean => !group.adminOnly || isAdmin.value)
      .map(
        (group: SettingsNavGroup): SettingsNavGroup => ({
          ...group,
          entries: group.entries.filter(isEntryShown).map(renameEntryForActiveModule),
        }),
      )
      .filter((group: SettingsNavGroup): boolean => group.entries.length > 0),
  )

  const settingsPaths: ComputedRef<string[]> = computed((): string[] =>
    allSettingsGroups.value
      .flatMap((group: SettingsNavGroup): SettingsNavLink[] => group.entries)
      .map((entry: SettingsNavLink): string => entry.to),
  )

  /**
   * Whether the user's role may open a settings page.
   * @param entry - A settings page.
   * @returns False for an admin page the user's role does not reach.
   */
  function isAllowedByRole(entry: SettingsNavLink): boolean {
    if (entry.superAdminOnly) {
      return isSuperAdminUser.value
    }

    if (entry.adminOnly) {
      return isAdmin.value
    }
    return true
  }

  /**
   * Whether the module the user has open uses a settings page.
   * @param entry - A settings page.
   * @returns True for a shared page, for a page of the open module, and for a core page that module writes with.
   */
  function isUsedByActiveModule(entry: SettingsNavLink): boolean {
    const activeModuleKey: string = moduleStore.activeKey

    if (entry.ownerModuleKey) {
      return entry.ownerModuleKey === activeModuleKey
    }

    if (entry.requiredModuleFeature === 'email-templates') {
      return moduleStore.hasEmailTemplates(activeModuleKey)
    }

    if (entry.requiredModuleFeature === 'sms-templates') {
      return moduleStore.hasSmsTemplates(activeModuleKey)
    }

    if (entry.requiredModuleFeature === 'presenter-video') {
      return PresenterVideoAdapterRegistry.of(activeModuleKey) !== null
    }
    return true
  }

  /**
   * Whether the panel lists a settings page.
   * @param entry - A settings page.
   * @returns True when the open module uses it, and for the page being read, so the panel always shows where one is.
   */
  function isEntryShown(entry: SettingsNavLink): boolean {
    return isAllowedByRole(entry) && (isUsedByActiveModule(entry) || matchesPath(entry.to))
  }

  /**
   * Give a settings page the name it has in the open module.
   * @param entry - A settings page the panel lists.
   * @returns The page, renamed when another module than the websites one uses a reduced version of it.
   */
  function renameEntryForActiveModule(entry: SettingsNavLink): SettingsNavLink {
    const labelOutsideWebsitesModule: string | undefined = entry.labelOutsideWebsitesModule
    const isWebsitesModuleActive: boolean = moduleStore.activeKey === WEBSITES_MODULE_KEY

    if (labelOutsideWebsitesModule === undefined || isWebsitesModuleActive || !isUsedByActiveModule(entry)) {
      return entry
    }
    return { ...entry, label: labelOutsideWebsitesModule }
  }

  /**
   * Whether a route path matches the current route (exact or nested).
   * @param path - Route path to test.
   * @returns True when the current route is at or under `path`.
   */
  function matchesPath(path: string): boolean {
    return route.path === path || route.path.startsWith(`${path}/`)
  }

  const isSettingsRoute: ComputedRef<boolean> = computed((): boolean =>
    settingsPaths.value.some((path: string): boolean => matchesPath(path)),
  )

  watch(
    (): string => route.path,
    (): void => {
      if (isSettingsRoute.value) showSettingsPanel.value = true
    },
    { immediate: true },
  )

  /** Show the settings sub-panel instead of the main menu. */
  function openSettingsPanel(): void {
    showSettingsPanel.value = true
  }

  /** Return to the main sidebar menu. */
  function closeSettingsPanel(): void {
    showSettingsPanel.value = false
  }

  /**
   * Whether a sub-panel link matches the current route.
   * @param path - Link route path.
   * @returns True when the link is active.
   */
  function isLinkActive(path: string): boolean {
    return matchesPath(path)
  }

  return {
    isAdmin,
    isSuperAdmin: isSuperAdminUser,
    showSettingsPanel,
    settingsGroups,
    openSettingsPanel,
    closeSettingsPanel,
    isLinkActive,
  }
}
