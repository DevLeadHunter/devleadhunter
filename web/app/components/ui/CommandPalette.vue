<template>
  <Teleport to="body">
    <Transition name="palette-fade">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[70] flex items-start justify-center bg-[var(--app-overlay)] px-4 pt-[14vh] backdrop-blur-sm"
        @click.self="close()"
      >
        <div class="app-card w-full max-w-xl overflow-hidden p-0 shadow-[var(--app-shadow-soft)]">
          <!-- Search input -->
          <div class="flex items-center gap-3 border-b border-[var(--app-line)] px-4 py-3">
            <UIcon name="i-lucide-search" class="h-4 w-4 shrink-0 text-[var(--app-faint)]" />
            <input
              ref="searchInput"
              v-model="query"
              type="text"
              placeholder="Rechercher une page, un prospect, une campagne…"
              class="w-full border-0 bg-transparent text-sm text-[var(--app-ink)] placeholder-[var(--app-faint)] focus:ring-0 focus:outline-none"
              @keydown="handleInputKeydown"
            />
            <span
              class="font-label shrink-0 rounded border border-[var(--app-line)] bg-[var(--app-bg)] px-1.5 py-0.5 text-[9px] text-[var(--app-ink-soft)] uppercase"
            >
              Échap
            </span>
          </div>

          <!-- Results -->
          <div ref="resultsContainer" class="max-h-[50vh] overflow-y-auto p-1.5">
            <template v-for="group in visibleGroups" :key="group.key">
              <p class="app-label px-2.5 pt-2.5 pb-1 !text-[0.6rem]">{{ group.heading }}</p>
              <button
                v-for="item in group.items"
                :key="item.id"
                type="button"
                :data-palette-index="item.flatIndex"
                :class="[
                  'flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors',
                  item.flatIndex === activeIndex
                    ? 'bg-[var(--app-surface-2)] text-[var(--app-ink)]'
                    : 'text-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]',
                ]"
                @click="runItem(item)"
                @mousemove="activeIndex = item.flatIndex"
              >
                <UIcon :name="item.icon" class="h-4 w-4 shrink-0 text-[var(--app-ink-soft)]" />
                <span class="min-w-0 flex-1 truncate font-medium">{{ item.label }}</span>
                <span v-if="item.meta" class="text-muted shrink-0 truncate text-xs">{{ item.meta }}</span>
              </button>
            </template>

            <p v-if="totalResults === 0" class="text-muted px-2.5 py-6 text-center text-sm">
              Aucun résultat pour « {{ query }} ».
            </p>
          </div>

          <!-- Footer hint -->
          <div class="text-muted flex items-center gap-3 border-t border-[var(--app-line)] px-4 py-2 text-[10px]">
            <span>↑↓ naviguer</span>
            <span>Entrée ouvrir</span>
            <span class="ml-auto flex items-center gap-1.5">
              <LandingAsterisk class="text-[0.55rem] text-[var(--app-accent)]" />
              devleadhunter
            </span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { CampaignResponse } from '~/services/campaignService'
import type { Prospect } from '~/types'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { campaignService } from '~/services/campaignService'
import { listProspects } from '~/services/prospectsService'
import { useAppTheme } from '~/composables/useAppTheme'
import { useCommandPalette } from '~/composables/useCommandPalette'
import { useDrawerStackStore } from '~/stores/drawerStack'

/** One actionable row of the palette. */
interface PaletteItem {
  id: string
  label: string
  icon: string
  meta?: string
  /** Extra text matched by the search (city, email…). */
  keywords?: string
  run: () => void
  flatIndex: number
}

/** One displayed group of palette rows. */
interface PaletteGroup {
  key: string
  heading: string
  items: PaletteItem[]
}

const { isOpen, close } = useCommandPalette()

const drawerStack = useDrawerStackStore()

const { toggleTheme } = useAppTheme()

const query: Ref<string> = ref<string>('')
const activeIndex: Ref<number> = ref<number>(0)
const searchInput: Ref<HTMLInputElement | null> = ref<HTMLInputElement | null>(null)
const resultsContainer: Ref<HTMLDivElement | null> = ref<HTMLDivElement | null>(null)

/** Cached data sources (loaded on first open). */
const prospects: Ref<Prospect[]> = ref<Prospect[]>([])
const campaigns: Ref<CampaignResponse[]> = ref<CampaignResponse[]>([])
const hasLoadedSources: Ref<boolean> = ref<boolean>(false)

/** Static navigation entries. */
const PAGES: ReadonlyArray<{ label: string; icon: string; to: string }> = [
  { label: 'Tableau de bord', icon: 'i-lucide-layout-dashboard', to: '/dashboard' },
  { label: 'Mes prospects', icon: 'i-lucide-users', to: '/dashboard/my-prospects' },
  { label: 'Trouver des prospects', icon: 'i-lucide-search', to: '/dashboard/search-prospects' },
  { label: 'Sites démo', icon: 'i-lucide-app-window', to: '/dashboard/demo-sites' },
  { label: 'Campagnes', icon: 'i-lucide-megaphone', to: '/dashboard/campaigns' },
  { label: 'Suivi des emails', icon: 'i-lucide-send', to: '/dashboard/emails' },
  { label: "Modèles d'email", icon: 'i-lucide-layout-template', to: '/dashboard/email-templates' },
  { label: 'Ventes', icon: 'i-lucide-banknote', to: '/dashboard/orders' },
  { label: 'Support', icon: 'i-lucide-life-buoy', to: '/dashboard/support' },
  { label: 'Comptes email', icon: 'i-lucide-at-sign', to: '/dashboard/email-accounts' },
  { label: 'Configuration Resend', icon: 'i-lucide-mail-open', to: '/dashboard/settings/resend' },
]

/**
 * Normalize a string for accent-insensitive matching.
 * @param value - Raw string.
 * @returns Lowercased string without diacritics.
 */
function normalize(value: string): string {
  return value.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
}

/**
 * Whether an item matches the current query.
 * @param label - Item label.
 * @param keywords - Extra searchable text.
 * @returns True when every query word is found.
 */
function matches(label: string, keywords = ''): boolean {
  const haystack: string = normalize(`${label} ${keywords}`)
  return normalize(query.value)
    .split(/\s+/)
    .filter(Boolean)
    .every((word: string): boolean => haystack.includes(word))
}

/** Groups currently displayed (filtered by the query, flat-indexed). */
const visibleGroups: ComputedRef<PaletteGroup[]> = computed((): PaletteGroup[] => {
  const groups: PaletteGroup[] = []
  let flatIndex = 0

  /**
   * Append a group when it has matching items.
   * @param key - Stable group key.
   * @param heading - Visible group heading.
   * @param items - Candidate items (without flat index).
   */
  function pushGroup(key: string, heading: string, items: Array<Omit<PaletteItem, 'flatIndex'>>): void {
    const kept: PaletteItem[] = items
      .filter((item: Omit<PaletteItem, 'flatIndex'>): boolean => !query.value || matches(item.label, item.keywords))
      .map((item: Omit<PaletteItem, 'flatIndex'>): PaletteItem => ({ ...item, flatIndex: flatIndex++ }))
    if (kept.length) groups.push({ key, heading, items: kept })
  }

  pushGroup('actions', 'Actions', [
    {
      id: 'action-create-site',
      label: 'Créer un site',
      icon: 'i-lucide-plus',
      keywords: 'website builder tunnel démo',
      run: (): void => {
        navigateTo('/dashboard/demo-sites/create')
      },
    },
    {
      id: 'action-send-email',
      label: 'Envoyer un email',
      icon: 'i-lucide-send',
      keywords: 'composer mail',
      run: (): void => {
        drawerStack.push({ kind: 'send-email', prospect: null })
      },
    },
    {
      id: 'action-new-template',
      label: "Nouveau modèle d'email",
      icon: 'i-lucide-layout-template',
      keywords: 'template',
      run: (): void => {
        drawerStack.push({ kind: 'email-template', mode: 'create', template: null })
      },
    },
    {
      id: 'action-add-prospect',
      label: 'Ajouter un prospect',
      icon: 'i-lucide-user-plus',
      keywords: 'nouveau manuel',
      run: (): void => {
        drawerStack.push({ kind: 'add-prospect' })
      },
    },
    {
      id: 'action-new-campaign',
      label: 'Nouvelle campagne',
      icon: 'i-lucide-megaphone',
      keywords: 'créer cold email',
      run: (): void => {
        drawerStack.push({ kind: 'create-campaign' })
      },
    },
    {
      id: 'action-profile',
      label: 'Mon profil',
      icon: 'i-lucide-user-round',
      keywords: 'compte nom email',
      run: (): void => {
        drawerStack.push({ kind: 'profile' })
      },
    },
    {
      id: 'action-organization',
      label: 'Organisation',
      icon: 'i-lucide-users-round',
      keywords: 'équipe team membres inviter',
      run: (): void => {
        drawerStack.push({ kind: 'organization' })
      },
    },
    {
      id: 'action-toggle-theme',
      label: 'Basculer le thème clair / sombre',
      icon: 'i-lucide-sun-moon',
      keywords: 'dark light mode',
      run: (): void => {
        toggleTheme()
      },
    },
  ])

  pushGroup(
    'pages',
    'Pages',
    PAGES.map((page: { label: string; icon: string; to: string }): Omit<PaletteItem, 'flatIndex'> => {
      return {
        id: `page-${page.to}`,
        label: page.label,
        icon: page.icon,
        run: (): void => {
          navigateTo(page.to)
        },
      }
    }),
  )

  if (query.value) {
    pushGroup(
      'prospects',
      'Prospects',
      prospects.value.slice(0, 400).map((prospect: Prospect): Omit<PaletteItem, 'flatIndex'> => {
        return {
          id: `prospect-${prospect.id}`,
          label: prospect.name,
          icon: 'i-lucide-store',
          meta: prospect.city ?? undefined,
          keywords: `${prospect.city ?? ''} ${prospect.email ?? ''} ${prospect.category}`,
          run: (): void => {
            drawerStack.push({ kind: 'prospect', prospect })
          },
        }
      }),
    )

    pushGroup(
      'campaigns',
      'Campagnes',
      campaigns.value.map((campaign: CampaignResponse): Omit<PaletteItem, 'flatIndex'> => {
        return {
          id: `campaign-${campaign.id}`,
          label: campaign.name,
          icon: 'i-lucide-megaphone',
          meta: `${campaign.prospects_count} prospect${campaign.prospects_count > 1 ? 's' : ''}`,
          keywords: campaign.description ?? '',
          run: (): void => {
            navigateTo(`/dashboard/campaigns/${campaign.id}`)
          },
        }
      }),
    )
  }

  // Cap la longueur des groupes dynamiques pour rester lisible.
  return groups.map((group: PaletteGroup): PaletteGroup => {
    if (group.key === 'prospects' || group.key === 'campaigns') {
      return { ...group, items: group.items.slice(0, 6) }
    }
    return group
  })
})

/** Flat list of displayed items (keyboard navigation target). */
const flatItems: ComputedRef<PaletteItem[]> = computed((): PaletteItem[] => {
  return visibleGroups.value.flatMap((group: PaletteGroup): PaletteItem[] => group.items)
})

/** Number of displayed results. */
const totalResults: ComputedRef<number> = computed((): number => flatItems.value.length)

/**
 * Execute an item then close the palette.
 * @param item - Selected palette row.
 */
function runItem(item: PaletteItem): void {
  close()
  item.run()
}

/**
 * Load the dynamic sources once (prospects + campaigns), errors ignored.
 * @returns Resolves when both fetches settled.
 */
async function loadSources(): Promise<void> {
  if (hasLoadedSources.value) return
  hasLoadedSources.value = true
  const [prospectsResult, campaignsResult] = await Promise.all([
    listProspects().catch((): Prospect[] => []),
    campaignService.list(0, 200).then(
      (response: { campaigns: CampaignResponse[] }): CampaignResponse[] => response.campaigns,
      (): CampaignResponse[] => [],
    ),
  ])
  prospects.value = prospectsResult
  campaigns.value = campaignsResult
}

/**
 * Keyboard navigation inside the search input.
 * @param event - Keyboard event.
 */
function handleInputKeydown(event: KeyboardEvent): void {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeIndex.value = Math.min(activeIndex.value + 1, totalResults.value - 1)
    scrollActiveIntoView()
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    activeIndex.value = Math.max(activeIndex.value - 1, 0)
    scrollActiveIntoView()
  } else if (event.key === 'Enter') {
    event.preventDefault()
    const item: PaletteItem | undefined = flatItems.value[activeIndex.value]
    if (item) runItem(item)
  }
}

/** Keep the active row visible while navigating with the arrows. */
function scrollActiveIntoView(): void {
  void nextTick((): void => {
    const row: HTMLElement | null | undefined = resultsContainer.value?.querySelector(
      `[data-palette-index="${activeIndex.value}"]`,
    )
    row?.scrollIntoView({ block: 'nearest' })
  })
}

/**
 * Global shortcuts: Ctrl/Cmd+K toggles, Escape closes (captured before the
 * drawer stack's own Escape handler).
 * @param event - Keyboard event.
 */
function handleGlobalKeydown(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    isOpen.value = !isOpen.value
    return
  }
  if (event.key === 'Escape' && isOpen.value) {
    event.preventDefault()
    close()
  }
}

watch(isOpen, (open: boolean): void => {
  if (open) {
    query.value = ''
    activeIndex.value = 0
    void loadSources()
    void nextTick((): void => {
      searchInput.value?.focus()
    })
  }
})

watch(query, (): void => {
  activeIndex.value = 0
})

onMounted((): void => {
  window.addEventListener('keydown', handleGlobalKeydown, { capture: true })
})

onBeforeUnmount((): void => {
  window.removeEventListener('keydown', handleGlobalKeydown, { capture: true })
})
</script>

<style scoped>
.palette-fade-enter-active,
.palette-fade-leave-active {
  transition: opacity 0.15s ease;
}
.palette-fade-enter-from,
.palette-fade-leave-to {
  opacity: 0;
}
</style>
