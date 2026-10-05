<template>
  <div>
    <UiPageHeader
      eyebrow="Prospection"
      :has-eyebrow-mark="false"
      title="Sites démo"
      description="Générez des sites vitrines pour vos prospects — 21 jours en ligne à partir du premier email envoyé"
      class="mb-8"
    >
      <template #primary-action>
        <NuxtLink
          to="/dashboard/demo-sites/create"
          class="app-btn-primary h-11 px-4 text-sm whitespace-nowrap @2xl:h-9 @2xl:text-xs"
        >
          <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
          Créer un site
        </NuxtLink>
      </template>
    </UiPageHeader>

    <div v-if="pending" class="grid gap-4 @2xl:grid-cols-2 @5xl:grid-cols-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse">
        <div class="h-36 bg-[var(--app-surface-2)]"></div>
        <div class="space-y-3 p-5">
          <div class="h-4 w-2/3 rounded bg-[var(--app-surface-2)]"></div>
          <div class="h-3 w-1/2 rounded bg-[var(--app-surface-2)]"></div>
        </div>
      </div>
    </div>

    <div v-else-if="!sites.length" class="card flex flex-col items-center justify-center px-8 py-16 text-center">
      <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--app-surface-2)]/50">
        <UIcon name="i-lucide-globe" class="h-6 w-6 text-[var(--app-ink-soft)]" />
      </div>
      <h2 class="text-lg font-semibold text-[var(--app-ink)]">Aucun site démo</h2>
      <p class="mt-2 max-w-sm text-sm text-[var(--app-ink-soft)]">
        Créez votre premier site vitrine en quelques minutes à partir d'un prospect ou d'une saisie manuelle.
      </p>
      <NuxtLink to="/dashboard/demo-sites/create" class="btn-primary mt-6 inline-flex items-center gap-2">
        <UIcon name="i-lucide-wand-sparkles" class="h-4 w-4" />
        Lancer le builder
      </NuxtLink>
    </div>

    <template v-else>
      <!-- Barre d'outils : recherche par nom/ville + filtre par template. -->
      <div class="mb-5 flex flex-col gap-3 @2xl:flex-row @2xl:items-center @2xl:justify-between">
        <div class="relative w-full @2xl:max-w-xs">
          <UIcon
            name="i-lucide-search"
            class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
          />
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Nom du prospect, ville…"
            aria-label="Rechercher un site démo"
            class="app-input pl-9"
          />
        </div>
        <div class="w-full @2xl:w-56">
          <UiSelectField
            v-model="selectedTemplateId"
            :options="templateFilterOptions"
            aria-label="Filtrer par template"
          />
        </div>
      </div>

      <!-- Compteur de résultats quand un filtre restreint la liste. -->
      <p v-if="hasActiveFilters" class="mb-4 flex flex-wrap items-center gap-2 text-xs text-[var(--app-ink-soft)]">
        <UIcon name="i-lucide-filter" class="h-3 w-3" />
        {{ filteredSites.length }} sur {{ sites.length }} sites
        <button
          type="button"
          class="cursor-pointer font-medium underline underline-offset-2 hover:text-[var(--app-ink)]"
          @click="clearFilters"
        >
          Tout afficher
        </button>
      </p>

      <div v-if="filteredSites.length" class="grid gap-5 @2xl:grid-cols-2 @5xl:grid-cols-3">
        <DemoSitesDemoSiteCard
          v-for="site in filteredSites"
          :key="site.id"
          :site="site"
          :template-name="templateNameById[site.template_id] ?? null"
          @copy="copyDemoUrl"
          @open="openDemoUrl"
        />
      </div>

      <div v-else class="card flex flex-col items-center justify-center px-8 py-16 text-center">
        <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--app-surface-2)]/50">
          <UIcon name="i-lucide-search-x" class="h-6 w-6 text-[var(--app-ink-soft)]" />
        </div>
        <h2 class="text-lg font-semibold text-[var(--app-ink)]">Aucun site ne correspond</h2>
        <p class="mt-2 max-w-sm text-sm text-[var(--app-ink-soft)]">
          Aucun site démo ne correspond à votre recherche ou au template sélectionné.
        </p>
        <button type="button" class="btn-secondary mt-6 inline-flex items-center gap-2" @click="clearFilters">
          <UIcon name="i-lucide-rotate-ccw" class="h-4 w-4" />
          Réinitialiser les filtres
        </button>
      </div>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { UseCopyToClipboardReturn, UseOpenExternalUrlReturn } from '~/types/Composables'
import type { ComputedRef, Ref } from 'vue'
import type { DemoSite, DemoSiteListResponse, DemoSiteTemplate } from '~/services/demoSiteService'
import type { SelectFieldOption } from '~/types/SelectField'
import { DemoSiteService } from '~/services/demoSiteService'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

const sites: Ref<DemoSite[]> = ref([])
const pending: Ref<boolean> = ref(true)
/** Registry display name of each template, keyed by template id. */
const templateNameById: Ref<Record<string, string>> = ref({})

/** Live search over the business name and the city. */
const searchQuery: Ref<string> = ref('')
/** Selected template filter — 'all' keeps every template visible. */
const selectedTemplateId: Ref<string> = ref('all')

const { copy }: UseCopyToClipboardReturn = useCopyToClipboard()
const { openExternalUrl }: UseOpenExternalUrlReturn = useOpenExternalUrl()

/** Template filter options, built from the templates actually present in the list plus an « all » entry. */
const templateFilterOptions: ComputedRef<SelectFieldOption[]> = computed(() => {
  const presentTemplateIds: string[] = Array.from(
    new Set(sites.value.map((site: DemoSite): string => site.template_id)),
  )
  const options: SelectFieldOption[] = presentTemplateIds
    .map(
      (templateId: string): SelectFieldOption => ({
        value: templateId,
        label: templateNameById.value[templateId] ?? templateId,
      }),
    )
    .sort((first: SelectFieldOption, second: SelectFieldOption): number => first.label.localeCompare(second.label))
  return [{ value: 'all', label: 'Tous les templates' }, ...options]
})

/** Sites matching both the search query (name/city) and the selected template. */
const filteredSites: ComputedRef<DemoSite[]> = computed(() => {
  let result: DemoSite[] = sites.value

  if (selectedTemplateId.value !== 'all') {
    result = result.filter((site: DemoSite): boolean => site.template_id === selectedTemplateId.value)
  }

  const query: string = searchQuery.value.trim().toLowerCase()
  if (query) {
    result = result.filter(
      (site: DemoSite): boolean =>
        site.business_name.toLowerCase().includes(query) || (site.city?.toLowerCase().includes(query) ?? false),
    )
  }

  return result
})

/** Whether a search term or a template filter is currently narrowing the list. */
const hasActiveFilters: ComputedRef<boolean> = computed(
  (): boolean => searchQuery.value.trim() !== '' || selectedTemplateId.value !== 'all',
)

/**
 * Open the demo URL in a new browser tab.
 */
async function openDemoUrl(url: string): Promise<void> {
  await openExternalUrl(url)
}

/**
 * Copy the demo URL to the clipboard.
 */
async function copyDemoUrl(url: string): Promise<void> {
  await copy(url)
}

/**
 * Reset the search field and the template filter so every site shows again.
 */
function clearFilters(): void {
  searchQuery.value = ''
  selectedTemplateId.value = 'all'
}

/**
 * Load the template registry names shown under each card title.
 */
async function loadTemplateNames(): Promise<void> {
  try {
    const templates: DemoSiteTemplate[] = await DemoSiteService.listDemoSiteTemplates()
    templateNameById.value = Object.fromEntries(
      templates.map((template: DemoSiteTemplate): [string, string] => [template.id, template.name]),
    )
  } catch {
    // The raw template id shown as fallback is good enough when the registry call fails.
  }
}

onMounted(async () => {
  loadTemplateNames()
  try {
    const response: DemoSiteListResponse = await DemoSiteService.listDemoSites()
    sites.value = response.items
  } finally {
    pending.value = false
  }
})
</script>
