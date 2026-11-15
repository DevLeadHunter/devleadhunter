<template>
  <!-- Comme GoupixDex : téléphone, deux onglets, le gros bouton ambré du module, deux onglets ; l'onglet ouvert passe
       en ambre. iPad : un onglet de plus de chaque côté, les libellés sous les icônes, et le bouton écrit son nom
       dans la barre. -->
  <nav
    class="standalone:max-lg:block standalone:pointer-coarse:block hidden shrink-0 border-t border-[var(--app-line)] bg-[var(--app-surface)] pt-1 pr-[env(safe-area-inset-right)] pb-[max(1.5rem,env(safe-area-inset-bottom))] pl-[env(safe-area-inset-left)]"
    aria-label="Navigation rapide"
  >
    <div class="mx-auto flex h-14 max-w-xl items-stretch md:max-w-3xl md:px-2">
      <UiMobileTabBarTab v-for="tab in tabsBeforeMainAction" :key="tab.to" v-bind="tab" />

      <div v-if="mainAction" class="flex w-22 shrink-0 items-center justify-center md:w-auto md:px-2">
        <NuxtLink
          :to="mainAction.to"
          :title="mainAction.label"
          :aria-label="mainAction.label"
          :aria-current="isMainActionPageOpen ? 'page' : undefined"
          class="flex size-15 -translate-y-2.5 items-center justify-center gap-2 rounded-full bg-[var(--app-accent)] text-[#1b1508] transition-opacity [-webkit-tap-highlight-color:transparent] active:opacity-80 md:h-11 md:w-auto md:translate-y-0 md:px-5"
        >
          <UIcon :name="mainAction.icon" class="size-7 md:size-5" />
          <span class="hidden text-sm font-semibold whitespace-nowrap md:inline">{{ mainAction.label }}</span>
        </NuxtLink>
      </div>

      <UiMobileTabBarTab v-for="tab in tabsAfterMainAction" :key="tab.to" v-bind="tab" />
    </div>
  </nav>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import type { RouteLocationNormalizedLoaded } from 'vue-router'
import type { UseModuleNavigationReturn } from '~/types/Composables'
import type { UiMobileTabBarLink } from '~/types/UiMobileTabBar'
import type { UiMobileTabBarTabProps } from '~/types/UiMobileTabBarTab'
import type { DlhModulePrimaryCta, UiSidebarCounter, UiSidebarCounterKey } from '~/types/UiSidebar'
import { useMediaQuery } from '@vueuse/core'
import { computed, onBeforeUnmount, watch } from 'vue'
import { MOBILE_TAB_BAR_UNREAD_NOTIFICATIONS_COUNTER_KEY } from '~/constants/mobileTabBar'
import { useModuleNavigation } from '~/composables/useModuleNavigation'
import { useNotificationStore } from '~/stores/notifications'
import { ModuleNavigation } from '~/utils/moduleNavigation'

const TABLET_SCREEN_MEDIA_QUERY: string = '(width >= 48rem)'

const route: RouteLocationNormalizedLoaded = useRoute()

const notificationStore: ReturnType<typeof useNotificationStore> = useNotificationStore()

const { counters, tabBar }: UseModuleNavigationReturn = useModuleNavigation()

// Same conditions as the `standalone:` classes above: the count is only followed while the bar shows.
const isTabBarShown: ComputedRef<boolean> = useMediaQuery(
  '(display-mode: standalone) and (width < 64rem), (display-mode: standalone) and (pointer: coarse)',
)

const isTabletScreen: ComputedRef<boolean> = useMediaQuery(TABLET_SCREEN_MEDIA_QUERY)

const shownLinks: ComputedRef<UiMobileTabBarLink[]> = computed((): UiMobileTabBarLink[] =>
  tabBar.value.links.filter((link: UiMobileTabBarLink): boolean => isTabletScreen.value || link.isShownOnPhone),
)

const mainAction: ComputedRef<DlhModulePrimaryCta | null> = computed(
  (): DlhModulePrimaryCta | null => tabBar.value.mainAction,
)

const isMainActionPageOpen: ComputedRef<boolean> = computed(
  (): boolean => mainAction.value !== null && ModuleNavigation.isPathAtOrUnder(route.path, mainAction.value.to),
)

const activeLinkPath: ComputedRef<string | null> = computed((): string | null => {
  if (isMainActionPageOpen.value) {
    return null
  }
  return ModuleNavigation.electActivePath(
    route.path,
    shownLinks.value.map((link: UiMobileTabBarLink): string => link.to),
  )
})

const linkCounters: ComputedRef<Record<UiSidebarCounterKey, UiSidebarCounter>> = computed(
  (): Record<UiSidebarCounterKey, UiSidebarCounter> => {
    const unreadCount: number = notificationStore.unreadCount
    return {
      ...counters.value,
      [MOBILE_TAB_BAR_UNREAD_NOTIFICATIONS_COUNTER_KEY]: {
        count: unreadCount,
        description: unreadCount > 1 ? `${unreadCount} non lues` : '1 non lue',
      },
    }
  },
)

const shownTabs: ComputedRef<UiMobileTabBarTabProps[]> = computed((): UiMobileTabBarTabProps[] =>
  shownLinks.value.map((link: UiMobileTabBarLink): UiMobileTabBarTabProps => {
    const counter: UiSidebarCounter | undefined =
      link.counterKey === null ? undefined : linkCounters.value[link.counterKey]
    return {
      to: link.to,
      icon: link.icon,
      label: link.label,
      caption: link.caption,
      isActive: link.to === activeLinkPath.value,
      badgeCount: counter?.count ?? 0,
      badgeDescription: counter?.description ?? null,
    }
  }),
)

const tabCountBeforeMainAction: ComputedRef<number> = computed((): number =>
  mainAction.value ? Math.ceil(shownTabs.value.length / 2) : shownTabs.value.length,
)

const tabsBeforeMainAction: ComputedRef<UiMobileTabBarTabProps[]> = computed((): UiMobileTabBarTabProps[] =>
  shownTabs.value.slice(0, tabCountBeforeMainAction.value),
)

const tabsAfterMainAction: ComputedRef<UiMobileTabBarTabProps[]> = computed((): UiMobileTabBarTabProps[] =>
  shownTabs.value.slice(tabCountBeforeMainAction.value),
)

watch(
  isTabBarShown,
  (isShown: boolean): void => {
    if (isShown) notificationStore.startWatching()
    else notificationStore.stopWatching()
  },
  { immediate: true },
)

onBeforeUnmount((): void => {
  notificationStore.stopWatching()
})
</script>
