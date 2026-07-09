<template>
  <aside
    :class="[
      'fixed top-0 left-0 z-40 flex h-full w-64 flex-col border-r border-[var(--app-line)] bg-[var(--app-surface)] transition-transform duration-300',
      isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
    ]"
  >
    <!-- Brand + module switcher -->
    <div class="border-b border-[var(--app-line)] px-4 pt-4 pb-3">
      <div class="flex items-center gap-2.5 px-1">
        <svg
          class="h-4 w-4 fill-current text-[var(--app-ink)]"
          viewBox="0 0 493 515"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            d="M40.6667 1.73334C13.3333 8.80001 2.93333 27.6 8.53333 59.3333C9.73333 65.8667 15.4667 86.6667 21.3333 105.333C33.4667 143.6 41.2 173.733 45.6 199.333C48 213.867 48.5333 221.867 48.5333 248C48.6667 296.8 44.1333 319.067 19.3333 392.667C3.46667 440 0 453.867 0 469.867C0 489.067 6.8 500.933 21.7333 508.133C44.2667 518.8 77.8667 516.133 107.333 501.333C144.533 482.667 158.933 460.133 168.667 404.933C174.8 369.6 179.733 357.6 194 343.2C199.2 337.867 207.6 331.333 212.933 328.133C233.067 316.533 266.267 305.733 291.467 302.667C298 301.867 305.333 301.067 307.733 300.667L312 300.133V335.067C312 385.6 314.667 410.933 322.267 435.2C333.333 470.533 356.267 493.333 393.867 506.533C435.067 521.067 476 515.067 486.533 492.933C493.6 477.867 491.467 464.133 473.867 410.933C459.867 368.8 452.533 341.733 447.867 315.333C445.2 300.533 444.8 293.6 444.8 267.333C444.8 241.6 445.333 234 447.867 220C453.333 189.2 460 164.4 477.6 108C491.867 62.1333 494.533 45.2 490 29.7333C484.267 10.4 465.6 5.71296e-06 437.067 5.71296e-06C405.867 5.71296e-06 378.533 10.8 358.4 31.0667C341.467 47.8667 331.6 71.3333 325.467 108.667C321.2 134.533 317.733 147.467 312.4 158.667C298 188.8 258.533 207.6 192.933 215.467C182.8 216.667 174.267 217.333 173.867 216.933C173.467 216.533 173.867 206.133 174.8 193.867C178.667 139.867 172.133 78 160.133 53.0667C148.8 29.4667 126 12.1333 96.1333 4.40001C80.5333 0.400006 51.4667 -1.06666 40.6667 1.73334Z"
            fill="currentColor"
          />
        </svg>
        <span class="text-sm font-semibold tracking-tight text-[var(--app-ink)]">devleadhunter</span>
      </div>

      <!-- Module switcher — the shell is built for three activatable modules -->
      <div class="relative mt-2.5">
        <div v-if="showModuleMenu" class="fixed inset-0 z-40" @click="showModuleMenu = false"></div>
        <button
          type="button"
          class="relative z-50 flex w-full cursor-pointer items-center justify-between rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-2.5 py-1.5 transition-colors hover:border-[var(--app-ink-soft)]"
          aria-label="Changer de module"
          @click.stop="showModuleMenu = !showModuleMenu"
        >
          <span class="app-label flex items-center gap-1.5 !text-[0.6rem]">
            <span class="h-1.5 w-1.5 rounded-full bg-[var(--app-accent)]"></span>
            {{ activeModuleLabel }}
          </span>
          <UIcon name="i-lucide-chevrons-up-down" class="h-3 w-3 text-[var(--app-ink-soft)]" />
        </button>
        <div
          v-if="showModuleMenu"
          class="app-card absolute inset-x-0 top-full z-50 mt-1 p-1 shadow-[var(--app-shadow-soft)]"
        >
          <button
            v-for="moduleEntry in modules"
            :key="moduleEntry.key"
            type="button"
            class="flex w-full cursor-pointer items-center justify-between rounded-md px-2 py-1.5 text-left text-xs transition-colors hover:bg-[var(--app-surface-2)]"
            :class="moduleEntry.locked ? 'text-[var(--app-ink-soft)]' : 'font-medium text-[var(--app-ink)]'"
            @click="handleModuleClick(moduleEntry)"
          >
            <span class="flex items-center gap-2">
              <UIcon :name="moduleEntry.icon" class="h-3.5 w-3.5" />
              {{ moduleEntry.label }}
            </span>
            <UIcon v-if="moduleEntry.locked" name="i-lucide-lock" class="h-3 w-3 opacity-70" />
            <span v-else class="h-1.5 w-1.5 rounded-full bg-[var(--app-accent)]"></span>
          </button>
        </div>
      </div>
    </div>

    <!-- Primary action -->
    <div class="px-4 pt-3">
      <NuxtLink
        to="/dashboard/demo-sites/create"
        class="app-btn-primary h-8 min-h-8 w-full text-xs"
        @click="handleClick"
      >
        <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
        Créer un site
      </NuxtLink>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto px-4 py-3">
      <!-- Administration sub-panel (replaces main menu, Vercel-style) -->
      <template v-if="isAdmin && showAdminPanel">
        <button
          type="button"
          class="mb-3 flex w-full cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-sm font-semibold text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
          @click="handleAdminBack"
        >
          <UIcon name="i-lucide-chevron-left" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
          <span>Menu principal</span>
        </button>
        <div class="space-y-0.5">
          <NuxtLink
            v-for="link in adminLinks"
            :key="link.to"
            :to="link.to"
            :class="navItemClass(isLinkActive(link.to))"
            @click="handleClick"
          >
            <span :class="navBarClass(isLinkActive(link.to))"></span>
            <UIcon v-if="link.icon.startsWith('i-')" :name="link.icon" class="h-4 w-4 shrink-0" />
            <i v-else :class="link.icon" class="h-4 w-4 shrink-0"></i>
            <span class="truncate">{{ link.label }}</span>
          </NuxtLink>
        </div>
      </template>

      <!-- Paramètres sub-panel -->
      <template v-else-if="showSettingsPanel">
        <button
          type="button"
          class="mb-3 flex w-full cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-sm font-semibold text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
          @click="showSettingsPanel = false"
        >
          <UIcon name="i-lucide-chevron-left" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
          <span>Menu principal</span>
        </button>
        <NuxtLink
          to="/dashboard/settings/resend"
          :class="navItemClass(isActive('/dashboard/settings/resend'))"
          @click="handleClick"
        >
          <span :class="navBarClass(isActive('/dashboard/settings/resend'))"></span>
          <UIcon name="i-lucide-mail-open" class="h-4 w-4 shrink-0" />
          <span>Configuration Resend</span>
        </NuxtLink>
      </template>

      <!-- Main grouped menu -->
      <template v-else>
        <div v-for="group in navGroups" :key="group.heading ?? 'top'" class="mb-4 last:mb-0">
          <p v-if="group.heading" class="app-label mb-1.5 px-3 !text-[0.6rem]">{{ group.heading }}</p>
          <div class="space-y-0.5">
            <NuxtLink
              v-for="link in group.links"
              :key="link.to"
              :to="link.to"
              :class="navItemClass(isActive(link.to))"
              @click="handleClick"
            >
              <span :class="navBarClass(isActive(link.to))"></span>
              <UIcon :name="link.icon" class="h-4 w-4 shrink-0" />
              <span class="truncate">{{ link.label }}</span>
            </NuxtLink>
          </div>
        </div>

        <!-- Paramètres -->
        <button type="button" :class="navItemClass(showSettingsPanel)" class="w-full" @click="showSettingsPanel = true">
          <span :class="navBarClass(false)"></span>
          <UIcon name="i-lucide-settings" class="h-4 w-4 shrink-0" />
          <span>Paramètres</span>
          <UIcon name="i-lucide-chevron-right" class="ml-auto h-3.5 w-3.5 opacity-50" />
        </button>

        <!-- Administration (admin only) -->
        <button
          v-if="isAdmin"
          type="button"
          :class="navItemClass(isAdminNavActive)"
          class="w-full"
          @click="handleAdminClick"
        >
          <span :class="navBarClass(isAdminNavActive)"></span>
          <UIcon name="i-lucide-shield" class="h-4 w-4 shrink-0" />
          <span>Administration</span>
          <UIcon name="i-lucide-chevron-right" class="ml-auto h-3.5 w-3.5 opacity-50" />
        </button>

        <!-- Credits (admin only) -->
        <div
          v-if="!isMobile && isAdmin"
          class="relative mt-5"
          @mouseenter="handleMouseEnter"
          @mouseleave="handleMouseLeave"
        >
          <button
            class="flex w-full cursor-pointer items-center justify-between rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5 transition-colors hover:border-[var(--app-ink-soft)]"
            @click.stop="toggleCreditsPopover"
          >
            <span class="app-label !text-[0.6rem]">Crédits</span>
            <span class="flex items-center gap-2">
              <span class="h-2 w-2 rounded-full" :style="{ backgroundColor: creditDotColor }"></span>
              <span class="font-label text-xs font-medium text-[var(--app-ink)]">{{ creditIconValue }}</span>
            </span>
          </button>
          <!-- Desktop popover -->
          <div
            v-if="showCreditsPopover && !isMobile"
            class="app-card absolute bottom-0 left-full z-50 ml-3 w-72 p-4 shadow-[var(--app-shadow-soft)]"
            @mouseenter="handleMouseEnter"
            @mouseleave="handleMouseLeave"
            @click.stop
          >
            <p class="app-label">Crédits restants</p>
            <p class="font-display mt-1 text-3xl font-semibold text-[var(--app-ink)]">{{ creditIconValue }}</p>
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
      </template>
    </nav>

    <!-- Footer: theme, user, logout -->
    <div class="border-t border-[var(--app-line)] px-4 py-3">
      <!-- Theme switch -->
      <div class="mb-2 flex items-center justify-between px-2">
        <span class="app-label !text-[0.6rem]">Thème</span>
        <div class="flex items-center gap-1 rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] p-0.5">
          <button type="button" :class="themeButtonClass('light')" aria-label="Thème clair" @click="setTheme('light')">
            <UIcon name="i-lucide-sun" class="h-3.5 w-3.5" />
          </button>
          <button type="button" :class="themeButtonClass('dark')" aria-label="Thème sombre" @click="setTheme('dark')">
            <UIcon name="i-lucide-moon" class="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <!-- User -->
      <button
        class="group flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left transition-colors hover:bg-[var(--app-surface-2)]"
        @click="handleProfile"
      >
        <span
          class="font-label flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--app-ink)] text-[0.65rem] font-semibold text-[var(--app-surface)]"
        >
          {{ userInitials }}
        </span>
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-medium text-[var(--app-ink)]">{{ userName }}</span>
          <span class="block truncate text-xs text-[var(--app-ink-soft)]">{{ userEmail }}</span>
        </span>
      </button>

      <button
        class="mt-1 flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-[var(--app-red)] transition-colors hover:bg-[var(--app-red-soft)]"
        @click="handleLogout"
      >
        <UIcon name="i-lucide-log-out" class="h-3.5 w-3.5" />
        Déconnexion
      </button>
    </div>
  </aside>

  <!-- Overlay for mobile -->
  <div
    v-if="isOpen && isMobile"
    class="fixed inset-0 z-30 bg-[var(--app-overlay)] md:hidden"
    @click="$emit('toggle')"
  />
</template>

<script setup lang="ts">
import type { ComputedRef, Ref } from 'vue'
import type { AppTheme } from '~/types/AppTheme'
import type { DlhModuleEntry, UiSidebarGroup, UiSidebarProps } from '~/types/UiSidebar'
import { ref, computed } from 'vue'
import { useUserStore } from '~/stores/user'
import { useAuth } from '~/composables/useAuth'
import { useAppTheme } from '~/composables/useAppTheme'
import { useToast } from '~/composables/useToast'

/**
 * Defines the component props.
 */
const props: UiSidebarProps = defineProps({
  isOpen: {
    type: Boolean,
    required: true,
  },
  isMobile: {
    type: Boolean,
    required: true,
  },
})

const emit = defineEmits<{
  (e: 'toggle'): void
}>()

/** User store instance. */
const userStore = useUserStore()

const toast = useToast()

const { logout } = useAuth()

const { theme, toggleTheme } = useAppTheme()

const {
  isAdmin,
  isAdminNavOpen,
  isAdminNavActive,
  isMobileAdminPanel,
  adminLinks,
  openAdminNav,
  closeAdminNav,
  isLinkActive,
} = useAdminNav()

/** Whether the Administration sub-panel replaces the main sidebar menu. */
const showAdminPanel: ComputedRef<boolean> = computed((): boolean => {
  return props.isMobile ? isMobileAdminPanel.value : isAdminNavOpen.value
})

/** Whether the Settings sub-panel is currently open. */
const showSettingsPanel: Ref<boolean> = ref<boolean>(false)

/** Whether the module switcher menu is open. */
const showModuleMenu: Ref<boolean> = ref<boolean>(false)

/** The three product modules of DevLeadHunter (only websites is live today). */
const modules: DlhModuleEntry[] = [
  { key: 'websites', label: 'Sites web', icon: 'i-lucide-globe', locked: false },
  { key: 'wallet-cards', label: 'Cartes Apple Wallet', icon: 'i-lucide-wallet-cards', locked: true },
  { key: 'freelance-missions', label: 'Missions freelance', icon: 'i-lucide-briefcase-business', locked: true },
]

/** Label of the currently active module. */
const activeModuleLabel: ComputedRef<string> = computed((): string => {
  return modules.find((moduleEntry: DlhModuleEntry): boolean => !moduleEntry.locked)?.label ?? 'Sites web'
})

/**
 * Handle a click on a module entry: locked modules announce their arrival,
 * the active one simply closes the menu.
 * @param moduleEntry - The clicked module.
 */
function handleModuleClick(moduleEntry: DlhModuleEntry): void {
  showModuleMenu.value = false
  if (moduleEntry.locked) {
    toast.info(`Le module « ${moduleEntry.label} » arrive bientôt.`)
  }
}

/** Credits popover visibility state. */
const showCreditsPopover: Ref<boolean> = ref<boolean>(false)

/** Popover hover state. */
const isHoveringPopover: Ref<boolean> = ref<boolean>(false)

/** Pending popover close timer. */
let hoverTimeout: ReturnType<typeof setTimeout> | null = null

/** Grouped navigation of the websites module. */
const navGroups: ComputedRef<UiSidebarGroup[]> = computed((): UiSidebarGroup[] => {
  const groups: UiSidebarGroup[] = [
    {
      heading: 'Pilotage',
      links: [{ to: '/dashboard', label: 'Tableau de bord', icon: 'i-lucide-layout-dashboard' }],
    },
    {
      heading: 'Prospection',
      links: [
        { to: '/dashboard/my-prospects', label: 'Mes prospects', icon: 'i-lucide-users' },
        { to: '/dashboard/search-prospects', label: 'Rechercher', icon: 'i-lucide-search' },
      ],
    },
    {
      heading: 'Production',
      links: [{ to: '/dashboard/demo-sites', label: 'Sites démo', icon: 'i-lucide-app-window' }],
    },
    {
      heading: 'Campagnes',
      links: [
        { to: '/dashboard/campaigns', label: 'Campagnes', icon: 'i-lucide-megaphone' },
        { to: '/dashboard/emails', label: 'Emails envoyés', icon: 'i-lucide-send' },
        { to: '/dashboard/email-templates', label: 'Templates email', icon: 'i-lucide-layout-template' },
      ],
    },
    {
      heading: 'Ventes',
      links: [{ to: '/dashboard/orders', label: 'Ventes', icon: 'i-lucide-banknote' }],
    },
  ]

  // Support stays available to regular users in the main menu (admins have it
  // in the Administration panel).
  if (!isAdmin.value) {
    groups.push({
      heading: 'Aide',
      links: [{ to: '/dashboard/support', label: 'Support', icon: 'i-lucide-life-buoy' }],
    })
  }

  return groups
})

/** User display name. */
const userName: ComputedRef<string> = computed((): string => {
  return userStore.userName || 'User'
})

/** User email. */
const userEmail: ComputedRef<string> = computed((): string => {
  return userStore.userEmail
})

/** User initials shown in the avatar circle. */
const userInitials: ComputedRef<string> = computed((): string => {
  const name: string = userName.value
  if (!name) return 'U'
  const parts: string[] = name.split(' ')
  if (parts.length >= 2 && parts[0] && parts[1]) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
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
 * Classes of a navigation row for a given active state.
 * @param active - Whether the row matches the current route.
 * @returns Tailwind classes for the row.
 */
function navItemClass(active: boolean): string {
  const base =
    'relative flex cursor-pointer items-center gap-2.5 rounded-lg py-1.5 pr-3 pl-4 text-sm font-medium transition-colors'
  if (active) {
    return `${base} bg-[var(--app-surface-2)] text-[var(--app-ink)]`
  }
  return `${base} text-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]`
}

/**
 * Classes of the amber active indicator bar of a navigation row.
 * @param active - Whether the row matches the current route.
 * @returns Tailwind classes for the indicator.
 */
function navBarClass(active: boolean): string {
  const base = 'absolute top-1/2 left-1 h-4 w-0.5 -translate-y-1/2 rounded-full transition-colors'
  return active ? `${base} bg-[var(--app-accent)]` : `${base} bg-transparent`
}

/**
 * Classes of a theme-switch segment button.
 * @param value - The theme this button activates.
 * @returns Tailwind classes for the segment.
 */
function themeButtonClass(value: AppTheme): string {
  const base = 'flex h-6 w-6 cursor-pointer items-center justify-center rounded-full transition-colors'
  if (theme.value === value) {
    return `${base} bg-[var(--app-ink)] text-[var(--app-surface)]`
  }
  return `${base} text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]`
}

/**
 * Activate a specific theme (no-op when already active).
 * @param value - Target theme.
 */
function setTheme(value: AppTheme): void {
  if (theme.value !== value) {
    toggleTheme()
  }
}

/**
 * Toggle the credits popover (click).
 */
function toggleCreditsPopover(): void {
  showCreditsPopover.value = !showCreditsPopover.value
}

/**
 * Open the credits popover on hover (desktop).
 */
function handleMouseEnter(): void {
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
 * Close the credits popover shortly after the pointer leaves (desktop).
 */
function handleMouseLeave(): void {
  if (!props.isMobile) {
    isHoveringPopover.value = false
    hoverTimeout = setTimeout((): void => {
      if (!isHoveringPopover.value) {
        showCreditsPopover.value = false
      }
    }, 100)
  }
}

/**
 * Whether a route is active (exact, or a sub-route for non-root paths).
 * @param path - Route path to check.
 * @returns True if the route is active.
 */
function isActive(path: string): boolean {
  const route = useRoute()
  if (route.path === path) return true
  if (path !== '/dashboard' && route.path.startsWith(path + '/')) return true
  return false
}

/**
 * Close the sidebar after a navigation on mobile.
 */
function handleClick(): void {
  if (props.isMobile) {
    emit('toggle')
  }
}

/**
 * Close the Administration sub-panel and return to the main menu.
 */
function handleAdminBack(): void {
  closeAdminNav(props.isMobile)
}

/**
 * Open the Administration sub-panel inside the sidebar.
 */
function handleAdminClick(): void {
  openAdminNav(props.isMobile)
}

/**
 * Open the profile page.
 */
function handleProfile(): void {
  navigateTo('/profile')
  handleClick()
}

/**
 * Log the user out.
 */
function handleLogout(): void {
  logout()
  handleClick()
}
</script>
