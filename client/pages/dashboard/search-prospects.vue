<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-3xl font-bold text-[#f9f9f9]">Recherche de Prospects</h1>
      <p class="mt-2 text-sm text-muted">
        Lancez une recherche pour trouver de nouveaux prospects. Vous pouvez quitter cette page et revenir plus tard.
      </p>
    </div>

    <!-- Search Form (only show if no active job) -->
    <div v-if="!currentJob" class="card">
      <h2 class="text-xl font-semibold text-[#f9f9f9] mb-6">Nouvelle Recherche</h2>
      <form @submit.prevent="startSearch" class="space-y-4">
        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label class="block text-xs font-medium text-muted mb-1.5">Catégorie</label>
            <input
              v-model="searchForm.category"
              type="text"
              placeholder="Ex: restaurant, plombier, etc."
              required
              class="input-field"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-muted mb-1.5">Ville</label>
            <input
              v-model="searchForm.city"
              type="text"
              placeholder="Ex: Paris, Lyon, etc."
              required
              class="input-field"
            />
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label class="block text-xs font-medium text-muted mb-1.5">Nombre maximum de résultats</label>
            <input
              v-model.number="searchForm.maxResults"
              type="number"
              min="1"
              max="100"
              required
              class="input-field"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-muted mb-1.5">Source</label>
            <select
              v-model="searchForm.source"
              class="input-field"
            >
              <option value="">Toutes les sources</option>
              <option value="google">Google</option>
              <option value="pagesjaunes">Pages Jaunes</option>
              <option value="mock">Mock (Test)</option>
            </select>
          </div>
        </div>

        <div class="flex items-center">
          <input
            v-model="searchForm.skipDuplicates"
            type="checkbox"
            id="skipDuplicates"
            class="w-4 h-4 text-[#f9f9f9] bg-[#050505] border-[#30363d] rounded focus:ring-[#f9f9f9]"
          />
          <label for="skipDuplicates" class="ml-2 text-sm text-muted">
            Ignorer les prospects déjà enregistrés (recommandé)
          </label>
        </div>

        <div class="flex items-center gap-4 pt-4">
          <button
            type="submit"
            :disabled="isStarting"
            class="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="isStarting">Démarrage...</span>
            <span v-else>Lancer la recherche</span>
          </button>
          <NuxtLink
            to="/dashboard/my-prospects"
            class="btn-secondary"
          >
            Voir mes prospects
          </NuxtLink>
        </div>
      </form>
    </div>

    <!-- Job Progress -->
    <div v-if="currentJob" class="card">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h2 class="text-xl font-semibold text-[#f9f9f9]">
            Recherche en cours
            <span v-if="currentJob.status === 'completed'" class="ml-2 text-[#2BAD5F]">✓ Terminée</span>
            <span v-else-if="currentJob.status === 'failed'" class="ml-2 text-[#DC4747]">✗ Échec</span>
          </h2>
          <p class="mt-1 text-sm text-muted">
            {{ currentJob.category }} à {{ currentJob.city }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="refreshJobStatus"
            :disabled="isRefreshing"
            class="btn-secondary text-xs px-3 py-1.5 disabled:opacity-50"
          >
            <i class="fa-solid fa-rotate-right mr-1"></i>
            Actualiser
          </button>
          <button
            v-if="currentJob.status === 'completed' || currentJob.status === 'failed'"
            @click="resetSearch"
            class="btn-primary text-xs px-3 py-1.5"
          >
            Nouvelle recherche
          </button>
        </div>
      </div>

      <!-- Progress Bar -->
      <div v-if="currentJob.status === 'running'" class="space-y-4">
        <div>
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium text-muted">
              {{ currentJob.progress.current }} / {{ currentJob.progress.total }} prospects traités
            </span>
            <span class="text-sm font-medium text-muted">
              {{ Math.round(currentJob.progress.percentage) }}%
            </span>
          </div>
          <div class="w-full h-3 bg-[#050505] border border-[#30363d] rounded-full overflow-hidden">
            <div
              class="h-full bg-[#f9f9f9] transition-all duration-300 rounded-full"
              :style="{ width: currentJob.progress.percentage + '%' }"
            ></div>
          </div>
        </div>

        <div v-if="currentJob.progress.current_prospect" class="p-3 bg-[#1a1a1a] border border-[#30363d] rounded-lg">
          <p class="text-sm text-[#f9f9f9]">
            <span class="font-medium">En cours:</span> {{ currentJob.progress.current_prospect }}
          </p>
        </div>

        <div v-if="currentJob.progress.estimated_time_remaining !== null" class="flex items-center gap-2 text-sm text-muted">
          <i class="fa-solid fa-clock w-4 h-4"></i>
          Temps restant estimé: {{ formatTime(currentJob.progress.estimated_time_remaining) }}
        </div>

        <div class="p-4 bg-[#1a1a1a] border border-[#30363d] rounded-lg">
          <div class="flex items-start gap-3">
            <i class="fa-solid fa-info-circle text-[#8b949e] mt-0.5"></i>
            <div class="flex-1">
              <p class="text-sm font-medium text-[#f9f9f9]">Vous pouvez quitter cette page</p>
              <p class="mt-1 text-sm text-muted">
                La recherche continue en arrière-plan. Revenez plus tard pour voir les résultats.
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Results -->
      <div v-if="currentJob.status === 'completed'" class="space-y-4">
        <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div class="p-4 bg-[#1a1a1a] border border-[#30363d] rounded-lg">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-[#050505] border border-[#30363d] rounded-lg">
                <i class="fa-solid fa-check text-[#2BAD5F] text-lg"></i>
              </div>
              <div>
                <p class="text-2xl font-bold text-[#f9f9f9]">{{ currentJob.results.length }}</p>
                <p class="text-sm text-muted">Prospects ajoutés</p>
              </div>
            </div>
          </div>

          <div class="p-4 bg-[#1a1a1a] border border-[#30363d] rounded-lg">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-[#050505] border border-[#30363d] rounded-lg">
                <i class="fa-solid fa-file-lines text-[#f9f9f9] text-lg"></i>
              </div>
              <div>
                <p class="text-2xl font-bold text-[#f9f9f9]">{{ currentJob.progress.total }}</p>
                <p class="text-sm text-muted">Prospects trouvés</p>
              </div>
            </div>
          </div>

          <div class="p-4 bg-[#1a1a1a] border border-[#30363d] rounded-lg">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-[#050505] border border-[#30363d] rounded-lg">
                <i class="fa-solid fa-ban text-muted text-lg"></i>
              </div>
              <div>
                <p class="text-2xl font-bold text-[#f9f9f9]">{{ currentJob.skipped_duplicates }}</p>
                <p class="text-sm text-muted">Doublons ignorés</p>
              </div>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-4 pt-4">
          <NuxtLink
            to="/dashboard/my-prospects"
            class="btn-primary"
          >
            Voir mes prospects
          </NuxtLink>
          <button
            @click="resetSearch"
            class="btn-secondary"
          >
            Nouvelle recherche
          </button>
        </div>
      </div>

      <!-- Error -->
      <div v-if="currentJob.status === 'failed'" class="p-4 text-[#DC4747] bg-[#1a1a1a] border border-[#DC4747] rounded-lg">
        <p class="font-semibold">La recherche a échoué</p>
        <p class="mt-1 text-sm text-muted">{{ currentJob.error }}</p>
        <button
          @click="resetSearch"
          class="btn-danger mt-4"
        >
          Réessayer
        </button>
      </div>
    </div>

    <!-- Recent Jobs -->
    <div v-if="recentJobs.length > 0" class="card">
      <h2 class="text-xl font-semibold text-[#f9f9f9] mb-4">Recherches récentes</h2>
      <div class="space-y-3">
        <div
          v-for="job in recentJobs"
          :key="job.id"
          class="flex items-center justify-between p-4 border border-[#30363d] rounded-lg hover:bg-[#050505] cursor-pointer transition-colors"
          @click="loadJob(job.id)"
        >
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <p class="font-medium text-[#f9f9f9]">{{ job.category }} à {{ job.city }}</p>
              <span
                :class="{
                  'px-2 py-0.5 text-xs font-medium rounded-full': true,
                  'bg-[#1a1a1a] text-[#2BAD5F] border border-[#2BAD5F]': job.status === 'completed',
                  'bg-[#1a1a1a] text-[#8b949e] border border-[#8b949e]': job.status === 'running',
                  'bg-[#1a1a1a] text-[#DC4747] border border-[#DC4747]': job.status === 'failed',
                  'bg-[#1a1a1a] text-muted border border-[#30363d]': job.status === 'pending'
                }"
              >
                {{ formatStatus(job.status) }}
              </span>
            </div>
            <p class="mt-1 text-sm text-muted">
              {{ new Date(job.created_at).toLocaleString('fr-FR') }}
              <span v-if="job.status === 'completed'" class="ml-2">
                • {{ job.results.length }} prospects ajoutés
              </span>
            </p>
          </div>
          <i class="fa-solid fa-chevron-right text-muted"></i>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRuntimeConfig } from '#app';
import { useUserStore } from '~/stores/user';

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth']
});

interface ScrapingJob {
  id: string;
  user_id: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  category: string | null;
  city: string | null;
  max_results: number;
  source: string | null;
  skip_duplicates: boolean;
  progress: {
    current: number;
    total: number;
    percentage: number;
    current_prospect: string | null;
    estimated_time_remaining: number | null;
  };
  results: number[];
  skipped_duplicates: number;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

const config = useRuntimeConfig();
const userStore = useUserStore();

// State
const searchForm = ref({
  category: '',
  city: '',
  maxResults: 50,
  source: '',
  skipDuplicates: true
});

const currentJob = ref<ScrapingJob | null>(null);
const recentJobs = ref<ScrapingJob[]>([]);
const isStarting = ref(false);
const isRefreshing = ref(false);
let pollInterval: ReturnType<typeof setInterval> | null = null;

// Methods
async function startSearch() {
  try {
    isStarting.value = true;
    
    const response = await $fetch<ScrapingJob>(
      `${config.public.apiBase}/api/v1/scraping-jobs`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(userStore.token && { Authorization: `Bearer ${userStore.token}` })
        },
        body: {
          category: searchForm.value.category || null,
          city: searchForm.value.city || null,
          max_results: searchForm.value.maxResults,
          source: searchForm.value.source || null,
          skip_duplicates: searchForm.value.skipDuplicates
        }
      }
    );
    
    currentJob.value = response;
    startPolling();
  } catch (err: any) {
    alert(`Erreur: ${err.data?.detail || err.message}`);
  } finally {
    isStarting.value = false;
  }
}

async function refreshJobStatus() {
  if (!currentJob.value) return;
  
  try {
    isRefreshing.value = true;
    
    const response = await $fetch<ScrapingJob>(
      `${config.public.apiBase}/api/v1/scraping-jobs/${currentJob.value.id}`,
      {
        method: 'GET',
        headers: {
          ...(userStore.token && { Authorization: `Bearer ${userStore.token}` })
        }
      }
    );
    
    currentJob.value = response;
    
    // Stop polling if job is completed or failed
    if (response.status === 'completed' || response.status === 'failed') {
      stopPolling();
      await loadRecentJobs();
    }
  } catch (err: any) {
    console.error('Error refreshing job:', err);
  } finally {
    isRefreshing.value = false;
  }
}

async function loadJob(jobId: string) {
  try {
    const response = await $fetch<ScrapingJob>(
      `${config.public.apiBase}/api/v1/scraping-jobs/${jobId}`,
      {
        method: 'GET',
        headers: {
          ...(userStore.token && { Authorization: `Bearer ${userStore.token}` })
        }
      }
    );
    
    currentJob.value = response;
    
    if (response.status === 'running') {
      startPolling();
    }
  } catch (err: any) {
    alert(`Erreur: ${err.message}`);
  }
}

async function loadRecentJobs() {
  try {
    const response = await $fetch<ScrapingJob[]>(
      `${config.public.apiBase}/api/v1/scraping-jobs`,
      {
        method: 'GET',
        headers: {
          ...(userStore.token && { Authorization: `Bearer ${userStore.token}` })
        }
      }
    );
    
    // Sort by creation date (most recent first) and limit to 5
    recentJobs.value = response
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 5);
    
    // If there's a running job and no current job, set it as current
    if (!currentJob.value) {
      const runningJob = recentJobs.value.find(j => j.status === 'running');
      if (runningJob) {
        currentJob.value = runningJob;
        startPolling();
      }
    }
  } catch (err: any) {
    console.error('Error loading recent jobs:', err);
  }
}

function resetSearch() {
  currentJob.value = null;
  stopPolling();
  searchForm.value = {
    category: '',
    city: '',
    maxResults: 50,
    source: '',
    skipDuplicates: true
  };
}

function startPolling() {
  stopPolling();
  pollInterval = setInterval(() => {
    refreshJobStatus();
  }, 2000); // Poll every 2 seconds
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds} secondes`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}min ${remainingSeconds}s`;
}

function formatStatus(status: string): string {
  const statusMap: Record<string, string> = {
    pending: 'En attente',
    running: 'En cours',
    completed: 'Terminée',
    failed: 'Échec'
  };
  return statusMap[status] || status;
}

// Lifecycle
onMounted(() => {
  loadRecentJobs();
});

onUnmounted(() => {
  stopPolling();
});
</script>

