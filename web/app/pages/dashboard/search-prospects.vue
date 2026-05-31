<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-3xl font-bold text-[#f9f9f9]">Recherche de Prospects</h1>
      <p class="text-muted mt-2 text-sm">
        Lancez une recherche pour trouver de nouveaux prospects. Vous pouvez quitter cette page et revenir plus tard.
      </p>
    </div>

    <!-- Search Form (only show if no active job) -->
    <div v-if="!currentJob" class="card">
      <h2 class="mb-6 text-xl font-semibold text-[#f9f9f9]">Nouvelle Recherche</h2>
      <form class="space-y-4" @submit.prevent="startSearch">
        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">Catégorie</label>
            <input
              v-model="searchForm.category"
              type="text"
              placeholder="Ex: restaurant, plombier, etc."
              required
              class="input-field"
            />
          </div>
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">Ville</label>
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
            <label class="text-muted mb-1.5 block text-xs font-medium">Nombre maximum de résultats</label>
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
            <label class="text-muted mb-1.5 block text-xs font-medium">Source</label>
            <select v-model="searchForm.source" class="input-field">
              <option
                v-for="option in PROSPECT_SOURCE_SEARCH_OPTIONS"
                :key="option.value || 'all'"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>
          </div>
        </div>

        <div class="space-y-3">
          <UiCheckbox
            id="onlyWithoutWebsite"
            v-model="searchForm.onlyWithoutWebsite"
            label="Uniquement les prospects sans site web (recommandé)"
          />
          <UiCheckbox
            id="skipDuplicates"
            v-model="searchForm.skipDuplicates"
            label="Ignorer les prospects déjà enregistrés (recommandé)"
          />
        </div>

        <div class="flex items-center gap-4 pt-4">
          <button
            type="submit"
            :disabled="isStarting"
            class="btn-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span v-if="isStarting">Démarrage...</span>
            <span v-else>Lancer la recherche</span>
          </button>
          <NuxtLink to="/dashboard/my-prospects" class="btn-secondary"> Voir mes prospects </NuxtLink>
        </div>
      </form>
    </div>

    <!-- Job Progress -->
    <div v-if="currentJob" class="card">
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h2 class="text-xl font-semibold text-[#f9f9f9]">
            Recherche en cours
            <span v-if="currentJob.status === 'completed'" class="ml-2 text-[#2BAD5F]">✓ Terminée</span>
            <span v-else-if="currentJob.status === 'failed'" class="ml-2 text-[#DC4747]">✗ Échec</span>
          </h2>
          <p class="text-muted mt-1 text-sm">{{ currentJob.category }} à {{ currentJob.city }}</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            :disabled="isRefreshing"
            class="btn-secondary px-3 py-1.5 text-xs disabled:opacity-50"
            @click="refreshJobStatus"
          >
            <i class="fa-solid fa-rotate-right mr-1"></i>
            Actualiser
          </button>
          <button
            v-if="currentJob.status === 'completed' || currentJob.status === 'failed'"
            class="btn-primary px-3 py-1.5 text-xs"
            @click="resetSearch"
          >
            Nouvelle recherche
          </button>
        </div>
      </div>

      <!-- Progress + live stream -->
      <div v-if="currentJob.status === 'running' || currentJob.status === 'pending'" class="space-y-4">
        <div>
          <div class="mb-2 flex items-center justify-between">
            <span class="text-muted text-sm font-medium">
              {{ liveProgress.current }} / {{ liveProgress.total || currentJob.max_results }} prospects ajoutés
            </span>
            <span class="text-muted text-sm font-medium"> {{ Math.round(liveProgress.percentage) }}% </span>
          </div>
          <div class="h-3 w-full overflow-hidden rounded-full border border-[#30363d] bg-[#050505]">
            <div
              class="h-full rounded-full bg-[#f9f9f9] transition-all duration-300"
              :style="{ width: Math.min(liveProgress.percentage, 100) + '%' }"
            ></div>
          </div>
        </div>

        <div v-if="liveProgress.current_prospect" class="rounded-lg border border-[#30363d] bg-[#1a1a1a] p-3">
          <p class="text-sm text-[#f9f9f9]">
            <span class="font-medium">En cours:</span> {{ liveProgress.current_prospect }}
          </p>
        </div>

        <div
          v-if="liveProgress.estimated_time_remaining !== null && liveProgress.estimated_time_remaining > 0"
          class="text-muted flex items-center gap-2 text-sm"
        >
          <i class="fa-solid fa-clock h-4 w-4"></i>
          Temps restant estimé: {{ formatTime(liveProgress.estimated_time_remaining) }}
        </div>

        <div class="flex items-center gap-2 text-xs">
          <span
            class="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5"
            :class="streamConnected ? 'border-[#2BAD5F] text-[#2BAD5F]' : 'border-[#8b949e] text-[#8b949e]'"
          >
            <span class="h-1.5 w-1.5 rounded-full" :class="streamConnected ? 'bg-[#2BAD5F]' : 'bg-[#8b949e]'"></span>
            {{ streamConnected ? 'Temps réel actif' : 'Connexion temps réel…' }}
          </span>
          <span v-if="streamSkipped > 0" class="text-muted"> {{ streamSkipped }} doublon(s) ignoré(s) </span>
        </div>

        <ScrapingJobLivePanel
          :logs="streamLogs"
          :prospects="streamProspects"
          :is-running="currentJob.status === 'running'"
        />

        <div class="rounded-lg border border-[#30363d] bg-[#1a1a1a] p-4">
          <div class="flex items-start gap-3">
            <i class="fa-solid fa-info-circle mt-0.5 text-[#8b949e]"></i>
            <div class="flex-1">
              <p class="text-sm font-medium text-[#f9f9f9]">Vous pouvez quitter cette page</p>
              <p class="text-muted mt-1 text-sm">
                La recherche continue en arrière-plan. Revenez plus tard pour voir les résultats.
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Live recap after completion (last run) -->
      <div v-if="currentJob.status === 'completed' && streamLogs.length > 0" class="space-y-4">
        <ScrapingJobLivePanel :logs="streamLogs" :prospects="streamProspects" :is-running="false" />
      </div>

      <!-- Results -->
      <div v-if="currentJob.status === 'completed'" class="space-y-4">
        <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div class="rounded-lg border border-[#30363d] bg-[#1a1a1a] p-4">
            <div class="flex items-center gap-3">
              <div class="rounded-lg border border-[#30363d] bg-[#050505] p-2">
                <i class="fa-solid fa-check text-lg text-[#2BAD5F]"></i>
              </div>
              <div>
                <p class="text-2xl font-bold text-[#f9f9f9]">{{ currentJob.results.length }}</p>
                <p class="text-muted text-sm">Prospects ajoutés</p>
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-[#30363d] bg-[#1a1a1a] p-4">
            <div class="flex items-center gap-3">
              <div class="rounded-lg border border-[#30363d] bg-[#050505] p-2">
                <i class="fa-solid fa-file-lines text-lg text-[#f9f9f9]"></i>
              </div>
              <div>
                <p class="text-2xl font-bold text-[#f9f9f9]">{{ currentJob.progress.total }}</p>
                <p class="text-muted text-sm">Prospects trouvés</p>
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-[#30363d] bg-[#1a1a1a] p-4">
            <div class="flex items-center gap-3">
              <div class="rounded-lg border border-[#30363d] bg-[#050505] p-2">
                <i class="fa-solid fa-ban text-muted text-lg"></i>
              </div>
              <div>
                <p class="text-2xl font-bold text-[#f9f9f9]">{{ currentJob.skipped_duplicates }}</p>
                <p class="text-muted text-sm">Doublons ignorés</p>
              </div>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-4 pt-4">
          <NuxtLink to="/dashboard/my-prospects" class="btn-primary"> Voir mes prospects </NuxtLink>
          <button class="btn-secondary" @click="resetSearch">Nouvelle recherche</button>
        </div>
      </div>

      <!-- Error -->
      <div
        v-if="currentJob.status === 'failed'"
        class="rounded-lg border border-[#DC4747] bg-[#1a1a1a] p-4 text-[#DC4747]"
      >
        <p class="font-semibold">La recherche a échoué</p>
        <p class="text-muted mt-1 text-sm">{{ currentJob.error }}</p>
        <button class="btn-danger mt-4" @click="resetSearch">Réessayer</button>
      </div>
    </div>

    <!-- Recent Jobs -->
    <div v-if="recentJobs.length > 0" class="card">
      <h2 class="mb-4 text-xl font-semibold text-[#f9f9f9]">Recherches récentes</h2>
      <div class="space-y-3">
        <div
          v-for="job in recentJobs"
          :key="job.id"
          class="flex cursor-pointer items-center justify-between rounded-lg border border-[#30363d] p-4 transition-colors hover:bg-[#050505]"
          @click="loadJob(job.id)"
        >
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <p class="font-medium text-[#f9f9f9]">{{ job.category }} à {{ job.city }}</p>
              <span
                :class="{
                  'rounded-full px-2 py-0.5 text-xs font-medium': true,
                  'border border-[#2BAD5F] bg-[#1a1a1a] text-[#2BAD5F]': job.status === 'completed',
                  'border border-[#8b949e] bg-[#1a1a1a] text-[#8b949e]': job.status === 'running',
                  'border border-[#DC4747] bg-[#1a1a1a] text-[#DC4747]': job.status === 'failed',
                  'text-muted border border-[#30363d] bg-[#1a1a1a]': job.status === 'pending',
                }"
              >
                {{ formatStatus(job.status) }}
              </span>
            </div>
            <p class="text-muted mt-1 text-sm">
              {{ new Date(job.created_at).toLocaleString('fr-FR') }}
              <span v-if="job.status === 'completed'" class="ml-2"> • {{ job.results.length }} prospects ajoutés </span>
            </p>
          </div>
          <i class="fa-solid fa-chevron-right text-muted"></i>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRuntimeConfig } from '#app'
import { useUserStore } from '~/stores/user'
import { PROSPECT_SOURCE_SEARCH_OPTIONS } from '~/constants/prospectSources'
import { useScrapingJobStream } from '~/composables/useScrapingJobStream'
import type { Prospect } from '~/types'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

interface ScrapingJob {
  id: string
  user_id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  category: string | null
  city: string | null
  max_results: number
  source: string | null
  skip_duplicates: boolean
  progress: {
    current: number
    total: number
    percentage: number
    current_prospect: string | null
    estimated_time_remaining: number | null
  }
  logs?: string[]
  live_prospects?: Prospect[]
  results: number[]
  skipped_duplicates: number
  error: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

const config = useRuntimeConfig()
const userStore = useUserStore()

const SEARCH_FORM_STORAGE_KEY = 'devleadhunter-search-form'

interface SearchFormState {
  category: string
  city: string
  maxResults: number
  source: string
  skipDuplicates: boolean
  onlyWithoutWebsite: boolean
}

const defaultSearchForm = (): SearchFormState => ({
  category: '',
  city: '',
  maxResults: 50,
  source: '',
  skipDuplicates: true,
  onlyWithoutWebsite: true,
})

function loadSavedSearchForm(): SearchFormState {
  if (import.meta.server) {
    return defaultSearchForm()
  }
  try {
    const raw = localStorage.getItem(SEARCH_FORM_STORAGE_KEY)
    if (!raw) {
      return defaultSearchForm()
    }
    const parsed = JSON.parse(raw) as Partial<SearchFormState>
    return { ...defaultSearchForm(), ...parsed }
  } catch {
    return defaultSearchForm()
  }
}

function persistSearchForm(form: SearchFormState): void {
  if (import.meta.server) {
    return
  }
  localStorage.setItem(SEARCH_FORM_STORAGE_KEY, JSON.stringify(form))
}

// State — restored from last search
const searchForm = ref<SearchFormState>(loadSavedSearchForm())

const currentJob = ref<ScrapingJob | null>(null)
const recentJobs = ref<ScrapingJob[]>([])
const isStarting = ref(false)
const isRefreshing = ref(false)
const stream = useScrapingJobStream()
let pollInterval: ReturnType<typeof setInterval> | null = null

const liveProgress = computed(() => {
  if (stream.progress.value.total > 0 || stream.progress.value.current > 0) {
    return stream.progress.value
  }
  return currentJob.value?.progress ?? stream.progress.value
})

const streamLogs = computed(() => stream.logs.value)
const streamProspects = computed(() => stream.prospects.value)
const streamConnected = computed(() => stream.isConnected.value)
const streamSkipped = computed(() => stream.skippedDuplicates.value)

function attachStream(job: ScrapingJob): void {
  stream.hydrateFromJob({
    logs: job.logs,
    live_prospects: job.live_prospects,
    progress: job.progress,
    skipped_duplicates: job.skipped_duplicates,
  })

  const token = userStore.token
  if (!token) {
    return
  }

  stream.connect(job.id, token, {
    onDone: async (summary) => {
      stopPolling()
      stream.disconnect()
      await refreshJobStatus()
      if (currentJob.value) {
        currentJob.value.status = 'completed'
        currentJob.value.skipped_duplicates = summary.skipped_duplicates
      }
    },
    onError: async () => {
      stopPolling()
      await refreshJobStatus()
    },
  })
}

// Methods
async function startSearch() {
  try {
    isStarting.value = true
    persistSearchForm(searchForm.value)

    const response = await $fetch<ScrapingJob>(`${config.public.apiBase}/api/v1/scraping-jobs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(userStore.token && { Authorization: `Bearer ${userStore.token}` }),
      },
      body: {
        category: searchForm.value.category || null,
        city: searchForm.value.city || null,
        max_results: searchForm.value.maxResults,
        source: searchForm.value.source || null,
        skip_duplicates: searchForm.value.skipDuplicates,
        only_without_website: searchForm.value.onlyWithoutWebsite,
      },
    })

    currentJob.value = response
    stream.reset()
    attachStream(response)
    startPolling()
  } catch (err: unknown) {
    alert(`Erreur: ${err.data?.detail || err.message}`)
  } finally {
    isStarting.value = false
  }
}

async function refreshJobStatus() {
  if (!currentJob.value) return

  try {
    isRefreshing.value = true

    const response = await $fetch<ScrapingJob>(`${config.public.apiBase}/api/v1/scraping-jobs/${currentJob.value.id}`, {
      method: 'GET',
      headers: {
        ...(userStore.token && { Authorization: `Bearer ${userStore.token}` }),
      },
    })

    currentJob.value = response

    // Stop polling if job is completed or failed
    if (response.status === 'completed' || response.status === 'failed') {
      stopPolling()
      await loadRecentJobs()
    }
  } catch (err: unknown) {
    console.error('Error refreshing job:', err)
  } finally {
    isRefreshing.value = false
  }
}

async function loadJob(jobId: string) {
  try {
    const response = await $fetch<ScrapingJob>(`${config.public.apiBase}/api/v1/scraping-jobs/${jobId}`, {
      method: 'GET',
      headers: {
        ...(userStore.token && { Authorization: `Bearer ${userStore.token}` }),
      },
    })

    currentJob.value = response
    stream.reset()
    attachStream(response)

    if (response.status === 'running' || response.status === 'pending') {
      startPolling()
    }
  } catch (err: unknown) {
    alert(`Erreur: ${err.message}`)
  }
}

async function loadRecentJobs() {
  try {
    const response = await $fetch<ScrapingJob[]>(`${config.public.apiBase}/api/v1/scraping-jobs`, {
      method: 'GET',
      headers: {
        ...(userStore.token && { Authorization: `Bearer ${userStore.token}` }),
      },
    })

    // Sort by creation date (most recent first) and limit to 5
    recentJobs.value = response
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 5)

    // If there's a running job and no current job, set it as current
    if (!currentJob.value) {
      const runningJob = recentJobs.value.find((j) => j.status === 'running')
      if (runningJob) {
        currentJob.value = runningJob
        stream.reset()
        attachStream(runningJob)
        startPolling()
      }
    }
  } catch (err: unknown) {
    console.error('Error loading recent jobs:', err)
  }
}

function resetSearch() {
  currentJob.value = null
  stream.disconnect()
  stream.reset()
  stopPolling()
}

watch(
  searchForm,
  (form) => {
    persistSearchForm(form)
  },
  { deep: true },
)

function startPolling() {
  stopPolling()
  pollInterval = setInterval(() => {
    refreshJobStatus()
  }, 8000)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds} secondes`
  }
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}min ${remainingSeconds}s`
}

function formatStatus(status: string): string {
  const statusMap: Record<string, string> = {
    pending: 'En attente',
    running: 'En cours',
    completed: 'Terminée',
    failed: 'Échec',
  }
  return statusMap[status] || status
}

// Lifecycle
onMounted(() => {
  loadRecentJobs()
})

onUnmounted(() => {
  stopPolling()
  stream.disconnect()
})
</script>
