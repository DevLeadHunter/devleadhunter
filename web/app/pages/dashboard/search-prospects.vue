<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <p class="app-label flex items-center gap-2">
        <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
        Prospection
      </p>
      <h1 class="app-page-title mt-2">Trouver des prospects</h1>
      <p class="mt-1.5 text-sm text-[var(--app-ink-soft)]">
        Décrivez un métier et une ville — DevLeadHunter va chercher les artisans qui correspondent. La recherche
        continue en arrière-plan, vous pouvez quitter la page.
      </p>
    </div>

    <!-- Search Form (only show if no active job) -->
    <div v-if="!currentJob" class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_260px]">
      <form class="app-card space-y-5 p-5 md:p-6" @submit.prevent="startSearch">
        <div class="space-y-4">
          <div>
            <label for="search-category" class="app-label mb-1.5 block">
              Métier recherché <span class="text-[var(--app-accent)]">*</span>
            </label>
            <div class="relative">
              <UIcon
                name="i-lucide-hammer"
                class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
              />
              <input
                id="search-category"
                v-model="searchForm.category"
                type="text"
                placeholder="Plombier, électricien, restaurant…"
                required
                class="input-field pl-9"
              />
            </div>
            <div class="mt-2 flex flex-wrap gap-1.5">
              <button
                v-for="quick in QUICK_CATEGORIES"
                :key="quick"
                type="button"
                class="cursor-pointer rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] px-2.5 py-1 text-xs text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-ink-soft)] hover:text-[var(--app-ink)]"
                @click="searchForm.category = quick"
              >
                {{ quick }}
              </button>
            </div>
          </div>

          <div>
            <label for="search-city" class="app-label mb-1.5 block">
              Ville <span class="text-[var(--app-accent)]">*</span>
            </label>
            <UiCityAutocompleteInput v-model="searchForm.city" input-id="search-city" required show-icon />
          </div>

          <div>
            <label for="search-max-results" class="app-label mb-1.5 block">Nombre maximum de résultats</label>
            <input
              id="search-max-results"
              v-model.number="searchForm.maxResults"
              type="number"
              min="1"
              max="100"
              required
              class="input-field"
            />
          </div>

          <div>
            <label for="search-source" class="app-label mb-1.5 block">Source</label>
            <select id="search-source" v-model="searchForm.source" class="input-field">
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

        <div class="space-y-3 border-t border-[var(--app-line-soft)] pt-4">
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

        <div class="flex items-center gap-3 border-t border-[var(--app-line-soft)] pt-4">
          <button
            type="submit"
            :disabled="isStarting"
            class="btn-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            <UIcon
              :name="isStarting ? 'i-lucide-loader-circle' : 'i-lucide-search'"
              :class="['h-4 w-4', isStarting && 'animate-spin']"
            />
            {{ isStarting ? 'Démarrage…' : 'Lancer la recherche' }}
          </button>
          <NuxtLink to="/dashboard/my-prospects" class="btn-secondary">Voir mes prospects</NuxtLink>
        </div>
      </form>

      <!-- Side rail : comment ça marche -->
      <aside class="app-card h-fit space-y-4 p-5">
        <p class="app-label">Comment ça marche</p>
        <ol class="space-y-3">
          <li v-for="(step, index) in SEARCH_STEPS" :key="step" class="flex items-start gap-3">
            <span
              class="font-label flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--app-surface-2)] text-[0.65rem] font-semibold text-[var(--app-ink)]"
            >
              {{ index + 1 }}
            </span>
            <p class="text-xs leading-relaxed text-[var(--app-ink-soft)]">{{ step }}</p>
          </li>
        </ol>
        <p
          class="flex items-center gap-2 border-t border-[var(--app-line-soft)] pt-3 text-[11px] leading-relaxed text-[var(--app-ink-soft)]"
        >
          <UIcon name="i-lucide-info" class="h-3.5 w-3.5 shrink-0 text-[var(--app-accent-ink)]" />
          Chaque prospect trouvé consomme des crédits selon vos paramètres.
        </p>
      </aside>
    </div>

    <!-- Job Progress -->
    <div v-if="currentJob" class="card">
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h2 class="text-xl font-semibold text-[var(--app-ink)]">
            Recherche en cours
            <span v-if="currentJob.status === 'completed'" class="ml-2 text-[var(--app-green)]">✓ Terminée</span>
            <span v-else-if="currentJob.status === 'failed'" class="ml-2 text-[var(--app-red)]">✗ Échec</span>
          </h2>
          <p class="text-muted mt-1 text-sm">{{ currentJob.category }} à {{ currentJob.city }}</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            :disabled="isRefreshing"
            class="btn-secondary px-3 py-1.5 text-xs disabled:opacity-50"
            @click="refreshJobStatus"
          >
            <UIcon name="i-lucide-rotate-cw" :class="['h-3.5 w-3.5', isRefreshing && 'animate-spin']" />
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
          <div class="h-3 w-full overflow-hidden rounded-full border border-[var(--app-line)] bg-[var(--app-bg)]">
            <div
              class="h-full rounded-full bg-[var(--app-ink)] transition-all duration-300"
              :style="{ width: Math.min(liveProgress.percentage, 100) + '%' }"
            ></div>
          </div>
        </div>

        <div
          v-if="liveProgress.current_prospect"
          class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-3"
        >
          <p class="text-sm text-[var(--app-ink)]">
            <span class="font-medium">En cours:</span> {{ liveProgress.current_prospect }}
          </p>
        </div>

        <div
          v-if="liveProgress.estimated_time_remaining !== null && liveProgress.estimated_time_remaining > 0"
          class="text-muted flex items-center gap-2 text-sm"
        >
          <UIcon name="i-lucide-clock" class="h-4 w-4" />
          Temps restant estimé : {{ formatTime(liveProgress.estimated_time_remaining) }}
        </div>

        <div class="flex items-center gap-2 text-xs">
          <span
            class="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5"
            :class="
              streamConnected
                ? 'border-[var(--app-green)] text-[var(--app-green)]'
                : 'border-[var(--app-ink-soft)] text-[var(--app-ink-soft)]'
            "
          >
            <span
              class="h-1.5 w-1.5 rounded-full"
              :class="streamConnected ? 'bg-[var(--app-green)]' : 'bg-[var(--app-ink-soft)]'"
            ></span>
            {{ streamConnected ? 'Temps réel actif' : 'Connexion temps réel…' }}
          </span>
          <span v-if="streamSkipped > 0" class="text-muted"> {{ streamSkipped }} doublon(s) ignoré(s) </span>
        </div>

        <ScrapingJobLivePanel
          :logs="streamLogs"
          :prospects="streamProspects"
          :is-running="currentJob.status === 'running'"
        />

        <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-4">
          <div class="flex items-start gap-3">
            <UIcon name="i-lucide-info" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-ink-soft)]" />
            <div class="flex-1">
              <p class="text-sm font-medium text-[var(--app-ink)]">Vous pouvez quitter cette page</p>
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
          <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-4">
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--app-green-soft)]">
                <UIcon name="i-lucide-user-check" class="h-5 w-5 text-[var(--app-green)]" />
              </div>
              <div>
                <p class="text-2xl font-bold text-[var(--app-ink)] tabular-nums">{{ currentJob.results.length }}</p>
                <p class="text-muted text-sm">Prospects ajoutés</p>
              </div>
            </div>
          </div>

          <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-4">
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--app-blue-soft)]">
                <UIcon name="i-lucide-search" class="h-5 w-5 text-[var(--app-blue)]" />
              </div>
              <div>
                <p class="text-2xl font-bold text-[var(--app-ink)] tabular-nums">{{ currentJob.progress.total }}</p>
                <p class="text-muted text-sm">Prospects trouvés</p>
              </div>
            </div>
          </div>

          <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-4">
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--app-surface-2)]">
                <UIcon name="i-lucide-copy-x" class="h-5 w-5 text-[var(--app-ink-soft)]" />
              </div>
              <div>
                <p class="text-2xl font-bold text-[var(--app-ink)] tabular-nums">{{ currentJob.skipped_duplicates }}</p>
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
        class="rounded-lg border border-[var(--app-red)] bg-[var(--app-surface)] p-4 text-[var(--app-red)]"
      >
        <p class="font-semibold">La recherche a échoué</p>
        <p class="text-muted mt-1 text-sm">{{ currentJob.error }}</p>
        <button class="btn-danger mt-4" @click="resetSearch">Réessayer</button>
      </div>
    </div>

    <!-- Recent Jobs -->
    <div v-if="recentJobs.length > 0" class="app-card p-5 md:p-6">
      <h2 class="mb-4 text-sm font-semibold text-[var(--app-ink)]">Recherches récentes</h2>
      <div class="divide-y divide-[var(--app-line-soft)]">
        <button
          v-for="job in recentJobs"
          :key="job.id"
          type="button"
          class="group flex w-full cursor-pointer items-center justify-between gap-3 py-3 text-left transition-colors first:pt-0 last:pb-0"
          @click="loadJob(job.id)"
        >
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <p
                class="truncate text-sm font-medium text-[var(--app-ink)] capitalize underline decoration-transparent underline-offset-4 transition-colors group-hover:decoration-[var(--app-accent)]"
              >
                {{ job.category }} · {{ job.city }}
              </p>
              <span :class="['app-badge', jobStatusVariant(job.status)]">{{ formatStatus(job.status) }}</span>
            </div>
            <p class="text-muted mt-0.5 text-xs">
              {{ new Date(job.created_at).toLocaleString('fr-FR') }}
              <span v-if="job.status === 'completed'"> · {{ job.results.length }} prospects ajoutés</span>
            </p>
          </div>
          <UIcon name="i-lucide-chevron-right" class="h-4 w-4 shrink-0 text-[var(--app-ink-soft)]" />
        </button>
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
import { useToast } from '~/composables/useToast'
import type { Prospect } from '~/types'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const toast = useToast()

/** Quick-pick trades filling the category field in one click. */
const QUICK_CATEGORIES: readonly string[] = [
  'Plombier',
  'Électricien',
  'Menuisier',
  'Restaurant',
  'Coiffeur',
  'Garagiste',
  'Serrurier',
  'Paysagiste',
]

/** Steps shown in the "comment ça marche" side rail. */
const SEARCH_STEPS: readonly string[] = [
  'Saisissez un métier et une ville, puis lancez la recherche.',
  'DevLeadHunter parcourt les sources et ajoute les artisans trouvés à vos prospects.',
  'Générez un site démo et lancez une campagne depuis la fiche de chaque prospect.',
]

/**
 * app-badge variant class for a scraping job status.
 * @param status - Job status.
 * @returns The badge variant modifier class.
 */
function jobStatusVariant(status: string): string {
  if (status === 'completed') return 'app-badge--success'
  if (status === 'failed') return 'app-badge--danger'
  if (status === 'running') return 'app-badge--info'
  return ''
}

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
    const detail =
      (err as { data?: { detail?: string }; message?: string })?.data?.detail ??
      (err as { message?: string })?.message ??
      'Erreur inconnue'
    toast.error(`Erreur : ${detail}`)
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
    toast.error(`Erreur : ${(err as { message?: string })?.message ?? 'chargement impossible'}`)
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
