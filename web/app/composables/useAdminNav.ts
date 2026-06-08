export interface AdminNavLink {
  to: string
  label: string
  icon: string
}

export const ADMIN_NAV_LINKS: AdminNavLink[] = [
  { to: '/dashboard/users', label: 'Users', icon: 'fa-solid fa-users' },
  { to: '/dashboard/credits', label: 'Mes crédits', icon: 'fa-solid fa-coins' },
  { to: '/dashboard/buy-credits', label: 'Acheter des crédits', icon: 'fa-solid fa-credit-card' },
  { to: '/dashboard/credit-settings', label: 'Credit Settings', icon: 'fa-solid fa-sliders' },
  { to: '/dashboard/support', label: 'Support', icon: 'fa-solid fa-headset' },
  { to: '/dashboard/accounting', label: 'Comptabilité', icon: 'fa-solid fa-calculator' },
]

/**
 * Shared state and helpers for the Administration in-sidebar navigation panel.
 */
export function useAdminNav() {
  const route = useRoute()
  const userStore = useUserStore()

  const isAdmin = computed(() => userStore.user?.role === 'ADMIN')
  const isAdminNavOpen = useState('admin-nav-open', () => false)
  const isMobileAdminPanel = useState('admin-mobile-panel', () => false)

  const matchesAdminPath = (path: string): boolean => {
    if (route.path === path) return true
    return route.path.startsWith(`${path}/`)
  }

  const isAdminSection = computed(() => isAdmin.value && ADMIN_NAV_LINKS.some((link) => matchesAdminPath(link.to)))

  const isAdminNavActive = computed(() => isAdminNavOpen.value || isAdminSection.value)

  watch(
    () => route.path,
    () => {
      if (isAdminSection.value) {
        isAdminNavOpen.value = true
      }
    },
    { immediate: true },
  )

  const openAdminNav = (mobile = false): void => {
    if (mobile) {
      isMobileAdminPanel.value = true
      return
    }

    isAdminNavOpen.value = true
    if (!isAdminSection.value) {
      navigateTo(ADMIN_NAV_LINKS[0]!.to)
    }
  }

  const closeAdminNav = (mobile = false): void => {
    if (mobile) {
      isMobileAdminPanel.value = false
      return
    }

    isAdminNavOpen.value = false
  }

  const isLinkActive = (path: string): boolean => matchesAdminPath(path)

  return {
    isAdmin,
    isAdminNavOpen,
    isMobileAdminPanel,
    isAdminSection,
    isAdminNavActive,
    adminLinks: ADMIN_NAV_LINKS,
    openAdminNav,
    closeAdminNav,
    isLinkActive,
  }
}
