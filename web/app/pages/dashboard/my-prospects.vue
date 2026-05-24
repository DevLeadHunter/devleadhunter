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
        <NuxtLink to="/dashboard/search-prospects" class="btn-primary"> Nouvelle Recherche </NuxtLink>
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
      <div class="grid grid-cols-1 gap-4 md:grid-cols-4">
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Rechercher</label>
          <input v-model="searchQuery" type="text" placeholder="Nom, ville, email..." class="input-field" />
        </div>
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Source</label>
          <select v-model="filterSource" class="input-field">
            <option value="">Toutes les sources</option>
            <option value="google">Google</option>
            <option value="pagesjaunes">Pages Jaunes</option>
            <option value="mock">Mock</option>
          </select>
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
          searchQuery || filterSource || filterCategory
            ? 'Essayez de modifier vos filtres'
            : 'Commencez par faire une recherche de prospects'
        }}
      </p>
      <NuxtLink to="/dashboard/search-prospects" class="btn-primary mt-4 inline-block">
        Rechercher des prospects
      </NuxtLink>
    </div>

    <!-- Prospects Table -->
    <div v-else class="card overflow-hidden">
      <ProspectTable
        :prospects="paginatedProspects"
        :selected-prospects="selectedProspects"
        @toggle-prospect="toggleProspect"
        @view-prospect="viewProspect"
        @delete-prospect="deleteProspect"
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
            class="btn-secondary px-3 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            @click="currentPage--"
          >
            Précédent
          </button>
          <span class="text-muted px-4 py-1 text-sm font-medium"> Page {{ currentPage }} / {{ totalPages }} </span>
          <button
            :disabled="currentPage === totalPages"
            class="btn-secondary px-3 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            @click="currentPage++"
          >
            Suivant
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRuntimeConfig } from '#app'
import { useUserStore } from '~/stores/user'
import type { Prospect } from '~/types'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const config = useRuntimeConfig()
const userStore = useUserStore()

// State
const prospects = ref<Prospect[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)
const selectedProspects = ref<string[]>([])
const searchQuery = ref('')
const filterSource = ref('')
const filterCategory = ref('')
const currentPage = ref(1)
const pageSize = 50

// Computed
const totalProspects = computed(() => prospects.value.length)
const prospectsWithEmail = computed(() => prospects.value.filter((p) => p.email).length)
const prospectsWithWebsite = computed(() => prospects.value.filter((p) => p.website).length)
const prospectsWithPhone = computed(() => prospects.value.filter((p) => p.phone).length)

const filteredProspects = computed(() => {
  let filtered = prospects.value

  // Search filter
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

  // Source filter
  if (filterSource.value) {
    filtered = filtered.filter((p) => p.source === filterSource.value)
  }

  // Category filter
  if (filterCategory.value) {
    const cat = filterCategory.value.toLowerCase()
    filtered = filtered.filter((p) => p.category.toLowerCase().includes(cat))
  }

  return filtered
})

const totalPages = computed(() => Math.ceil(filteredProspects.value.length / pageSize))

const paginatedProspects = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return filteredProspects.value.slice(start, end)
})

// Methods
async function loadProspects() {
  try {
    isLoading.value = true
    error.value = null

    const response = await $fetch<Prospect[]>(`${config.public.apiBase}/api/v1/prospects`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(userStore.token && { Authorization: `Bearer ${userStore.token}` }),
      },
    })

    prospects.value = response
  } catch (err: unknown) {
    error.value = err.message || 'Erreur lors du chargement des prospects'
    console.error('Error loading prospects:', err)
  } finally {
    isLoading.value = false
  }
}

function refreshProspects() {
  currentPage.value = 1
  loadProspects()
}

function clearFilters() {
  searchQuery.value = ''
  filterSource.value = ''
  filterCategory.value = ''
  currentPage.value = 1
}

function toggleProspect(prospectId: string) {
  const index = selectedProspects.value.indexOf(prospectId)
  if (index > -1) {
    selectedProspects.value.splice(index, 1)
  } else {
    selectedProspects.value.push(prospectId)
  }
}

function viewProspect(prospect: Prospect) {
  // TODO: Implement prospect detail view
  console.log('View prospect:', prospect)
}

async function deleteProspect(prospect: Prospect) {
  if (!confirm(`Êtes-vous sûr de vouloir supprimer le prospect "${prospect.name}" ?`)) {
    return
  }

  try {
    await $fetch(`${config.public.apiBase}/api/v1/prospects/${prospect.id}`, {
      method: 'DELETE',
      headers: {
        ...(userStore.token && { Authorization: `Bearer ${userStore.token}` }),
      },
    })

    // Remove from local list
    prospects.value = prospects.value.filter((p) => p.id !== prospect.id)
  } catch (err: unknown) {
    alert(`Erreur lors de la suppression: ${err.message}`)
  }
}

// Lifecycle
onMounted(() => {
  loadProspects()
})
</script>
