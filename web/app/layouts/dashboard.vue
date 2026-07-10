<template>
  <div class="app-theme" :data-theme="theme">
    <div
      v-if="isInitializing"
      class="fixed inset-0 z-50 flex items-center justify-center"
      :style="{ backgroundColor: 'var(--app-bg)' }"
    >
      <div class="loader-smooth"></div>
    </div>
    <div v-else class="flex h-screen w-full" :style="{ backgroundColor: 'var(--app-bg)' }">
      <!-- Sidebar -->
      <UiSidebar :is-open="isSidebarOpen" :is-mobile="isMobile" @toggle="toggleSidebar" />

      <!-- Main Content — pushed left when a drawer is open (nothing gets hidden) -->
      <div
        class="ml-0 flex flex-1 flex-col overflow-hidden transition-[margin] duration-200 md:ml-64"
        :class="drawerPushClass"
      >
        <!-- Mobile Header -->
        <header class="sticky top-0 z-10 border-b border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3 md:hidden">
          <div v-if="showCreditsPopover && isMobile" class="fixed inset-0 z-40" @click="handleClickOutside"></div>
          <div class="flex items-center justify-between">
            <button
              class="flex h-9 w-9 items-center justify-center rounded-lg text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
              aria-label="Ouvrir le menu"
              @click="toggleSidebar"
            >
              <UIcon name="i-lucide-menu" class="h-4 w-4" />
            </button>
            <span class="font-display text-base font-semibold tracking-tight text-[var(--app-ink)]">
              devleadhunter
            </span>
            <!-- Mobile credits pill -->
            <div class="relative z-50">
              <button
                class="flex items-center gap-2 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)] px-3 py-1.5"
                @click.stop="toggleCreditsPopover"
              >
                <span class="h-2 w-2 rounded-full" :style="{ backgroundColor: creditDotColor }"></span>
                <span class="font-label text-xs font-medium text-[var(--app-ink)]">{{ creditIconValue }}</span>
              </button>
              <!-- Mobile Popover -->
              <div
                v-if="showCreditsPopover && isMobile"
                class="app-card absolute top-11 right-0 z-50 w-72 p-4 shadow-[var(--app-shadow-soft)]"
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

        <!-- Page Content -->
        <main class="flex-1 overflow-y-auto px-4 py-5 md:px-6 md:py-6">
          <slot />
        </main>
      </div>

      <!-- Persistent drawer stack — rendered once here so open drawers
           survive page navigation. -->
      <UiDrawerStackHost />

      <!-- Global command palette (Ctrl+K) -->
      <UiCommandPalette />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ComputedRef, Ref } from 'vue'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '~/stores/user'
import { useAppTheme } from '~/composables/useAppTheme'
import { useDrawerStackStore } from '~/stores/drawerStack'

/** Auth initialization state (boot loader overlay). */
const isInitializing: Ref<boolean> = ref<boolean>(true)

/** Sidebar visibility (always open on desktop, toggled on mobile). */
const isSidebarOpen: Ref<boolean> = ref<boolean>(false)

/** Whether the viewport is below the md breakpoint. */
const isMobile: Ref<boolean> = ref<boolean>(false)

/** Credits popover visibility (mobile header). */
const showCreditsPopover: Ref<boolean> = ref<boolean>(false)

/** User store instance. */
const userStore = useUserStore()

/** Dashboard theme (light paper / dark warm ink). */
const { theme, initTheme } = useAppTheme()

/** Persistent drawer stack — drives the content push when a drawer is open. */
const drawerStack = useDrawerStackStore()

/**
 * Right margin pushing the content aside so the open drawer hides nothing.
 * Matches each drawer's width; only from lg up (below, the drawer overlays).
 */
const drawerPushClass: ComputedRef<string> = computed((): string => {
  const top = drawerStack.topEntry
  if (!top) return ''
  return top.kind === 'email-template' ? 'lg:mr-[560px]' : 'lg:mr-[480px]'
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
 * Track the md breakpoint and force the sidebar open on desktop.
 */
function checkMobile(): void {
  if (import.meta.client) {
    isMobile.value = window.innerWidth < 768
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

onMounted(async (): Promise<void> => {
  initTheme()
  await initializeAuth()
  checkMobile()
  if (import.meta.client) {
    window.addEventListener('resize', handleResize)
  }
})

onUnmounted((): void => {
  if (import.meta.client) {
    window.removeEventListener('resize', handleResize)
  }
})
</script>
