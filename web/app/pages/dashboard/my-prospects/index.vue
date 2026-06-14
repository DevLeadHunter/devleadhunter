<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-[#f9f9f9]">Mes Prospects</h1>
        <p class="text-muted mt-2 text-sm">Tous vos prospects sauvegardés depuis vos recherches</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          :disabled="isLoading"
          class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
          @click="refreshProspects"
        >
          <i class="fa-solid fa-rotate-right mr-2"></i>
          Actualiser
        </button>
        <NuxtLink to="/dashboard/my-prospects/add" class="btn-secondary inline-flex">
          <i class="fa-solid fa-user-plus mr-2"></i>
          Ajouter manuellement
        </NuxtLink>
        <NuxtLink to="/dashboard/search-prospects" class="btn-primary inline-flex"> Nouvelle Recherche </NuxtLink>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 gap-6 md:grid-cols-4">
      <div class="card">
        <div class="flex items-center">
          <div class="flex-1">
            <p class="text-muted text-sm font-medium">Total Prospects</p>
            <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ totalProspects }}</p>
          </div>
          <div class="rounded-lg border border-[#30363d] bg-[#050505] p-3">
            <i class="fa-solid fa-users text-xl text-[#f9f9f9]"></i>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-1">
            <p class="text-muted text-sm font-medium">Avec Email</p>
            <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ prospectsWithEmail }}</p>
          </div>
          <div class="rounded-lg border border-[#30363d] bg-[#050505] p-3">
            <i class="fa-solid fa-envelope text-xl text-[#2BAD5F]"></i>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-1">
            <p class="text-muted text-sm font-medium">Avec Site Web</p>
            <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ prospectsWithWebsite }}</p>
          </div>
          <div class="rounded-lg border border-[#30363d] bg-[#050505] p-3">
            <i class="fa-solid fa-globe text-xl text-[#f9f9f9]"></i>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-1">
            <p class="text-muted text-sm font-medium">Avec Téléphone</p>
            <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ prospectsWithPhone }}</p>
          </div>
          <div class="rounded-lg border border-[#30363d] bg-[#050505] p-3">
            <i class="fa-solid fa-phone text-xl text-[#8b949e]"></i>
          </div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="card">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-5">
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Rechercher</label>
          <input v-model="searchQuery" type="text" placeholder="Nom, ville, email..." class="input-field" />
        </div>
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Source</label>
          <UiSelectField v-model="filterSource" :options="sourceFilterOptions" />
        </div>
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Catégorie</label>
          <input v-model="filterCategory" type="text" placeholder="Ex: restaurant" class="input-field" />
        </div>
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Site web</label>
          <UiSelectField v-model="filterWebsite" :options="websiteFilterOptions" />
        </div>
        <div class="flex items-end">
          <button class="btn-secondary w-full" @click="clearFilters">Réinitialiser</button>
        </div>
      </div>
    </div>

    <!-- Loader -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <i class="fa-solid fa-spinner fa-spin text-muted text-4xl"></i>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="rounded-lg border border-[#DC4747] bg-[#1a1a1a] p-4 text-[#DC4747]">
      <p class="font-semibold">Erreur</p>
      <p class="text-muted mt-1 text-sm">{{ error }}</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredProspects.length === 0" class="py-12 text-center">
      <i class="fa-solid fa-inbox text-muted mb-4 text-6xl"></i>
      <h3 class="mt-4 text-lg font-medium text-[#f9f9f9]">Aucun prospect trouvé</h3>
      <p class="text-muted mt-2 text-sm">
        {{
          searchQuery || hasActiveSourceFilter || filterCategory
            ? 'Essayez de modifier vos filtres'
            : 'Commencez par faire une recherche de prospects'
        }}
      </p>
      <NuxtLink to="/dashboard/search-prospects" class="btn-primary mt-4 inline-flex">
        Rechercher des prospects
      </NuxtLink>
    </div>

    <!-- Prospects Table -->
    <div v-else class="card overflow-hidden">
      <UiProspectTable
        :prospects="paginatedProspects"
        :selected-prospects="selectedProspects"
        @view-prospect="openDrawer"
        @delete-prospect="handleDeleteProspect"
        @toggle-select="toggleSelect"
        @toggle-select-all="toggleSelectAll"
      />

      <!-- Pagination -->
      <div class="flex items-center justify-between border-t border-[#30363d] px-6 py-4">
        <div class="text-muted text-sm">
          Affichage de {{ (currentPage - 1) * pageSize + 1 }} à
          {{ Math.min(currentPage * pageSize, filteredProspects.length) }} sur {{ filteredProspects.length }} prospects
        </div>
        <div class="flex items-center gap-2">
          <button
            :disabled="currentPage === 1"
            class="btn-secondary h-auto min-h-0 px-3 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            @click="currentPage--"
          >
            Précédent
          </button>
          <span class="text-muted px-4 py-1 text-sm font-medium"> Page {{ currentPage }} / {{ totalPages }} </span>
          <button
            :disabled="currentPage === totalPages"
            class="btn-secondary h-auto min-h-0 px-3 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-50"
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

    <!-- Prospect detail drawer -->
    <UiProspectDrawer
      :open="drawerOpen"
      :prospect="drawerProspect"
      @close="drawerOpen = false"
      @updated="handleProspectUpdated"
      @deleted="handleProspectDeleted"
      @add-to-campaign="handleAddToCampaign"
      @send-email="handleSendEmail"
      @mark-as-sold="handleMarkAsSold"
    />

    <!-- Bulk action bar (visible when prospects are selected) -->
    <Transition name="bulkbar">
      <div v-if="selectedProspects.length > 0" class="fixed inset-x-0 bottom-6 z-40 flex justify-center px-4">
        <div
          class="flex flex-wrap items-center justify-center gap-2 rounded-2xl border border-[#30363d] bg-[#161b22]/95 px-4 py-3 shadow-2xl backdrop-blur"
        >
          <span class="px-1 text-sm font-semibold text-[#f9f9f9]">
            {{ selectedProspects.length }} sélectionné{{ selectedProspects.length > 1 ? 's' : '' }}
          </span>
          <span class="hidden h-5 w-px bg-[#30363d] sm:block"></span>
          <button type="button" class="btn-secondary" @click="bulkCampaignOpen = true">
            <i class="fa-solid fa-bullhorn mr-2"></i>Campagne
          </button>
          <button
            type="button"
            class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="bulkBusy"
            @click="bulkEnrich"
          >
            <i :class="bulkBusy ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-wand-magic-sparkles'" class="mr-2"></i>
            Enrichir
          </button>
          <button type="button" class="btn-primary" @click="bulkGenerateOpen = true">
            <i class="fa-solid fa-globe mr-2"></i>Générer les sites
          </button>
          <button
            type="button"
            class="text-muted ml-1 cursor-pointer p-2 transition-colors hover:text-[#f9f9f9]"
            aria-label="Désélectionner tout"
            @click="clearSelection"
          >
            <i class="fa-solid fa-times"></i>
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
import { ref, computed, onMounted } from 'vue'
import type { Prospect } from '~/types'
import { deleteProspect as deleteProspectApi, listProspects } from '~/services/prospectsService'
import { createOrder } from '~/services/ordersService'
import { runBulkEnrichment } from '~/services/enrichmentService'
import type { BulkGenerateResult } from '~/services/demoSiteService'
import { useToast } from '~/composables/useToast'
import { ALL_SOURCES_VALUE, PROSPECT_SOURCE_FILTER_OPTIONS } from '~/constants/prospectSources'

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
const filterSource = ref(ALL_SOURCES_VALUE)
const filterCategory = ref('')
const filterWebsite = ref<'all' | 'yes' | 'no'>('all')

const websiteFilterOptions = [
  { value: 'all', label: 'Tous' },
  { value: 'yes', label: 'Oui' },
  { value: 'no', label: 'Non' },
]
const currentPage = ref(1)
const pageSize = 50

// Quick-delete (from table row icon)
const prospectToDelete = ref<Prospect | null>(null)
const deleteConfirmModal = ref<{ open: () => void; close: () => void } | null>(null)

// Detail drawer
const drawerOpen = ref(false)
const drawerProspect = ref<Prospect | null>(null)

const toast = useToast()
const sourceFilterOptions = PROSPECT_SOURCE_FILTER_OPTIONS

// ─── Computed ─────────────────────────────────────────────────────────────────

const deleteConfirmMessage = computed(() => {
  if (!prospectToDelete.value) return 'Cette action est irréversible.'
  return `Supprimer définitivement « ${prospectToDelete.value.name} » ? Cette action est irréversible.`
})

const hasActiveSourceFilter = computed(() => filterSource.value !== ALL_SOURCES_VALUE)

const selectedIds = computed<number[]>(() =>
  selectedProspects.value.map((id) => Number(id)).filter((n) => !Number.isNaN(n)),
)

const totalProspects = computed(() => prospects.value.length)
const prospectsWithEmail = computed(() => prospects.value.filter((p) => p.email).length)
const prospectsWithWebsite = computed(() => prospects.value.filter((p) => p.website).length)
const prospectsWithPhone = computed(() => prospects.value.filter((p) => p.phone).length)

const filteredProspects = computed(() => {
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

  if (hasActiveSourceFilter.value) {
    filtered = filtered.filter((p) => p.source === filterSource.value)
  }

  if (filterCategory.value) {
    const cat = filterCategory.value.toLowerCase()
    filtered = filtered.filter((p) => p.category.toLowerCase().includes(cat))
  }

  if (filterWebsite.value === 'yes') {
    filtered = filtered.filter((p) => !!p.website)
  } else if (filterWebsite.value === 'no') {
    filtered = filtered.filter((p) => !p.website)
  }

  return filtered
})

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
  filterSource.value = ALL_SOURCES_VALUE
  filterCategory.value = ''
  filterWebsite.value = 'all'
  currentPage.value = 1
}

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

// ─── Drawer ───────────────────────────────────────────────────────────────────

/** Open the detail drawer for a given prospect. */
function openDrawer(prospect: Prospect): void {
  drawerProspect.value = prospect
  drawerOpen.value = true
}

/** Drawer emitted 'updated' — patch the local list in place. */
function handleProspectUpdated(updated: Prospect): void {
  const idx = prospects.value.findIndex((p) => p.id === updated.id)
  if (idx !== -1) prospects.value.splice(idx, 1, updated)
  // Keep the drawer open with fresh data
  drawerProspect.value = updated
}

/** Drawer emitted 'deleted' — remove from local list. */
function handleProspectDeleted(prospectId: number): void {
  prospects.value = prospects.value.filter((p) => p.id !== prospectId)
  selectedProspects.value = selectedProspects.value.filter((id) => id !== String(prospectId))
}

function handleAddToCampaign(prospect: Prospect): void {
  navigateTo(`/dashboard/campaigns?addProspect=${prospect.id}`)
}

function handleSendEmail(_prospect: Prospect): void {
  toast.info('La fonctionnalité email sera disponible prochainement.')
}

/**
 * Create a website order from a prospect and open the sales page.
 * @param prospect - The prospect being marked as sold.
 */
async function handleMarkAsSold(prospect: Prospect): Promise<void> {
  try {
    await createOrder({
      product_type: 'website',
      prospect_id: prospect.id,
      business_name: prospect.name,
      customer_email: prospect.email ?? null,
    })
    toast.success(`Vente créée pour « ${prospect.name} »`)
    drawerOpen.value = false
    navigateTo('/dashboard/orders')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la création de la vente')
  }
}

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
