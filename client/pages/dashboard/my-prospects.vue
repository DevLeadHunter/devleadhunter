<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-[#f9f9f9]">Mes Prospects</h1>
        <p class="mt-2 text-sm text-muted">
          Tous vos prospects sauvegardés depuis vos recherches
        </p>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="refreshProspects"
          :disabled="isLoading"
          class="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <i class="fa-solid fa-rotate-right mr-2"></i>
          Actualiser
        </button>
        <NuxtLink
          to="/dashboard/search-prospects"
          class="btn-primary"
        >
          Nouvelle Recherche
        </NuxtLink>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 gap-6 md:grid-cols-4">
      <div class="card">
        <div class="flex items-center">
          <div class="flex-1">
            <p class="text-sm font-medium text-muted">Total Prospects</p>
            <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ totalProspects }}</p>
          </div>
          <div class="p-3 bg-[#050505] border border-[#30363d] rounded-lg">
            <i class="fa-solid fa-users text-[#f9f9f9] text-xl"></i>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-1">
            <p class="text-sm font-medium text-muted">Avec Email</p>
            <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ prospectsWithEmail }}</p>
          </div>
          <div class="p-3 bg-[#050505] border border-[#30363d] rounded-lg">
            <i class="fa-solid fa-envelope text-[#2BAD5F] text-xl"></i>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-1">
            <p class="text-sm font-medium text-muted">Avec Site Web</p>
            <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ prospectsWithWebsite }}</p>
          </div>
          <div class="p-3 bg-[#050505] border border-[#30363d] rounded-lg">
            <i class="fa-solid fa-globe text-[#f9f9f9] text-xl"></i>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-1">
            <p class="text-sm font-medium text-muted">Avec Téléphone</p>
            <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ prospectsWithPhone }}</p>
          </div>
          <div class="p-3 bg-[#050505] border border-[#30363d] rounded-lg">
            <i class="fa-solid fa-phone text-[#8b949e] text-xl"></i>
          </div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="card">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-4">
        <div>
          <label class="block text-xs font-medium text-muted mb-1.5">Rechercher</label>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Nom, ville, email..."
            class="input-field"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-muted mb-1.5">Source</label>
          <select
            v-model="filterSource"
            class="input-field"
          >
            <option value="">Toutes les sources</option>
            <option value="google">Google</option>
            <option value="pagesjaunes">Pages Jaunes</option>
            <option value="mock">Mock</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-muted mb-1.5">Catégorie</label>
          <input
            v-model="filterCategory"
            type="text"
            placeholder="Ex: restaurant"
            class="input-field"
          />
        </div>
        <div class="flex items-end">
          <button
            @click="clearFilters"
            class="btn-secondary w-full"
          >
            Réinitialiser
          </button>
        </div>
      </div>
    </div>

    <!-- Loader -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <i class="fa-solid fa-spinner fa-spin text-4xl text-muted"></i>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="p-4 text-[#DC4747] bg-[#1a1a1a] border border-[#DC4747] rounded-lg">
      <p class="font-semibold">Erreur</p>
      <p class="mt-1 text-sm text-muted">{{ error }}</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredProspects.length === 0" class="py-12 text-center">
      <i class="fa-solid fa-inbox text-6xl text-muted mb-4"></i>
      <h3 class="mt-4 text-lg font-medium text-[#f9f9f9]">Aucun prospect trouvé</h3>
      <p class="mt-2 text-sm text-muted">
        {{ searchQuery || filterSource || filterCategory ? 'Essayez de modifier vos filtres' : 'Commencez par faire une recherche de prospects' }}
      </p>
      <NuxtLink
        to="/dashboard/search-prospects"
        class="inline-block btn-primary mt-4"
      >
        Rechercher des prospects
      </NuxtLink>
    </div>

    <!-- Prospects Table -->
    <div v-else class="overflow-hidden card">
      <ProspectTable
        :prospects="paginatedProspects"
        :selected-prospects="selectedProspects"
        @toggle-prospect="toggleProspect"
        @view-prospect="viewProspect"
        @delete-prospect="deleteProspect"
      />
      
      <!-- Pagination -->
      <div class="flex items-center justify-between px-6 py-4 border-t border-[#30363d]">
        <div class="text-sm text-muted">
          Affichage de {{ ((currentPage - 1) * pageSize) + 1 }} à {{ Math.min(currentPage * pageSize, filteredProspects.length) }} sur {{ filteredProspects.length }} prospects
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="currentPage--"
            :disabled="currentPage === 1"
            class="btn-secondary text-xs px-3 py-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Précédent
          </button>
          <span class="px-4 py-1 text-sm font-medium text-muted">
            Page {{ currentPage }} / {{ totalPages }}
          </span>
          <button
            @click="currentPage++"
            :disabled="currentPage === totalPages"
            class="btn-secondary text-xs px-3 py-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Suivant
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRuntimeConfig } from '#app';
import { useUserStore } from '~/stores/user';
import type { Prospect } from '~/types';

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth']
});

const config = useRuntimeConfig();
const userStore = useUserStore();

// State
const prospects = ref<Prospect[]>([]);
const isLoading = ref(false);
const error = ref<string | null>(null);
const selectedProspects = ref<string[]>([]);
const searchQuery = ref('');
const filterSource = ref('');
const filterCategory = ref('');
const currentPage = ref(1);
const pageSize = 50;

// Computed
const totalProspects = computed(() => prospects.value.length);
const prospectsWithEmail = computed(() => prospects.value.filter(p => p.email).length);
const prospectsWithWebsite = computed(() => prospects.value.filter(p => p.website).length);
const prospectsWithPhone = computed(() => prospects.value.filter(p => p.phone).length);

const filteredProspects = computed(() => {
  let filtered = prospects.value;
  
  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    filtered = filtered.filter(p =>
      p.name.toLowerCase().includes(query) ||
      p.city?.toLowerCase().includes(query) ||
      p.email?.toLowerCase().includes(query) ||
      p.phone?.toLowerCase().includes(query)
    );
  }
  
  // Source filter
  if (filterSource.value) {
    filtered = filtered.filter(p => p.source === filterSource.value);
  }
  
  // Category filter
  if (filterCategory.value) {
    const cat = filterCategory.value.toLowerCase();
    filtered = filtered.filter(p => p.category.toLowerCase().includes(cat));
  }
  
  return filtered;
});

const totalPages = computed(() => Math.ceil(filteredProspects.value.length / pageSize));

const paginatedProspects = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  const end = start + pageSize;
  return filteredProspects.value.slice(start, end);
});

// Methods
async function loadProspects() {
  try {
    isLoading.value = true;
    error.value = null;
    
    const response = await $fetch<Prospect[]>(
      `${config.public.apiBase}/api/v1/prospects`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(userStore.token && { Authorization: `Bearer ${userStore.token}` })
        }
      }
    );
    
    prospects.value = response;
  } catch (err: any) {
    error.value = err.message || 'Erreur lors du chargement des prospects';
    console.error('Error loading prospects:', err);
  } finally {
    isLoading.value = false;
  }
}

function refreshProspects() {
  currentPage.value = 1;
  loadProspects();
}

function clearFilters() {
  searchQuery.value = '';
  filterSource.value = '';
  filterCategory.value = '';
  currentPage.value = 1;
}

function toggleProspect(prospectId: string) {
  const index = selectedProspects.value.indexOf(prospectId);
  if (index > -1) {
    selectedProspects.value.splice(index, 1);
  } else {
    selectedProspects.value.push(prospectId);
  }
}

function viewProspect(prospect: Prospect) {
  // TODO: Implement prospect detail view
  console.log('View prospect:', prospect);
}

async function deleteProspect(prospect: Prospect) {
  if (!confirm(`Êtes-vous sûr de vouloir supprimer le prospect "${prospect.name}" ?`)) {
    return;
  }
  
  try {
    await $fetch(
      `${config.public.apiBase}/api/v1/prospects/${prospect.id}`,
      {
        method: 'DELETE',
        headers: {
          ...(userStore.token && { Authorization: `Bearer ${userStore.token}` })
        }
      }
    );
    
    // Remove from local list
    prospects.value = prospects.value.filter(p => p.id !== prospect.id);
  } catch (err: any) {
    alert(`Erreur lors de la suppression: ${err.message}`);
  }
}

// Lifecycle
onMounted(() => {
  loadProspects();
});
</script>

