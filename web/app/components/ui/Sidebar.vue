<template>
  <aside
    :class="[
      'fixed top-0 left-0 z-40 flex h-full w-64 flex-col border-r border-[var(--app-line)] bg-[var(--app-surface)] transition-transform duration-300',
      isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
    ]"
  >
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

    <div class="px-4 pt-3">
      <NuxtLink to="/dashboard/automations/new" class="app-btn-primary h-8 min-h-8 w-full text-xs" @click="handleClick">
        <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
        Créer une automatisation
      </NuxtLink>
    </div>

    <div class="px-4 pt-2">
      <button
        type="button"
        class="flex w-full cursor-pointer items-center justify-between rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-2.5 py-1.5 text-xs text-[var(--app-faint)] transition-colors hover:border-[var(--app-ink-soft)] hover:text-[var(--app-ink-soft)]"
        @click="commandPalette.open()"
      >
        <span class="flex items-center gap-2">
          <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
          Rechercher…
        </span>
        <span
          class="font-label rounded border border-[var(--app-line)] bg-[var(--app-surface)] px-1 py-0.5 text-[9px] uppercase"
        >
          Ctrl K
        </span>
      </button>
    </div>

    <nav class="flex flex-1 flex-col overflow-y-auto px-4 py-3">
      <template v-if="showSettingsPanel">
        <button
          type="button"
          class="mb-3 flex w-full cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-sm font-semibold text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
          @click="closeSettingsPanel"
        >
          <UIcon name="i-lucide-chevron-left" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
          <span>Menu principal</span>
        </button>
        <div v-for="group in settingsGroups" :key="group.heading" class="mb-4 last:mb-0">
          <p class="app-label mb-1.5 px-3 !text-[0.6rem]">{{ group.heading }}</p>
          <div class="space-y-0.5">
            <template v-for="entry in group.entries" :key="entry.kind === 'link' ? entry.to : entry.action">
              <NuxtLink
                v-if="entry.kind === 'link'"
                :to="entry.to"
                :class="navItemClass(isSettingsLinkActive(entry.to))"
                @click="handleClick"
              >
                <span :class="navBarClass(isSettingsLinkActive(entry.to))"></span>
                <UIcon :name="entry.icon" class="h-4 w-4 shrink-0" />
                <span class="truncate">{{ entry.label }}</span>
              </NuxtLink>
              <button
                v-else
                type="button"
                class="w-full"
                :class="navItemClass(false)"
                @click="handleSettingsAction(entry.action)"
              >
                <span :class="navBarClass(false)"></span>
                <UIcon :name="entry.icon" class="h-4 w-4 shrink-0" />
                <span>{{ entry.label }}</span>
              </button>
            </template>
          </div>
        </div>
      </template>

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

        <div class="mb-4">
          <p class="app-label mb-1.5 px-3 !text-[0.6rem]">Réglages</p>
          <div class="space-y-0.5">
            <button type="button" :class="navItemClass(false)" class="w-full" @click="openSettingsPanel">
              <span :class="navBarClass(false)"></span>
              <UIcon name="i-lucide-settings" class="h-4 w-4 shrink-0" />
              <span>Paramètres</span>
              <UIcon name="i-lucide-chevron-right" class="ml-auto h-3.5 w-3.5 opacity-50" />
            </button>
          </div>
        </div>

        <NuxtLink
          v-if="!isMobile"
          to="/dashboard/buy-credits"
          class="group mt-auto flex items-center justify-between rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2 transition-colors hover:border-[var(--app-ink-soft)]"
        >
          <span class="flex flex-col gap-0.5">
            <span class="app-label !text-[0.6rem]">Crédits</span>
            <span class="flex items-center gap-2">
              <span class="h-2.5 w-2.5 rounded-full" :style="{ backgroundColor: creditDotColor }"></span>
              <UIcon v-if="hasUnlimitedCredits" name="i-lucide-infinity" class="h-5 w-5 text-[var(--app-ink)]" />
              <span v-else class="font-label text-lg leading-tight font-semibold text-[var(--app-ink)]">{{
                creditBalanceLabel
              }}</span>
            </span>
          </span>
          <span
            class="app-label flex items-center gap-1 !text-[0.6rem] transition-colors group-hover:!text-[var(--app-ink)]"
          >
            Recharger
            <UIcon name="i-lucide-arrow-right" class="h-3 w-3" />
          </span>
        </NuxtLink>
      </template>
    </nav>

    <div class="relative border-t border-[var(--app-line)] px-4 py-3">
      <div v-if="showUserMenu" class="fixed inset-0 z-40" @click="showUserMenu = false"></div>

      <div
        v-if="showUserMenu"
        class="app-card absolute inset-x-4 bottom-full z-50 mb-1.5 p-1 shadow-[var(--app-shadow-soft)]"
      >
        <button
          type="button"
          class="flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
          @click="handleProfileFromMenu"
        >
          <UIcon name="i-lucide-user-round" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
          Profil
        </button>

        <button
          type="button"
          class="flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
          @click="handleOrganizationFromMenu"
        >
          <UIcon name="i-lucide-users-round" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
          Organisation
        </button>

        <div class="flex items-center justify-between rounded-md px-2 py-1.5">
          <span class="flex items-center gap-2 text-xs font-medium text-[var(--app-ink)]">
            <UIcon name="i-lucide-sun-moon" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
            Thème
          </span>
          <span class="flex items-center gap-1 rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] p-0.5">
            <button
              type="button"
              :class="themeButtonClass('light')"
              aria-label="Thème clair"
              @click="setTheme('light')"
            >
              <UIcon name="i-lucide-sun" class="h-3.5 w-3.5" />
            </button>
            <button type="button" :class="themeButtonClass('dark')" aria-label="Thème sombre" @click="setTheme('dark')">
              <UIcon name="i-lucide-moon" class="h-3.5 w-3.5" />
            </button>
          </span>
        </div>

        <div class="my-1 border-t border-[var(--app-line)]"></div>

        <NuxtLink
          v-if="!isDesktopApp"
          to="/downloads"
          target="_blank"
          class="flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
          @click="showUserMenu = false"
        >
          <UIcon name="i-lucide-monitor-down" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
          Télécharger l'app
        </NuxtLink>

        <button
          type="button"
          class="flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs font-medium text-[var(--app-red)] transition-colors hover:bg-[var(--app-red-soft)]"
          @click="handleLogout"
        >
          <UIcon name="i-lucide-log-out" class="h-3.5 w-3.5" />
          Déconnexion
        </button>
      </div>

      <button
        class="group flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2 py-2 text-left transition-colors hover:bg-[var(--app-surface-2)]"
        :aria-expanded="showUserMenu"
        aria-label="Ouvrir le menu du compte"
        @click.stop="showUserMenu = !showUserMenu"
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
        <UIcon name="i-lucide-chevrons-up-down" class="h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)]" />
      </button>
    </div>
  </aside>

  <div
    v-if="isOpen && isMobile"
    class="fixed inset-0 z-30 bg-[var(--app-overlay)] md:hidden"
    @click="$emit('toggle')"
  />
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { AppTheme } from '~/types/AppTheme'
import type { DlhModuleEntry, UiSidebarGroup, UiSidebarProps } from '~/types/UiSidebar'
import { ref, computed } from 'vue'
import { useUserStore } from '~/stores/user'
import { useAuth } from '~/composables/useAuth'
import { useAppTheme } from '~/composables/useAppTheme'
import { useCommandPalette } from '~/composables/useCommandPalette'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useToast } from '~/composables/useToast'

/** Dashboard sidebar shell with nav groups and user menu. */
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

/** Global Ctrl+K command palette (opened from the sidebar trigger). */
const commandPalette = useCommandPalette()

/** Persistent drawer stack — the profile entry opens from the user menu. */
const drawerStack = useDrawerStackStore()

/** Tauri desktop detection → hide the "download the app" link when already in the desktop app. */
const { isDesktopApp } = useDesktopRuntime()

const {
  showSettingsPanel,
  settingsGroups,
  openSettingsPanel,
  closeSettingsPanel,
  isLinkActive: isSettingsLinkActive,
} = useSettingsNav()

/** Whether the module switcher menu is open. */
const showModuleMenu: Ref<boolean> = ref(false)

/** Whether the user account menu (Profil / Thème / Déconnexion) is open. */
const showUserMenu: Ref<boolean> = ref(false)

/** The three product modules of DevLeadHunter (only websites is live today). */
const modules: DlhModuleEntry[] = [
  { key: 'websites', label: 'Sites web', icon: 'i-lucide-globe', locked: false },
  { key: 'wallet-cards', label: 'Cartes Apple Wallet', icon: 'i-lucide-wallet-cards', locked: true },
  { key: 'freelance-missions', label: 'Missions freelance', icon: 'i-lucide-briefcase-business', locked: true },
]

const navGroups: UiSidebarGroup[] = [
  {
    heading: 'Pilotage',
    links: [
      { to: '/dashboard', label: 'Tableau de bord', icon: 'i-lucide-layout-dashboard' },
      { to: '/dashboard/automations', label: 'Automatisations', icon: 'i-lucide-workflow' },
    ],
  },
  {
    heading: 'Prospection',
    links: [
      { to: '/dashboard/my-prospects', label: 'Mes prospects', icon: 'i-lucide-users' },
      { to: '/dashboard/coverage', label: 'Carte de prospection', icon: 'i-lucide-map' },
      { to: '/dashboard/demo-sites', label: 'Sites démo', icon: 'i-lucide-app-window' },
      { to: '/dashboard/campaigns', label: 'Campagnes', icon: 'i-lucide-megaphone' },
      { to: '/dashboard/emails', label: 'Suivi des emails', icon: 'i-lucide-send' },
      { to: '/dashboard/orders', label: 'Ventes', icon: 'i-lucide-banknote' },
    ],
  },
]

/** Label of the currently active module. */
const activeModuleLabel: ComputedRef<string> = computed((): string => {
  return modules.find((moduleEntry: DlhModuleEntry): boolean => !moduleEntry.locked)?.label ?? 'Sites web'
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

/** Raw credit balance (null when the field is missing). */
const creditBalance: ComputedRef<number | null> = computed((): number | null => {
  return userStore.user?.credits_available ?? userStore.user?.credit_balance ?? null
})

/** Whether the account has an unlimited plan. */
const hasUnlimitedCredits: ComputedRef<boolean> = computed((): boolean => creditBalance.value === -1)

/** Credits balance shown in the credits card (the unlimited case renders an infinity icon instead). */
const creditBalanceLabel: ComputedRef<string> = computed((): string => {
  return (creditBalance.value ?? 0).toString()
})

/** Semantic dot colour next to the credits counter. */
const creditDotColor: ComputedRef<string> = computed((): string => {
  if (hasUnlimitedCredits.value) return 'var(--app-ink-soft)'
  const credits: number | null = creditBalance.value
  if (credits === null || credits === 0 || credits <= 10) return 'var(--app-red)'
  return 'var(--app-green)'
})

/**
 * Handle a click on a module entry: locked modules announce their arrival.
 * @param moduleEntry - The clicked module.
 */
function handleModuleClick(moduleEntry: DlhModuleEntry): void {
  showModuleMenu.value = false
  if (moduleEntry.locked) {
    toast.info(`Le module « ${moduleEntry.label} » arrive bientôt.`)
  }
}

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
 * Handle a settings sub-panel action entry (opens the matching drawer).
 * @param action - The action key of the settings entry.
 */
function handleSettingsAction(action: 'send-policy'): void {
  if (action === 'send-policy') {
    drawerStack.push({ kind: 'send-policy' })
  }
  handleClick()
}

/**
 * Open the profile edit drawer from the user menu (no page navigation).
 */
function handleProfileFromMenu(): void {
  showUserMenu.value = false
  drawerStack.push({ kind: 'profile' })
  handleClick()
}

/**
 * Open the organization (team) drawer from the user menu (no page navigation).
 */
function handleOrganizationFromMenu(): void {
  showUserMenu.value = false
  drawerStack.push({ kind: 'organization' })
  handleClick()
}

/**
 * Log the user out.
 */
function handleLogout(): void {
  showUserMenu.value = false
  logout()
  handleClick()
}
</script>
