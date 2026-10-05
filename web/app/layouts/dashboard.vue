<template>
  <div class="app-theme" :data-theme="theme">
    <div
      v-if="isInitializing"
      class="fixed inset-0 z-50 flex items-center justify-center"
      :style="{ backgroundColor: 'var(--app-bg)' }"
    >
      <div class="loader-smooth"></div>
    </div>
    <!-- Fixée aux quatre bords plutôt que `h-dvh` : dans l'app installée sur iPhone, iOS compte 100dvh sans la barre
         d'état (59 pt de moins), ce qui décollait la barre d'onglets du bas de l'écran. -->
    <div v-else class="fixed inset-0 flex" :style="{ backgroundColor: 'var(--app-bg)' }">
      <UiSidebar :is-open="isSidebarOpen" :is-mobile="isMobile" @toggle="toggleSidebar" />

      <div
        ref="mobileSwipeArea"
        class="ml-0 flex min-w-0 flex-1 flex-col overflow-hidden transition-[margin] duration-200 lg:ml-64"
        :class="drawerPushClass"
      >
        <header
          class="sticky top-0 z-10 border-b border-[var(--app-line)] bg-[var(--app-surface)] pt-[calc(0.5rem+env(safe-area-inset-top))] pr-[max(1rem,env(safe-area-inset-right))] pb-2 pl-[max(1rem,env(safe-area-inset-left))] lg:hidden"
        >
          <div v-if="showCreditsPopover && isMobile" class="fixed inset-0 z-40" @click="handleClickOutside"></div>
          <div class="flex items-center justify-between">
            <button
              class="-ml-3 flex size-11 items-center justify-center rounded-xl text-[var(--app-ink-soft)] transition-colors [-webkit-tap-highlight-color:transparent] hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)] active:bg-[var(--app-surface-2)]"
              aria-label="Ouvrir le menu"
              @click="toggleSidebar"
            >
              <UIcon name="i-lucide-menu" class="size-5" />
            </button>
            <span class="font-display text-base font-semibold tracking-tight text-[var(--app-ink)]">
              devleadhunter
            </span>

            <div class="relative z-50">
              <button
                class="flex h-10 items-center gap-2 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)] px-3.5 [-webkit-tap-highlight-color:transparent]"
                @click.stop="toggleCreditsPopover"
              >
                <span class="h-2 w-2 rounded-full" :style="{ backgroundColor: creditDotColor }"></span>
                <span class="font-label text-xs font-medium text-[var(--app-ink)]">{{ creditIconValue }}</span>
              </button>

              <div
                v-if="showCreditsPopover && isMobile"
                class="app-card absolute top-12 right-0 z-50 w-72 p-4 shadow-[var(--app-shadow-soft)]"
                @click.stop
              >
                <p class="app-label">Crédits restants</p>
                <p class="font-display mt-1 text-3xl font-semibold text-[var(--app-ink)]">
                  {{ creditIconValue }}
                </p>
                <p class="mt-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
                  Consommés par les recherches de prospects et les envois d'emails.
                </p>
                <NuxtLink
                  to="/dashboard/buy-credits"
                  class="app-btn-secondary mt-4 h-9 w-full text-xs"
                  @click="showCreditsPopover = false"
                >
                  Recharger
                </NuxtLink>
              </div>
            </div>
          </div>
        </header>

        <main
          :id="DASHBOARD_SCROLL_CONTAINER_ID"
          class="standalone:max-md:pb-5 @container flex-1 scroll-pb-28 overflow-x-hidden overflow-y-auto pt-5 pr-[max(1rem,env(safe-area-inset-right))] pb-[calc(1.25rem+env(safe-area-inset-bottom))] pl-[max(1rem,env(safe-area-inset-left))] md:pt-6 md:pr-[max(1.5rem,env(safe-area-inset-right))] md:pb-6 md:pl-[max(1.5rem,env(safe-area-inset-left))]"
        >
          <slot />
        </main>

        <UiMobileTabBar />
      </div>

      <UiDrawerStackHost />

      <UiCommandPalette />

      <ProspectSearchLeadNotifications />

      <UiPullToRefresh />
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { AppTheme } from '~/types/AppTheme'
import type { UseAutomationCompletionNotifierReturn } from '~/types/Composables'
import type { ComputedRef, Ref } from 'vue'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '~/stores/user'
import { useAppTheme } from '~/composables/useAppTheme'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useProspectSearchStore } from '~/stores/prospectSearch'
import { useAutomationCompletionNotifier } from '~/composables/useAutomationCompletionNotifier'
import { DASHBOARD_SCROLL_CONTAINER_ID } from '~/composables/useDashboardScroll'
import { useHorizontalSwipe } from '~/composables/useHorizontalSwipe'

// Tailwind's `lg`: below it the sidebar is a slide-over menu, and the installed app shows its tab bar.
const SIDEBAR_BREAKPOINT_PX: number = 1024

// The header's `--app-surface` in each theme, for the browser bar and the installed app's status bar.
const APP_HEADER_COLORS: Record<AppTheme, string> = { light: '#fbf9f3', dark: '#1b1b1a' }

// The token renews twice a day: an hourly look keeps the desktop app hidden in the tray signed in.
const SESSION_RENEWAL_CHECK_INTERVAL_MS: number = 60 * 60 * 1000

let sessionRenewalTimer: ReturnType<typeof setInterval> | null = null

/** Auth initialization state (boot loader overlay). */
const isInitializing: Ref<boolean> = ref(true)

/** Sidebar visibility (always open on desktop, toggled on mobile). */
const isSidebarOpen: Ref<boolean> = ref(false)

/** Whether the viewport is below the lg breakpoint, where the sidebar becomes a slide-over menu. */
const isMobile: Ref<boolean> = ref(false)

/** Credits popover visibility (mobile header). */
const showCreditsPopover: Ref<boolean> = ref(false)

/** Content column — target of the left-edge swipe that opens the nav on mobile. */
const mobileSwipeArea: Ref<HTMLElement | null> = ref(null)

/** User store instance. */
const userStore: ReturnType<typeof useUserStore> = useUserStore()

/** Dashboard theme (light paper / dark warm ink). */
const { theme, initTheme }: { theme: Ref<AppTheme, AppTheme>; initTheme: () => void; toggleTheme: () => void } =
  useAppTheme()

/** Persistent drawer stack — drives the content push when a drawer is open. */
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

const prospectSearchStore: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()

/** Background watcher toasting automatisation completions across every dashboard page. */
const automationNotifier: UseAutomationCompletionNotifierReturn = useAutomationCompletionNotifier()

// Authenticated app shell — never index dashboard pages (thin content behind auth).
useSeoMeta({
  robots: 'noindex, nofollow',
})

// Short document title for Safari "Add to Home Screen" (iOS uses <title>, not the marketing default).
// The browser bar, and the status bar of the installed app, take the colour of the header in both themes.
useHead({
  title: 'DevleadHunter',
  titleTemplate: (): string => 'DevleadHunter',
  meta: [
    { name: 'apple-mobile-web-app-title', content: 'DevleadHunter' },
    { name: 'theme-color', content: computed((): string => APP_HEADER_COLORS[theme.value]) },
  ],
})

/**
 * Right margin pushing the content aside so the open drawer hides nothing.
 * Matches each drawer's width; only from xl up — below, the drawer overlays,
 * otherwise the sidebar + push would crush the content on mid-size screens.
 */
const drawerPushClass: ComputedRef<string> = computed((): string => {
  const top: ReturnType<typeof useDrawerStackStore>['topEntry'] = drawerStack.topEntry
  if (!top) return ''
  return top.kind === 'email-template' ? 'xl:mr-[560px]' : 'xl:mr-[480px]'
})

/** Credits counter shown in the pill ("∞" when unlimited). */
const creditIconValue: ComputedRef<string> = computed((): string => {
  const credits: number | null | undefined = userStore.user?.credits_available ?? userStore.user?.credit_balance
  if (credits === null || credits === undefined) {
    return '0'
  }
  if (credits === -1) {
    return '∞'
  }
  return credits.toString()
})

/** Semantic dot colour next to the credits counter. */
const creditDotColor: ComputedRef<string> = computed((): string => {
  const credits: number | null | undefined = userStore.user?.credits_available ?? userStore.user?.credit_balance
  if (credits === -1) {
    return 'var(--app-ink-soft)'
  }
  if (credits === null || credits === undefined || credits === 0 || credits <= 10) {
    return 'var(--app-red)'
  }
  return 'var(--app-green)'
})

/**
 * Toggle the mobile credits popover.
 */
function toggleCreditsPopover(): void {
  showCreditsPopover.value = !showCreditsPopover.value
}

/**
 * Close the credits popover when clicking outside of it.
 */
function handleClickOutside(): void {
  showCreditsPopover.value = false
}

/**
 * Wait for the auth store hydration before revealing the shell.
 */
async function initializeAuth(): Promise<void> {
  if (import.meta.client) {
    // Small delay to ensure store is hydrated from localStorage
    await new Promise((resolve: (value: unknown) => void): ReturnType<typeof setTimeout> => setTimeout(resolve, 300))
    isInitializing.value = false
  }
}

/**
 * Track the lg breakpoint and force the sidebar open on desktop.
 */
function checkMobile(): void {
  if (import.meta.client) {
    isMobile.value = window.innerWidth < SIDEBAR_BREAKPOINT_PX
    if (!isMobile.value) {
      isSidebarOpen.value = true
    }
  }
}

/**
 * Toggle the sidebar (mobile).
 */
function toggleSidebar(): void {
  isSidebarOpen.value = !isSidebarOpen.value
}

/**
 * Window resize handler.
 */
function handleResize(): void {
  checkMobile()
}

/** Distance from the left edge (px) within which an edge-swipe opens the menu. */
const EDGE_SWIPE_START_PX: number = 24

// Edge-swipe from the left opens the nav on mobile — only when no drawer is capturing gestures.
useHorizontalSwipe(mobileSwipeArea, {
  enabled: (): boolean => isMobile.value && !isSidebarOpen.value && drawerStack.topEntry === null,
  edgeStartPx: EDGE_SWIPE_START_PX,
  onSwipeRight: (): void => {
    isSidebarOpen.value = true
  },
})

onMounted(async (): Promise<void> => {
  initTheme()
  await initializeAuth()
  checkMobile()
  if (import.meta.client) {
    window.addEventListener('resize', handleResize)
    automationNotifier.start()
    prospectSearchStore.startWatching()
    sessionRenewalTimer = setInterval((): void => {
      void userStore.renewTokenIfAging()
    }, SESSION_RENEWAL_CHECK_INTERVAL_MS)
  }
})

onUnmounted((): void => {
  if (import.meta.client) {
    window.removeEventListener('resize', handleResize)
    automationNotifier.stop()
    prospectSearchStore.stopWatching()
    if (sessionRenewalTimer !== null) clearInterval(sessionRenewalTimer)
  }
})
</script>
