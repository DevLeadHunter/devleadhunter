<template>
  <div>
    <div v-if="isInitializing" class="fixed inset-0 z-50 flex items-center justify-center bg-[#050505]">
      <div class="loader-smooth"></div>
    </div>
    <div v-else class="flex h-screen w-full bg-[#050505]">
      <!-- Sidebar -->
      <UiSidebar :is-open="isSidebarOpen" :is-mobile="isMobile" @toggle="toggleSidebar" />

      <!-- Main Content -->
      <div class="ml-0 flex flex-1 flex-col overflow-hidden transition-[margin] duration-200 md:ml-64">
        <!-- Mobile Header -->
        <header class="sticky top-0 z-10 border-b border-[#30363d] bg-[#1a1a1a] px-4 py-3 md:hidden">
          <div v-if="showCreditsPopover && isMobile" class="fixed inset-0 z-40" @click="handleClickOutside"></div>
          <div class="flex items-center justify-between">
            <button class="text-[#8b949e] transition-colors hover:text-[#f9f9f9]" @click="toggleSidebar">
              <i class="fa-solid fa-bars h-5 w-5"></i>
            </button>
            <div class="flex flex-1 items-center justify-center gap-3">
              <h1 class="text-sm font-semibold text-[#f9f9f9]">devleadhunter</h1>
            </div>
            <!-- Mobile Credits Icon -->
            <div class="relative z-50">
              <button
                :class="[
                  'flex h-8 w-8 items-center justify-center rounded-full border-2 bg-[#1a1a1a] font-semibold text-[#f9f9f9]',
                  creditBorderColor,
                  creditTextSize,
                ]"
                @click.stop="toggleCreditsPopover"
              >
                {{ creditIconValue }}
              </button>
              <!-- Mobile Popover -->
              <div
                v-if="showCreditsPopover && isMobile"
                class="absolute top-10 right-0 z-50 w-72 rounded-lg border border-[#30363d] bg-[#1a1a1a] p-4 shadow-xl"
                @click.stop
              >
                <div class="mb-3 flex items-start gap-4">
                  <div
                    :class="[
                      'flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full border-2 bg-[#1a1a1a] font-semibold text-[#f9f9f9]',
                      creditBorderColor,
                      creditTextSizeLarge,
                    ]"
                  >
                    {{ creditIconValue }}
                  </div>
                  <div class="min-w-0 flex-1">
                    <p class="mb-1 text-sm font-bold text-[#f9f9f9] uppercase">Remaining Credits</p>
                    <p class="text-xs leading-relaxed text-[#8b949e]">
                      Used to search and find prospects for your campaigns and send emails
                    </p>
                  </div>
                </div>
                <NuxtLink
                  to="/dashboard/buy-credits"
                  class="btn-secondary flex w-full items-center justify-center px-3 py-2 text-center text-xs"
                  @click="showCreditsPopover = false"
                >
                  Refill now
                </NuxtLink>
              </div>
            </div>
          </div>
        </header>

        <!-- Page Content -->
        <main class="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <slot />
        </main>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '~/stores/user'

/**
 * Auth initialization state
 */
const isInitializing: Ref<boolean> = ref(true)

/**
 * Sidebar state
 */
const isSidebarOpen: Ref<boolean> = ref(false)

/**
 * Mobile state
 */
const isMobile: Ref<boolean> = ref(false)

/**
 * Credits popover visibility state
 */
const showCreditsPopover: Ref<boolean> = ref(false)

/**
 * User store instance
 */
const userStore = useUserStore()

/**
 * Credit icon value for circular icon
 */
const creditIconValue = computed(() => {
  const credits = userStore.user?.credits_available ?? userStore.user?.credit_balance
  if (credits === null || credits === undefined) {
    return '0'
  }
  if (credits === -1) {
    return '∞'
  }
  // Always show the real number of credits
  return credits.toString()
})

/**
 * Credit border color based on remaining credits
 */
const creditBorderColor = computed(() => {
  const credits = userStore.user?.credits_available ?? userStore.user?.credit_balance
  if (credits === null || credits === undefined || credits === 0) {
    return 'border-[#DC4747]' // Red for no credits
  }
  if (credits === -1) {
    return 'border-[#30363d]' // Default gray for unlimited
  }
  if (credits <= 10) {
    return 'border-[#DC4747]' // Red for low credits
  }
  return 'border-[#2BAD5F]' // Green for sufficient credits
})

/**
 * Credit text size based on remaining credits
 * Smaller font if 1000 or more
 */
const creditTextSize = computed(() => {
  const credits = userStore.user?.credits_available ?? userStore.user?.credit_balance
  if (credits === null || credits === undefined || credits === -1) {
    return 'text-xs'
  }
  if (credits >= 1000) {
    return 'text-[10px]'
  }
  return 'text-xs'
})

/**
 * Credit text size for large popover icon
 * Smaller font if 1000 or more
 */
const creditTextSizeLarge = computed(() => {
  const credits = userStore.user?.credits_available ?? userStore.user?.credit_balance
  if (credits === null || credits === undefined || credits === -1) {
    return 'text-lg'
  }
  if (credits >= 1000) {
    return 'text-sm'
  }
  return 'text-lg'
})

/**
 * Toggle credits popover (for mobile click)
 */
const toggleCreditsPopover = (): void => {
  showCreditsPopover.value = !showCreditsPopover.value
}

/**
 * Handle click outside to close popover
 */
const handleClickOutside = (): void => {
  showCreditsPopover.value = false
}

/**
 * Initialize authentication
 * @returns {Promise<void>}
 */
async function initializeAuth(): Promise<void> {
  if (import.meta.client) {
    // Small delay to ensure store is hydrated from localStorage
    await new Promise((resolve) => setTimeout(resolve, 300))
    isInitializing.value = false
  }
}

/**
 * Check if viewport is mobile size
 * @returns {void}
 */
const checkMobile = (): void => {
  if (import.meta.client) {
    isMobile.value = window.innerWidth < 768
    if (!isMobile.value) {
      isSidebarOpen.value = true
    }
  }
}

/**
 * Toggle sidebar
 * @returns {void}
 */
const toggleSidebar = (): void => {
  isSidebarOpen.value = !isSidebarOpen.value
}

/**
 * Handle window resize
 * @returns {void}
 */
const handleResize = (): void => {
  checkMobile()
}

// Lifecycle hooks
onMounted(async () => {
  await initializeAuth()
  checkMobile()
  if (import.meta.client) {
    window.addEventListener('resize', handleResize)
  }
})

onUnmounted(() => {
  if (import.meta.client) {
    window.removeEventListener('resize', handleResize)
  }
})
</script>

<style scoped>
.loader-smooth {
  width: 60px;
  height: 60px;
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-left-color: #f9f9f9;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
