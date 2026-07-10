<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="app-label flex items-center gap-2">
          <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
          Prospection
        </p>
        <h1 class="app-page-title mt-2">Mes prospects</h1>
        <p class="mt-1.5 text-sm text-[var(--app-ink-soft)]">Tous vos prospects sauvegardés depuis vos recherches</p>
      </div>
      <div class="flex flex-wrap items-center gap-2 sm:gap-3">
        <button
          :disabled="isLoading"
          class="app-btn-secondary h-9 px-4 text-xs disabled:cursor-not-allowed disabled:opacity-50"
          @click="refreshProspects"
        >
          <UIcon name="i-lucide-refresh-cw" class="h-3.5 w-3.5" />
          Actualiser
        </button>
        <NuxtLink to="/dashboard/my-prospects/add" class="app-btn-secondary h-9 px-4 text-xs">
          <UIcon name="i-lucide-user-plus" class="h-3.5 w-3.5" />
          Ajouter manuellement
        </NuxtLink>
        <NuxtLink to="/dashboard/search-prospects" class="app-btn-primary h-9 px-4 text-xs">
          <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
          Nouvelle recherche
        </NuxtLink>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <UiStatCard label="Total Prospects" :value="totalProspects" icon="i-lucide-users" accent="neutral" />
      <UiStatCard label="Avec Email" :value="prospectsWithEmail" icon="i-lucide-mail" accent="emerald" />
      <UiStatCard label="Sans Site Web" :value="prospectsWithoutWebsite" icon="i-lucide-globe-lock" accent="danger" />
      <UiStatCard label="Avec Téléphone" :value="prospectsWithPhone" icon="i-lucide-phone" accent="sky" />
    </div>

    <!-- Filters -->
    <div class="app-card p-4">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div>
          <label class="app-label mb-1.5 block">Rechercher</label>
          <input v-model="searchQuery" type="text" placeholder="Nom, ville, email..." class="app-input" />
        </div>
        <div>
          <label class="app-label mb-1.5 block">Site web</label>
          <UiSelectField v-model="filterWebsite" :options="websiteFilterOptions" />
        </div>
        <div>
          <label class="app-label mb-1.5 block">Ville</label>
          <UiCitySelect v-model="filterCity" placeholder="Toutes les villes" />
        </div>
        <div>
          <label class="app-label mb-1.5 block">Catégorie</label>
          <input v-model="filterCategory" type="text" placeholder="Ex: restaurant" class="app-input" />
        </div>
        <div class="flex items-end">
          <button class="app-btn-secondary w-full" @click="clearFilters">Réinitialiser</button>
        </div>
      </div>
    </div>

    <!-- Contacted tabs -->
    <div class="flex items-center gap-1 border-b border-[var(--app-line)]">
      <button
        type="button"
        class="relative cursor-pointer px-4 py-2.5 text-sm font-medium transition-colors"
        :class="
          activeTab === 'not_contacted'
            ? 'text-[var(--app-ink)]'
            : 'text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
        "
        @click="activeTab = 'not_contacted'"
      >
        Pas contacté
        <span class="font-label ml-1.5 rounded-full bg-[var(--app-surface-2)] px-2 py-0.5 text-xs">
          {{ notContactedCount }}
        </span>
        <span
          v-if="activeTab === 'not_contacted'"
          class="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-[var(--app-accent)]"
        ></span>
      </button>
      <button
        type="button"
        class="relative cursor-pointer px-4 py-2.5 text-sm font-medium transition-colors"
        :class="
          activeTab === 'contacted' ? 'text-[var(--app-ink)]' : 'text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
        "
        @click="activeTab = 'contacted'"
      >
        Contacté
        <span class="font-label ml-1.5 rounded-full bg-[var(--app-surface-2)] px-2 py-0.5 text-xs">
          {{ contactedCount }}
        </span>
        <span
          v-if="activeTab === 'contacted'"
          class="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-[var(--app-accent)]"
        ></span>
      </button>
    </div>

    <!-- Loader -->
    <div v-if="isLoading" class="flex items-center justify-center py-16">
      <UIcon name="i-lucide-loader-circle" class="h-8 w-8 animate-spin text-[var(--app-accent)]" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="app-card border-[var(--app-red)]/40 bg-[var(--app-red-soft)] p-5">
      <p class="font-semibold text-[var(--app-red)]">Erreur</p>
      <p class="mt-1 text-sm text-[var(--app-ink-soft)]">{{ error }}</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredProspects.length === 0" class="app-card px-6 py-12 text-center">
      <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />
      <h3 class="font-display mt-5 text-2xl font-semibold text-[var(--app-ink)]">Aucun prospect trouvé</h3>
      <p class="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-[var(--app-ink-soft)]">
        {{
          searchQuery || filterCity || filterCategory
            ? 'Essayez de modifier vos filtres pour élargir la sélection.'
            : 'Lancez une recherche pour trouver des artisans sans site web près de chez vous.'
        }}
      </p>
      <NuxtLink to="/dashboard/search-prospects" class="app-btn-primary mt-6 inline-flex">
        Trouver des prospects
      </NuxtLink>
    </div>

    <!-- Prospects Table -->
    <div v-else class="app-card overflow-hidden">
      <UiProspectTable
        :prospects="paginatedProspects"
        :selected-prospects="selectedProspects"
        @view-prospect="openDrawer"
        @delete-prospect="handleDeleteProspect"
        @toggle-select="toggleSelect"
        @toggle-select-all="toggleSelectAll"
      />

      <!-- Pagination -->
      <div
        class="flex flex-col gap-3 border-t border-[var(--app-line)] bg-[var(--app-surface-2)]/50 px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between sm:px-6"
      >
        <div class="font-label text-xs text-[var(--app-ink-soft)]">
          {{ (currentPage - 1) * pageSize + 1 }}–{{ Math.min(currentPage * pageSize, filteredProspects.length) }} sur
          {{ filteredProspects.length }} prospects
        </div>
        <div class="flex items-center gap-2">
          <button
            :disabled="currentPage === 1"
            class="app-btn-secondary h-8 min-h-8 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            @click="currentPage--"
          >
            Précédent
          </button>
          <span class="font-label px-2 text-xs text-[var(--app-ink-soft)]">
            Page {{ currentPage }} / {{ totalPages }}
          </span>
          <button
            :disabled="currentPage === totalPages"
            class="app-btn-secondary h-8 min-h-8 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            @click="currentPage++"
          >
            Suivant
          </button>
        </div>
      </div>
    </div>

    <!-- Quick-delete confirmation modal -->
    <UiConfirmModal
      ref="deleteConfirmModal"
      title="Supprimer le prospect"
      :message="deleteConfirmMessage"
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="confirmDeleteProspect"
    />

    <!-- Bulk action bar (visible when prospects are selected) -->
    <Transition name="bulkbar">
      <div v-if="selectedProspects.length > 0" class="fixed inset-x-0 bottom-6 z-40 flex justify-center px-4">
        <div
          class="app-card flex flex-wrap items-center justify-center gap-2 rounded-full px-4 py-2.5 shadow-[var(--app-shadow-soft)] backdrop-blur"
        >
          <span class="font-label px-1.5 text-xs font-medium text-[var(--app-ink)]">
            {{ selectedProspects.length }} sélectionné{{ selectedProspects.length > 1 ? 's' : '' }}
          </span>
          <span class="hidden h-5 w-px bg-[var(--app-line)] sm:block"></span>
          <button type="button" class="app-btn-secondary h-9 px-4 text-xs" @click="bulkCampaignOpen = true">
            <UIcon name="i-lucide-megaphone" class="h-3.5 w-3.5" />Campagne
          </button>
          <button
            type="button"
            class="app-btn-secondary h-9 px-4 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="bulkBusy"
            @click="bulkEnrich"
          >
            <UIcon
              :name="bulkBusy ? 'i-lucide-loader-circle' : 'i-lucide-sparkles'"
              :class="['h-3.5 w-3.5', bulkBusy && 'animate-spin']"
            />
            Enrichir
          </button>
          <button type="button" class="app-btn-primary h-9 px-4 text-xs" @click="bulkGenerateOpen = true">
            <UIcon name="i-lucide-globe" class="h-3.5 w-3.5" />Générer les sites
          </button>
          <button
            type="button"
            class="ml-0.5 cursor-pointer rounded-full p-2 text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            aria-label="Désélectionner tout"
            @click="clearSelection"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>
      </div>
    </Transition>

    <!-- Bulk: add to campaign -->
    <UiBulkCampaignModal
      :open="bulkCampaignOpen"
      :prospect-ids="selectedIds"
      @close="bulkCampaignOpen = false"
      @added="handleBulkAdded"
    />

    <!-- Bulk: generate websites -->
    <UiBulkGenerateModal
      :open="bulkGenerateOpen"
      :prospect-ids="selectedIds"
      @close="bulkGenerateOpen = false"
      @generated="handleBulkGenerated"
    />
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, watch, onMounted } from 'vue'
import type { Prospect } from '~/types'
import { deleteProspect as deleteProspectApi, listProspects } from '~/services/prospectsService'
import { runBulkEnrichment } from '~/services/enrichmentService'
import { useDrawerStackStore } from '~/stores/drawerStack'
import type { BulkGenerateResult } from '~/services/demoSiteService'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

// ─── State ────────────────────────────────────────────────────────────────────

const prospects = ref<Prospect[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)
const selectedProspects = ref<string[]>([])
const bulkCampaignOpen = ref(false)
const bulkGenerateOpen = ref(false)
const bulkBusy = ref(false)
const searchQuery = ref('')
const filterCategory = ref('')
const filterCity = ref('')
const filterWebsite = ref<'all' | 'yes' | 'no' | 'improvable'>('no')
const activeTab = ref<'not_contacted' | 'contacted'>('not_contacted')

const websiteFilterOptions = [
  { value: 'all', label: 'Tous' },
  { value: 'yes', label: 'Oui' },
  { value: 'no', label: 'Non' },
  { value: 'improvable', label: 'Améliorable (audit)' },
]
const currentPage = ref(1)
const pageSize = 50

// Quick-delete (from table row icon)
const prospectToDelete = ref<Prospect | null>(null)
const deleteConfirmModal = ref<{ open: () => void; close: () => void } | null>(null)

// Detail drawer
/** Persistent drawer stack (the prospect drawer is hosted by the layout). */
const drawerStack = useDrawerStackStore()

const toast = useToast()

// ─── Computed ─────────────────────────────────────────────────────────────────

const deleteConfirmMessage = computed(() => {
  if (!prospectToDelete.value) return 'Cette action est irréversible.'
  return `Supprimer définitivement « ${prospectToDelete.value.name} » ? Cette action est irréversible.`
})

const selectedIds = computed<number[]>(() =>
  selectedProspects.value.map((id) => Number(id)).filter((n) => !Number.isNaN(n)),
)

const totalProspects = computed(() => prospects.value.length)
const prospectsWithEmail = computed(() => prospects.value.filter((p) => p.email).length)
const prospectsWithoutWebsite = computed(() => prospects.value.filter((p) => !p.website).length)
const prospectsWithPhone = computed(() => prospects.value.filter((p) => p.phone).length)

/** Prospects matching every filter EXCEPT the contacted tab (drives the tab counts). */
const baseFiltered = computed(() => {
  let filtered = prospects.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(
      (p) =>
        p.name.toLowerCase().includes(query) ||
        p.city?.toLowerCase().includes(query) ||
        p.email?.toLowerCase().includes(query) ||
        p.phone?.toLowerCase().includes(query),
    )
  }

  if (filterCity.value) {
    const city = filterCity.value.toLowerCase()
    filtered = filtered.filter((p) => p.city?.toLowerCase().includes(city))
  }

  if (filterCategory.value) {
    const cat = filterCategory.value.toLowerCase()
    filtered = filtered.filter((p) => p.category.toLowerCase().includes(cat))
  }

  if (filterWebsite.value === 'yes') {
    filtered = filtered.filter((p) => !!p.website)
  } else if (filterWebsite.value === 'no') {
    filtered = filtered.filter((p) => !p.website)
  } else if (filterWebsite.value === 'improvable') {
    // Site existant jugé faible par l'audit Lighthouse → cible refonte.
    filtered = filtered.filter((p) => !!p.website && p.lighthouse_json?.is_improvable === true)
  }

  return filtered
})

const notContactedCount = computed(() => baseFiltered.value.filter((p) => !p.contacted).length)
const contactedCount = computed(() => baseFiltered.value.filter((p) => p.contacted).length)

const filteredProspects = computed(() =>
  baseFiltered.value.filter((p) => (activeTab.value === 'contacted' ? p.contacted : !p.contacted)),
)

const totalPages = computed(() => Math.ceil(filteredProspects.value.length / pageSize))

const paginatedProspects = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredProspects.value.slice(start, start + pageSize)
})

// ─── Data loading ─────────────────────────────────────────────────────────────

async function loadProspects(): Promise<void> {
  try {
    isLoading.value = true
    error.value = null
    prospects.value = await listProspects()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Erreur lors du chargement des prospects'
  } finally {
    isLoading.value = false
  }
}

function refreshProspects(): void {
  currentPage.value = 1
  loadProspects()
}

function clearFilters(): void {
  searchQuery.value = ''
  filterCity.value = ''
  filterCategory.value = ''
  filterWebsite.value = 'no'
  currentPage.value = 1
}

// Reset to the first page whenever the active filter set or tab changes.
watch([activeTab, searchQuery, filterCity, filterCategory, filterWebsite], (): void => {
  currentPage.value = 1
})

// ─── Selection ──────────────────────────────────────────────────────────────

/**
 * Toggle a single prospect in the selection.
 * @param prospect - The prospect whose checkbox was toggled.
 */
function toggleSelect(prospect: Prospect): void {
  const id = String(prospect.id)
  const idx = selectedProspects.value.indexOf(id)
  if (idx === -1) selectedProspects.value.push(id)
  else selectedProspects.value.splice(idx, 1)
}

/**
 * Select or clear every prospect on the current page.
 * @param checked - True to add the page's prospects, false to remove them.
 */
function toggleSelectAll(checked: boolean): void {
  const pageIds = paginatedProspects.value.map((p) => String(p.id))
  if (checked) {
    const set = new Set([...selectedProspects.value, ...pageIds])
    selectedProspects.value = Array.from(set)
  } else {
    const pageSet = new Set(pageIds)
    selectedProspects.value = selectedProspects.value.filter((id) => !pageSet.has(id))
  }
}

/** Clear the entire selection. */
function clearSelection(): void {
  selectedProspects.value = []
}

// ─── Bulk actions ─────────────────────────────────────────────────────────────

/**
 * Campaign modal succeeded — toast and clear the selection.
 * @param payload - The add-to-campaign result.
 * @param payload.campaignName - Name of the campaign the prospects were added to.
 * @param payload.count - Number of prospects added.
 */
function handleBulkAdded(payload: { campaignName: string; count: number }): void {
  toast.success(`${payload.count} prospect(s) ajouté(s) à « ${payload.campaignName} »`)
  clearSelection()
}

/**
 * Bulk generation finished — surface skipped/failed items and clear selection.
 * @param result - The aggregated bulk generation result.
 */
function handleBulkGenerated(result: BulkGenerateResult): void {
  if (result.failed > 0 || result.skipped_no_email.length > 0) {
    toast.info(
      `${result.created} site(s) créé(s) · ${result.skipped_no_email.length} sans email · ${result.failed} échec(s)`,
    )
  }
  clearSelection()
}

/**
 * Run enrichment for every selected prospect (sequential server-side).
 */
async function bulkEnrich(): Promise<void> {
  if (bulkBusy.value || selectedIds.value.length === 0) return
  bulkBusy.value = true
  try {
    const res = await runBulkEnrichment(selectedIds.value)
    toast.success(`Enrichissement : ${res.succeeded} réussi(s), ${res.failed} échec(s)`)
    clearSelection()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Erreur lors de l'enrichissement")
  } finally {
    bulkBusy.value = false
  }
}

// ─── Drawer (persistent stack hosted by the layout) ──────────────────────────

/** Open the detail drawer for a given prospect. */
function openDrawer(prospect: Prospect): void {
  drawerStack.push({ kind: 'prospect', prospect })
}

/** Drawer notified 'updated' — patch the local list in place. */
function handleProspectUpdated(updated: Prospect): void {
  const idx = prospects.value.findIndex((p) => p.id === updated.id)
  if (idx !== -1) prospects.value.splice(idx, 1, updated)
}

/** Drawer notified 'deleted' — remove from local list. */
function handleProspectDeleted(prospectId: number): void {
  prospects.value = prospects.value.filter((p) => p.id !== prospectId)
  selectedProspects.value = selectedProspects.value.filter((id) => id !== String(prospectId))
}

// Mutations done inside the drawer (edit, delete, contacted…) are broadcast
// through the store — keep the local list in sync.
watch(
  (): number => drawerStack.prospectMutationCounter,
  (): void => {
    const mutation = drawerStack.lastProspectMutation
    if (!mutation) return
    if (mutation.type === 'updated') handleProspectUpdated(mutation.prospect)
    else handleProspectDeleted(mutation.prospectId)
  },
)

// ─── Quick-delete (table row icon) ────────────────────────────────────────────

function handleDeleteProspect(prospect: Prospect): void {
  prospectToDelete.value = prospect
  deleteConfirmModal.value?.open()
}

async function confirmDeleteProspect(): Promise<void> {
  const prospect = prospectToDelete.value
  if (!prospect) return
  try {
    await deleteProspectApi(prospect.id)
    handleProspectDeleted(prospect.id)
    toast.success(`Prospect « ${prospect.name} » supprimé`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la suppression')
  } finally {
    prospectToDelete.value = null
  }
}

// ─── Init ─────────────────────────────────────────────────────────────────────

onMounted(async (): Promise<void> => {
  await loadProspects()
  // Deep-link from the dashboard hot-leads widget: ?open=<prospectId> opens the drawer.
  const openParam = useRoute().query.open
  const openId: number = Number(Array.isArray(openParam) ? openParam[0] : openParam)
  if (!Number.isNaN(openId) && openId > 0) {
    const target = prospects.value.find((p) => p.id === openId)
    if (target) openDrawer(target)
  }
})
</script>

<style scoped>
.bulkbar-enter-active,
.bulkbar-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.bulkbar-enter-from,
.bulkbar-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

@media (prefers-reduced-motion: reduce) {
  .bulkbar-enter-active,
  .bulkbar-leave-active {
    transition: none;
  }
  .bulkbar-enter-from,
  .bulkbar-leave-to {
    transform: none;
  }
}
</style>
