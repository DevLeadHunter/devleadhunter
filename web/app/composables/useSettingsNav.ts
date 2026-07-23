import type { ComputedRef, Ref } from 'vue'
import { SETTINGS_NAV_GROUPS } from '~/constants/settingsNav'
import type { SettingsNavEntry, SettingsNavGroup, SettingsNavLink } from '~/types/SettingsNav'

export type SettingsNav = {
  isAdmin: ComputedRef<boolean>
  showSettingsPanel: Ref<boolean>
  settingsGroups: ComputedRef<SettingsNavGroup[]>
  openSettingsPanel: () => void
  closeSettingsPanel: () => void
  isLinkActive: (path: string) => boolean
}

/**
 * Paramètres sub-panel state; auto-opens on settings routes.
 * @returns Panel state, admin-filtered groups, and route helpers.
 */
export function useSettingsNav(): SettingsNav {
  const route: ReturnType<typeof useRoute> = useRoute()
  const userStore: ReturnType<typeof useUserStore> = useUserStore()

  const isAdmin: ComputedRef<boolean> = computed((): boolean => userStore.user?.role === 'ADMIN')
  const showSettingsPanel: Ref<boolean> = useState('settings-nav-open', (): boolean => false)

  const settingsGroups: ComputedRef<SettingsNavGroup[]> = computed((): SettingsNavGroup[] =>
    SETTINGS_NAV_GROUPS.filter((group: SettingsNavGroup): boolean => !group.adminOnly || isAdmin.value)
      .map(
        (group: SettingsNavGroup): SettingsNavGroup => ({
          ...group,
          entries: group.entries.filter((entry: SettingsNavEntry): boolean => !entry.adminOnly || isAdmin.value),
        }),
      )
      .filter((group: SettingsNavGroup): boolean => group.entries.length > 0),
  )

  const settingsPaths: ComputedRef<string[]> = computed((): string[] =>
    SETTINGS_NAV_GROUPS.flatMap((group: SettingsNavGroup): SettingsNavEntry[] => group.entries)
      .filter((entry: SettingsNavEntry): entry is SettingsNavLink => entry.kind === 'link')
      .map((entry: SettingsNavLink): string => entry.to),
  )

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

  return { isAdmin, showSettingsPanel, settingsGroups, openSettingsPanel, closeSettingsPanel, isLinkActive }
}
