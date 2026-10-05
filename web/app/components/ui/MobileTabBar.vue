<template>
  <nav
    class="standalone:max-lg:block standalone:pointer-coarse:block hidden shrink-0 border-t border-[var(--app-line)] bg-[var(--app-surface)] pt-1 pr-[env(safe-area-inset-right)] pb-[max(1.5rem,env(safe-area-inset-bottom))] pl-[env(safe-area-inset-left)]"
    aria-label="Navigation rapide"
  >
    <div class="mx-auto flex h-14 max-w-xl items-stretch">
      <UiMobileTabBarTab
        to="/dashboard/campaigns"
        icon="i-lucide-megaphone"
        label="Campagnes"
        :is-active="isRouteUnder('/dashboard/campaigns')"
      />
      <UiMobileTabBarTab
        to="/dashboard/notifications"
        icon="i-lucide-bell"
        label="Notifications"
        :is-active="isRouteUnder('/dashboard/notifications')"
        :badge-count="notificationStore.unreadCount"
        :badge-description="unreadNotificationsDescription"
      />

      <div class="flex w-22 shrink-0 items-center justify-center">
        <NuxtLink
          :to="PROSPECT_SEARCH_PAGE_PATH"
          title="Rechercher des leads"
          aria-label="Rechercher des leads"
          :aria-current="isRouteUnder(PROSPECT_SEARCH_PAGE_PATH) ? 'page' : undefined"
          class="flex size-15 -translate-y-2.5 items-center justify-center rounded-full bg-[var(--app-btn-bg)] text-[var(--app-btn-text)] shadow-[var(--app-shadow-soft)] ring-4 ring-[var(--app-surface)] transition-[translate,opacity] [-webkit-tap-highlight-color:transparent] active:opacity-80"
          :class="props.isDrawerOpenAbove && 'md:translate-y-0'"
        >
          <UIcon name="i-lucide-search" class="size-7" />
        </NuxtLink>
      </div>

      <UiMobileTabBarTab
        to="/dashboard/emails"
        icon="i-lucide-send"
        label="Suivi des emails"
        :is-active="isRouteUnder('/dashboard/emails')"
      />
      <UiMobileTabBarTab
        to="/dashboard/sms"
        icon="i-lucide-message-square-text"
        label="Suivi des SMS"
        :is-active="isRouteUnder('/dashboard/sms')"
      />
    </div>
  </nav>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import type { RouteLocationNormalizedLoaded } from 'vue-router'
import type { UiMobileTabBarProps } from '~/types/UiMobileTabBar'
import { useMediaQuery } from '@vueuse/core'
import { computed, onBeforeUnmount, watch } from 'vue'
import { PROSPECT_SEARCH_PAGE_PATH } from '~/constants/prospectSearch'
import { useNotificationStore } from '~/stores/notifications'

/**
 * Bottom navigation of the installed app: two links, the large search button, two links.
 * From the iPad's width a drawer stops right above the bar: the raised search button then settles into it.
 */
const props: UiMobileTabBarProps = defineProps({
  isDrawerOpenAbove: {
    type: Boolean,
    default: false,
  },
})

const route: RouteLocationNormalizedLoaded = useRoute()

const notificationStore: ReturnType<typeof useNotificationStore> = useNotificationStore()

// Same conditions as the `standalone:` classes above: the count is only followed while the bar shows.
const isTabBarShown: ComputedRef<boolean> = useMediaQuery(
  '(display-mode: standalone) and (width < 64rem), (display-mode: standalone) and (pointer: coarse)',
)

const unreadNotificationsDescription: ComputedRef<string> = computed((): string =>
  notificationStore.unreadCount > 1 ? `${notificationStore.unreadCount} non lues` : '1 non lue',
)

/**
 * Whether the current page is a given section or one of its sub-pages.
 * @param path - The section's path.
 * @returns True when the tab of that section is the current one.
 */
function isRouteUnder(path: string): boolean {
  return route.path === path || route.path.startsWith(`${path}/`)
}

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
