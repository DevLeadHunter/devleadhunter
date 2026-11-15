import type { ComputedRef } from 'vue'
import type { UseModuleNavigationReturn } from '~/types/Composables'
import type { UiMobileTabBarNavigation } from '~/types/UiMobileTabBar'
import type {
  DashboardModuleSidebarCounter,
  UiSidebarCounter,
  UiSidebarCounterKey,
  UiSidebarGroup,
  UiSidebarLink,
} from '~/types/UiSidebar'
import { computed } from 'vue'
import { PROSPECT_SEARCH_PENDING_LEADS_COUNTER_KEY } from '~/constants/prospectSearch'
import { useModuleStore } from '~/stores/moduleStore'
import { useProspectSearchStore } from '~/stores/prospectSearch'
import { DashboardModuleRegistry } from '~/utils/dashboardModuleRegistry'
import { ModuleNavigation } from '~/utils/moduleNavigation'

/**
 * The navigation of the module the user has open: the sidebar, the bottom bar and the palette read the same menu.
 * @returns The menu's groups, the module's own settings links, the counters of its links and the bottom bar.
 */
export function useModuleNavigation(): UseModuleNavigationReturn {
  const moduleStore: ReturnType<typeof useModuleStore> = useModuleStore()

  // The dashboard layout already follows the searches: the pending count is read, never fetched, here.
  const prospectSearchStore: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()

  const navGroups: ComputedRef<UiSidebarGroup[]> = computed((): UiSidebarGroup[] => moduleStore.activeModule.navGroups)

  const moduleSettingsLinks: ComputedRef<UiSidebarLink[]> = computed(
    (): UiSidebarLink[] => DashboardModuleRegistry.find(moduleStore.activeKey)?.settingsLinks ?? [],
  )

  const counters: ComputedRef<Record<UiSidebarCounterKey, UiSidebarCounter>> = computed(
    (): Record<UiSidebarCounterKey, UiSidebarCounter> => {
      const pendingLeadCount: number = prospectSearchStore.pendingCount
      const moduleCounters: Record<UiSidebarCounterKey, UiSidebarCounter> = Object.fromEntries(
        (DashboardModuleRegistry.find(moduleStore.activeKey)?.sidebarCounters ?? []).map(
          (counter: DashboardModuleSidebarCounter): [UiSidebarCounterKey, UiSidebarCounter] => [
            counter.key,
            counter.read(),
          ],
        ),
      )
      return {
        [PROSPECT_SEARCH_PENDING_LEADS_COUNTER_KEY]: {
          count: pendingLeadCount,
          description: pendingLeadCount > 1 ? `${pendingLeadCount} leads à valider` : '1 lead à valider',
        },
        ...moduleCounters,
      }
    },
  )

  const tabBar: ComputedRef<UiMobileTabBarNavigation> = computed(
    (): UiMobileTabBarNavigation => ModuleNavigation.buildTabBar(moduleStore.activeModule),
  )

  return { navGroups, moduleSettingsLinks, counters, tabBar }
}
