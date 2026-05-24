<template>
  <aside
    :class="[
      'fixed left-0 top-0 z-40 h-full border-r border-[#30363d] bg-[#1a1a1a] transition-transform duration-300',
      isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
      isMobile ? 'w-64' : 'w-64',
    ]"
  >
    <!-- Logo / Header -->
    <div class="border-b border-[#30363d] bg-[#1a1a1a] px-4 py-5">
      <div class="flex items-center justify-center gap-3">
        <div class="flex h-5 w-5 items-center justify-center rounded">
          <svg
            class="h-full w-full fill-current text-white"
            viewBox="0 0 493 515"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M40.6667 1.73334C13.3333 8.80001 2.93333 27.6 8.53333 59.3333C9.73333 65.8667 15.4667 86.6667 21.3333 105.333C33.4667 143.6 41.2 173.733 45.6 199.333C48 213.867 48.5333 221.867 48.5333 248C48.6667 296.8 44.1333 319.067 19.3333 392.667C3.46667 440 0 453.867 0 469.867C0 489.067 6.8 500.933 21.7333 508.133C44.2667 518.8 77.8667 516.133 107.333 501.333C144.533 482.667 158.933 460.133 168.667 404.933C174.8 369.6 179.733 357.6 194 343.2C199.2 337.867 207.6 331.333 212.933 328.133C233.067 316.533 266.267 305.733 291.467 302.667C298 301.867 305.333 301.067 307.733 300.667L312 300.133V335.067C312 385.6 314.667 410.933 322.267 435.2C333.333 470.533 356.267 493.333 393.867 506.533C435.067 521.067 476 515.067 486.533 492.933C493.6 477.867 491.467 464.133 473.867 410.933C459.867 368.8 452.533 341.733 447.867 315.333C445.2 300.533 444.8 293.6 444.8 267.333C444.8 241.6 445.333 234 447.867 220C453.333 189.2 460 164.4 477.6 108C491.867 62.1333 494.533 45.2 490 29.7333C484.267 10.4 465.6 5.71296e-06 437.067 5.71296e-06C405.867 5.71296e-06 378.533 10.8 358.4 31.0667C341.467 47.8667 331.6 71.3333 325.467 108.667C321.2 134.533 317.733 147.467 312.4 158.667C298 188.8 258.533 207.6 192.933 215.467C182.8 216.667 174.267 217.333 173.867 216.933C173.467 216.533 173.867 206.133 174.8 193.867C178.667 139.867 172.133 78 160.133 53.0667C148.8 29.4667 126 12.1333 96.1333 4.40001C80.5333 0.400006 51.4667 -1.06666 40.6667 1.73334Z"
              fill="currentColor"
            />
          </svg>
        </div>
        <h1 class="text-sm font-semibold text-[#f9f9f9]">Devleadhunter</h1>
      </div>
    </div>

    <!-- Navigation Links -->
    <nav class="flex flex-col gap-2 px-2 py-4">
      <!-- Desktop Credits Section -->
      <div v-if="!isMobile" class="px-2 py-2">
        <div class="relative" @mouseenter="handleMouseEnter" @mouseleave="handleMouseLeave">
          <button
            class="hover:btn-sidebar-hover flex w-full cursor-pointer items-center justify-start gap-2 rounded text-sm font-medium text-[#8b949e] transition-all hover:text-[#f9f9f9]"
            @click.stop="toggleCreditsPopover"
          >
            <div
              :class="[
                'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border-2 bg-[#050505] font-semibold text-[#f9f9f9]',
                creditBorderColor,
                creditTextSize,
              ]"
            >
              {{ creditIconValue }}
            </div>
            <span>Remaining Credits</span>
          </button>
          <!-- Desktop Popover -->
          <div
            v-if="showCreditsPopover && !isMobile"
            class="absolute left-full top-0 z-50 ml-4 w-80 rounded-lg border border-[#30363d] bg-[#1a1a1a] p-4 shadow-xl"
            @mouseenter="handleMouseEnter"
            @mouseleave="handleMouseLeave"
            @click.stop
          >
            <div class="mb-3 flex items-start gap-4">
              <div
                :class="[
                  'flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-full border-2 bg-[#1a1a1a] font-semibold text-[#f9f9f9]',
                  creditBorderColor,
                  creditTextSizeLarge,
                ]"
              >
                {{ creditIconValue }}
              </div>
              <div class="min-w-0 flex-1">
                <p class="mb-1 text-sm font-bold uppercase text-[#f9f9f9]">Remaining Credits</p>
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

      <NuxtLink
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        :class="[
          'flex items-center gap-2 rounded px-3 py-2 text-sm font-medium transition-all',
          isActive(link.to)
            ? 'btn-sidebar-active text-[#f9f9f9]'
            : 'hover:btn-sidebar-hover text-[#8b949e] hover:text-[#f9f9f9]',
        ]"
        @click="handleClick"
      >
        <i :class="link.icon" class="h-4 w-4"></i>
        <span>{{ link.label }}</span>
      </NuxtLink>
    </nav>

    <!-- User Info -->
    <div class="absolute bottom-0 left-0 right-0 border-t border-[#30363d] bg-[#1a1a1a] p-4">
      <!-- User Profile - Clickable -->
      <button
        class="group mb-2 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm transition-all hover:bg-[#2a2a2a]"
        @click="handleProfile"
      >
        <div
          class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-[#30363d] bg-[#050505]"
        >
          <span class="text-xs font-semibold text-[#f9f9f9]">
            {{ userInitials }}
          </span>
        </div>
        <div class="min-w-0 flex-1 text-left">
          <p class="truncate font-semibold text-[#f9f9f9] transition-colors">
            {{ userName }}
          </p>
          <p class="truncate text-xs text-[#8b949e]">
            {{ userEmail }}
          </p>
        </div>
      </button>

      <button
        class="w-full rounded px-3 py-1.5 text-sm text-[#DC4747] transition-all hover:bg-[#da3633]/20"
        @click="handleLogout"
      >
        Logout
      </button>
    </div>
  </aside>

  <!-- Overlay for mobile -->
  <div v-if="isOpen && isMobile" class="fixed inset-0 z-30 bg-black/70 md:hidden" @click="$emit('toggle')" />
</template>

<script setup lang="ts">
import type { Ref } from 'vue'
import { ref, computed } from 'vue'
import { useUserStore } from '~/stores/user'
import { useAuth } from '~/composables/useAuth'

/**
 * Props for the Sidebar component
 */
interface Props {
  /**
   * Whether the sidebar is open
   */
  isOpen: boolean

  /**
   * Whether the viewport is mobile size
   */
  isMobile: boolean
}

/**
 * Props definition
 */
const props = defineProps<Props>()

/**
 * Emits
 */
const emit = defineEmits<{
  toggle: []
}>()

/**
 * User store instance
 */
const userStore = useUserStore()

/**
 * Navigation links configuration
 */
const links = computed(() => {
  const baseLinks = [
    { to: '/dashboard/search-prospects', label: 'Recherche Prospects', icon: 'fa-solid fa-magnifying-glass' },
    { to: '/dashboard/my-prospects', label: 'Mes Prospects', icon: 'fa-solid fa-users' },
    { to: '/dashboard/demo-sites', label: 'Demo Websites', icon: 'fa-solid fa-globe' },
    { to: '/dashboard/campaigns', label: 'Campaigns', icon: 'fa-solid fa-envelope' },
    { to: '/dashboard/email-accounts', label: 'Email Accounts', icon: 'fa-solid fa-at' },
    { to: '/dashboard/email-templates', label: 'Email Templates', icon: 'fa-solid fa-file-lines' },
    { to: '/dashboard/credits', label: 'My Credits', icon: 'fa-solid fa-coins' },
    { to: '/dashboard/support', label: 'Support', icon: 'fa-solid fa-headset' },
    { to: '/dashboard/buy-credits', label: 'Buy Credits', icon: 'fa-solid fa-credit-card' },
  ]

  // Add admin links for admin users
  if (userStore.user?.role === 'ADMIN') {
    baseLinks.push({ to: '/dashboard/users', label: 'Users', icon: 'fa-solid fa-users-gear' })
    baseLinks.push({ to: '/dashboard/credit-settings', label: 'Credit Settings', icon: 'fa-solid fa-sliders' })
    baseLinks.push({ to: '/dashboard/accounting', label: 'Comptabilité', icon: 'fa-solid fa-chart-line' })
  }

  return baseLinks
})

/**
 * Auth composable
 */
const { logout } = useAuth()

/**
 * User name computed property
 */
const userName = computed(() => {
  return userStore.userName || 'User'
})

/**
 * User email computed property
 */
const userEmail = computed(() => {
  return userStore.userEmail
})

/**
 * User initials computed property
 */
const userInitials = computed(() => {
  const name = userName.value
  if (!name) return 'U'
  const parts = name.split(' ')
  if (parts.length >= 2 && parts[0] && parts[1]) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
})

/**
 * Credits popover visibility state
 */
const showCreditsPopover: Ref<boolean> = ref(false)

/**
 * Popover hover state
 */
const isHoveringPopover: Ref<boolean> = ref(false)

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

  if (credits === -1) {
    return 'text-2xl'
  }

  if (credits === null || credits === undefined) {
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

  if (credits === -1) {
    return 'text-4xl'
  }

  if (credits === null || credits === undefined) {
    return 'text-xl'
  }
  if (credits >= 1000) {
    return 'text-sm'
  }
  return 'text-xl'
})

/**
 * Timeout for closing popover
 */
let hoverTimeout: ReturnType<typeof setTimeout> | null = null

/**
 * Toggle credits popover
 */
const toggleCreditsPopover = (): void => {
  showCreditsPopover.value = !showCreditsPopover.value
}

/**
 * Handle mouse enter on credits section
 */
const handleMouseEnter = (): void => {
  if (!props.isMobile) {
    if (hoverTimeout) {
      clearTimeout(hoverTimeout)
      hoverTimeout = null
    }
    isHoveringPopover.value = true
    showCreditsPopover.value = true
  }
}

/**
 * Handle mouse leave from credits section
 */
const handleMouseLeave = (): void => {
  if (!props.isMobile) {
    isHoveringPopover.value = false
    hoverTimeout = setTimeout(() => {
      if (!isHoveringPopover.value) {
        showCreditsPopover.value = false
      }
    }, 100)
  }
}

/**
 * Check if a route is active
 * @param {string} path - Route path to check
 * @returns {boolean} True if the route is active
 */
const isActive = (path: string): boolean => {
  const route = useRoute()
  // Exact match
  if (route.path === path) return true
  // For sub-routes, but exclude /dashboard to avoid matching all dashboard routes
  if (path !== '/dashboard' && route.path.startsWith(path + '/')) return true
  return false
}

/**
 * Handle link click (close sidebar on mobile)
 * @returns {void}
 */
const handleClick = (): void => {
  if (props.isMobile) {
    emit('toggle')
  }
}

/**
 * Handle profile button click
 * @returns {void}
 */
const handleProfile = (): void => {
  navigateTo('/profile')
  handleClick()
}

/**
 * Handle logout button click
 * @returns {void}
 */
const handleLogout = (): void => {
  logout()
  handleClick()
}
</script>
