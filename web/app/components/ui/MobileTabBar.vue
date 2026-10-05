<template>
  <!-- Comme GoupixDex : téléphone, deux onglets, la grosse loupe ambrée, deux onglets ; l'onglet ouvert passe en ambre.
       iPad : un onglet de plus de chaque côté, les libellés sous les icônes, et la loupe devient un bouton
       « Rechercher des leads » posé dans la barre. -->
  <nav
    class="standalone:max-lg:block standalone:pointer-coarse:block hidden shrink-0 border-t border-[var(--app-line)] bg-[var(--app-surface)] pt-1 pr-[env(safe-area-inset-right)] pb-[max(1.5rem,env(safe-area-inset-bottom))] pl-[env(safe-area-inset-left)]"
    aria-label="Navigation rapide"
  >
    <div class="mx-auto flex h-14 max-w-xl items-stretch md:max-w-3xl md:px-2">
      <div class="hidden md:contents">
        <UiMobileTabBarTab
          to="/dashboard"
          icon="i-lucide-layout-dashboard"
          label="Tableau de bord"
          caption="Accueil"
          :is-active="route.path === '/dashboard'"
        />
      </div>
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

      <div class="flex w-22 shrink-0 items-center justify-center md:w-auto md:px-2">
        <NuxtLink
          :to="PROSPECT_SEARCH_PAGE_PATH"
          title="Rechercher des leads"
          aria-label="Rechercher des leads"
          :aria-current="isRouteUnder(PROSPECT_SEARCH_PAGE_PATH) ? 'page' : undefined"
          class="flex size-15 -translate-y-2.5 items-center justify-center gap-2 rounded-full bg-[var(--app-accent)] text-[#1b1508] transition-opacity [-webkit-tap-highlight-color:transparent] active:opacity-80 md:h-11 md:w-auto md:translate-y-0 md:px-5"
        >
          <UIcon name="i-lucide-search" class="size-7 md:size-5" />
          <span class="hidden text-sm font-semibold whitespace-nowrap md:inline">Rechercher des leads</span>
        </NuxtLink>
      </div>

      <UiMobileTabBarTab
        to="/dashboard/emails"
        icon="i-lucide-send"
        label="Suivi des emails"
        caption="Emails"
        :is-active="isRouteUnder('/dashboard/emails')"
      />
      <UiMobileTabBarTab
        to="/dashboard/sms"
        icon="i-lucide-message-square-text"
        label="Suivi des SMS"
        caption="SMS"
        :is-active="isRouteUnder('/dashboard/sms')"
      />
      <div class="hidden md:contents">
        <UiMobileTabBarTab
          to="/dashboard/my-prospects"
          icon="i-lucide-users"
          label="Mes prospects"
          caption="Prospects"
          :is-active="isRouteUnder('/dashboard/my-prospects')"
          :badge-count="prospectSearchStore.pendingCount"
          :badge-description="pendingLeadsDescription"
        />
      </div>
    </div>
  </nav>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import type { RouteLocationNormalizedLoaded } from 'vue-router'
import { useMediaQuery } from '@vueuse/core'
import { computed, onBeforeUnmount, watch } from 'vue'
import { PROSPECT_SEARCH_PAGE_PATH } from '~/constants/prospectSearch'
import { useNotificationStore } from '~/stores/notifications'
import { useProspectSearchStore } from '~/stores/prospectSearch'

const route: RouteLocationNormalizedLoaded = useRoute()

const notificationStore: ReturnType<typeof useNotificationStore> = useNotificationStore()

// The dashboard layout already follows the searches: the pending count is read, never fetched, here.
const prospectSearchStore: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()

// Same conditions as the `standalone:` classes above: the count is only followed while the bar shows.
const isTabBarShown: ComputedRef<boolean> = useMediaQuery(
  '(display-mode: standalone) and (width < 64rem), (display-mode: standalone) and (pointer: coarse)',
)

const unreadNotificationsDescription: ComputedRef<string> = computed((): string =>
  notificationStore.unreadCount > 1 ? `${notificationStore.unreadCount} non lues` : '1 non lue',
)

const pendingLeadsDescription: ComputedRef<string> = computed((): string =>
  prospectSearchStore.pendingCount > 1 ? `${prospectSearchStore.pendingCount} leads à valider` : '1 lead à valider',
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
