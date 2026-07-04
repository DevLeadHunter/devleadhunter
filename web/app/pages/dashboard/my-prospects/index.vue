<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-[#f9f9f9] sm:text-3xl">Mes Prospects</h1>
        <p class="text-muted mt-2 text-sm">Tous vos prospects sauvegardés depuis vos recherches</p>
      </div>
      <div class="flex flex-wrap items-center gap-2 sm:gap-3">
        <button
          :disabled="isLoading"
          class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
          @click="refreshProspects"
        >
          <UIcon name="i-lucide-refresh-cw" class="mr-2 h-4 w-4" />
          Actualiser
        </button>
        <NuxtLink to="/dashboard/my-prospects/add" class="btn-secondary inline-flex">
          <UIcon name="i-lucide-user-plus" class="mr-2 h-4 w-4" />
          Ajouter manuellement
        </NuxtLink>
        <NuxtLink to="/dashboard/search-prospects" class="btn-primary inline-flex"> Nouvelle Recherche </NuxtLink>
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
    <div class="card">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Rechercher</label>
          <input v-model="searchQuery" type="text" placeholder="Nom, ville, email..." class="input-field" />
        </div>
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Site web</label>
          <UiSelectField v-model="filterWebsite" :options="websiteFilterOptions" />
        </div>
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Ville</label>
          <UiCitySelect v-model="filterCity" placeholder="Toutes les villes" />
        </div>
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Catégorie</label>
          <input v-model="filterCategory" type="text" placeholder="Ex: restaurant" class="input-field" />
        </div>
        <div class="flex items-end">
          <button class="btn-secondary w-full" @click="clearFilters">Réinitialiser</button>
        </div>
      </div>
    </div>

    <!-- Contacted tabs -->
    <div class="flex items-center gap-1 border-b border-[#30363d]">
      <button
        type="button"
        class="relative cursor-pointer px-4 py-2.5 text-sm font-medium transition-colors"
        :class="activeTab === 'not_contacted' ? 'text-[#f9f9f9]' : 'text-[#8b949e] hover:text-[#f9f9f9]'"
        @click="activeTab = 'not_contacted'"
      >
        Pas contacté
        <span class="ml-1.5 rounded-full bg-[#30363d] px-2 py-0.5 text-xs">{{ notContactedCount }}</span>
        <span v-if="activeTab === 'not_contacted'" class="absolute inset-x-0 -bottom-px h-0.5 bg-[#f9f9f9]"></span>
      </button>
      <button
        type="button"
        class="relative cursor-pointer px-4 py-2.5 text-sm font-medium transition-colors"
        :class="activeTab === 'contacted' ? 'text-[#f9f9f9]' : 'text-[#8b949e] hover:text-[#f9f9f9]'"
        @click="activeTab = 'contacted'"
      >
        Contacté
        <span class="ml-1.5 rounded-full bg-[#30363d] px-2 py-0.5 text-xs">{{ contactedCount }}</span>
        <span v-if="activeTab === 'contacted'" class="absolute inset-x-0 -bottom-px h-0.5 bg-[#f9f9f9]"></span>
      </button>
    </div>

    <!-- Loader -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <UIcon name="i-lucide-loader-circle" class="text-muted h-10 w-10 animate-spin" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="rounded-lg border border-[#DC4747] bg-[#1a1a1a] p-4 text-[#DC4747]">
      <p class="font-semibold">Erreur</p>
      <p class="text-muted mt-1 text-sm">{{ error }}</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredProspects.length === 0" class="py-12 text-center">
      <UIcon name="i-lucide-inbox" class="text-muted mb-4 h-16 w-16" />
      <h3 class="mt-4 text-lg font-medium text-[#f9f9f9]">Aucun prospect trouvé</h3>
      <p class="text-muted mt-2 text-sm">
        {{
          searchQuery || filterCity || filterCategory
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
      <div
        class="flex flex-col gap-3 border-t border-[#30363d] px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6"
      >
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
      @toggle-contacted="handleToggleContacted"
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
            <UIcon name="i-lucide-megaphone" class="mr-2 h-4 w-4" />Campagne
          </button>
          <button
            type="button"
            class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="bulkBusy"
            @click="bulkEnrich"
          >
            <UIcon
              :name="bulkBusy ? 'i-lucide-loader-circle' : 'i-lucide-sparkles'"
              :class="['mr-2 h-4 w-4', bulkBusy && 'animate-spin']"
            />
            Enrichir
          </button>
          <button type="button" class="btn-primary" @click="bulkGenerateOpen = true">
            <UIcon name="i-lucide-globe" class="mr-2 h-4 w-4" />Générer les sites
          </button>
          <button
            type="button"
            class="text-muted ml-1 cursor-pointer p-2 transition-colors hover:text-[#f9f9f9]"
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
import { deleteProspect as deleteProspectApi, listProspects, updateProspect } from '~/services/prospectsService'
import { createOrder } from '~/services/ordersService'
import { runBulkEnrichment } from '~/services/enrichmentService'
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
const filterWebsite = ref<'all' | 'yes' | 'no'>('no')
const activeTab = ref<'not_contacted' | 'contacted'>('not_contacted')

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

/**
 * Table emitted 'toggleContacted' — flip the contacted status and patch local state.
 * @param prospect - The prospect whose contacted status was toggled.
 */
async function handleToggleContacted(prospect: Prospect): Promise<void> {
  const next = !prospect.contacted
  try {
    const updated = await updateProspect(prospect.id, { contacted: next })
    const idx = prospects.value.findIndex((p) => p.id === updated.id)
    if (idx !== -1) prospects.value.splice(idx, 1, updated)
    toast.success(next ? `« ${prospect.name} » marqué comme contacté` : `« ${prospect.name} » remis en non contacté`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la mise à jour')
  }
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
