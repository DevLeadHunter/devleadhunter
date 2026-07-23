<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="app-label flex items-center gap-2">
          <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
          Prospection
        </p>
        <h1 class="app-page-title mt-2">Trouver des prospects</h1>
        <p class="mt-1.5 text-sm text-[var(--app-ink-soft)]">
          Le formulaire s'ouvre dans un volet — les résultats s'affichent ici. La recherche continue en arrière-plan.
        </p>
      </div>
      <button class="app-btn-primary h-9 px-4 text-xs" @click="openSearchDrawer">
        <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
        Nouvelle recherche
      </button>
    </div>

    <div v-if="!store.currentJob" class="app-card px-6 py-14 text-center">
      <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />
      <h3 class="font-display mt-5 text-2xl font-semibold text-[var(--app-ink)]">Lancez une recherche</h3>
      <p class="mx-auto mt-2 max-w-md text-sm leading-relaxed text-[var(--app-ink-soft)]">
        Décrivez un métier et une ville dans le volet — DevLeadHunter trouve les artisans qui correspondent.
      </p>
      <button class="app-btn-primary mx-auto mt-6 inline-flex" @click="openSearchDrawer">
        <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
        Ouvrir le formulaire
      </button>
    </div>

    <div v-else class="app-card p-5 md:p-6">
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-[var(--app-ink)]">
            Recherche
            <span v-if="store.currentJob.status === 'completed'" class="ml-2 text-[var(--app-green)]">✓ Terminée</span>
            <span v-else-if="store.currentJob.status === 'cancelled'" class="ml-2 text-[var(--app-ink-soft)]">
              ⊘ Annulée
            </span>
            <span v-else-if="store.currentJob.status === 'failed'" class="ml-2 text-[var(--app-red)]">✗ Échec</span>
          </h2>
          <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
            {{ store.currentJob.category }} · {{ store.currentJob.city }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button
            :disabled="store.isRefreshing"
            class="app-btn-secondary h-8 px-3 text-xs disabled:opacity-50"
            @click="store.refreshJobStatus()"
          >
            <UIcon name="i-lucide-rotate-cw" :class="['h-3.5 w-3.5', store.isRefreshing && 'animate-spin']" />
            Actualiser
          </button>
          <button class="app-btn-primary h-8 px-3 text-xs" @click="openSearchDrawer">Nouvelle recherche</button>
        </div>
      </div>

      <div v-if="store.isSearching" class="space-y-4">
        <div>
          <div class="mb-2 flex items-center justify-between text-sm">
            <span class="font-medium text-[var(--app-ink-soft)]">
              {{ store.liveProgress.current }} / {{ store.liveProgress.total || store.currentJob.max_results }} ajoutés
            </span>
            <div class="flex items-center gap-3">
              <button
                type="button"
                class="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--app-red)] transition-opacity hover:opacity-80 disabled:opacity-50"
                :disabled="store.isCancelling"
                @click="store.cancelSearch()"
              >
                <UIcon
                  :name="store.isCancelling ? 'i-lucide-loader-circle' : 'i-lucide-circle-stop'"
                  :class="['h-3.5 w-3.5', store.isCancelling && 'animate-spin']"
                />
                {{ store.isCancelling ? 'Annulation…' : 'Annuler' }}
              </button>
              <span class="font-medium text-[var(--app-ink-soft)]"
                >{{ Math.round(store.liveProgress.percentage) }}%</span
              >
            </div>
          </div>
          <div class="h-3 w-full overflow-hidden rounded-full border border-[var(--app-line)] bg-[var(--app-bg)]">
            <div
              class="h-full rounded-full bg-[var(--app-ink)] transition-all duration-300"
              :style="{ width: Math.min(store.liveProgress.percentage, 100) + '%' }"
            />
          </div>
        </div>
        <div
          v-if="store.liveProgress.current_prospect"
          class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-3"
        >
          <p class="text-sm text-[var(--app-ink)]">
            <span class="font-medium">En cours :</span> {{ store.liveProgress.current_prospect }}
          </p>
        </div>
        <ScrapingJobLivePanel
          :logs="store.streamLogs"
          :prospects="store.streamProspects"
          :is-running="store.currentJob.status === 'running'"
        />
      </div>

      <div
        v-else-if="store.currentJob.status === 'completed' || store.currentJob.status === 'cancelled'"
        class="space-y-4"
      >
        <p v-if="store.currentJob.status === 'cancelled'" class="text-sm text-[var(--app-ink-soft)]">
          Recherche annulée — les {{ store.currentJob.results.length }} prospect(s) déjà trouvé(s) ont été conservés.
        </p>
        <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div
            v-for="stat in completedStats"
            :key="stat.label"
            class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-4"
          >
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 items-center justify-center rounded-lg" :class="stat.iconBg">
                <UIcon :name="stat.icon" class="h-5 w-5" :class="stat.iconColor" />
              </div>
              <div>
                <p class="text-2xl font-bold text-[var(--app-ink)] tabular-nums">{{ stat.value }}</p>
                <p class="text-sm text-[var(--app-ink-soft)]">{{ stat.label }}</p>
              </div>
            </div>
          </div>
        </div>
        <ScrapingJobLivePanel
          v-if="store.streamLogs.length > 0"
          :logs="store.streamLogs"
          :prospects="store.streamProspects"
          :is-running="false"
        />
        <div class="flex items-center gap-3 pt-2">
          <NuxtLink to="/dashboard/my-prospects" class="app-btn-primary">Voir mes prospects</NuxtLink>
          <button class="app-btn-secondary" @click="openSearchDrawer">Nouvelle recherche</button>
        </div>
      </div>

      <div
        v-else-if="store.currentJob.status === 'failed'"
        class="rounded-lg border border-[var(--app-red)] bg-[var(--app-surface)] p-4 text-[var(--app-red)]"
      >
        <p class="font-semibold">La recherche a échoué</p>
        <p class="mt-1 text-sm text-[var(--app-ink-soft)]">{{ store.currentJob.error }}</p>
        <button class="app-btn-secondary mt-4" @click="openSearchDrawer">Réessayer</button>
      </div>
    </div>

    <div v-if="store.recentJobs.length > 0" class="app-card p-5 md:p-6">
      <h2 class="mb-4 text-sm font-semibold text-[var(--app-ink)]">Recherches récentes</h2>
      <div class="divide-y divide-[var(--app-line-soft)]">
        <button
          v-for="job in store.recentJobs"
          :key="job.id"
          type="button"
          class="group flex w-full cursor-pointer items-center justify-between gap-3 py-3 text-left transition-colors first:pt-0 last:pb-0"
          @click="store.loadJob(job.id)"
        >
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <p class="truncate text-sm font-medium text-[var(--app-ink)] capitalize">
                {{ job.category }} · {{ job.city }}
              </p>
              <span :class="['app-badge', jobStatusVariant(job.status)]">{{ formatStatus(job.status) }}</span>
            </div>
            <p class="mt-0.5 text-xs text-[var(--app-ink-soft)]">
              {{ new Date(job.created_at).toLocaleString('fr-FR') }}
              <span v-if="job.status === 'completed' || job.status === 'cancelled'">
                · {{ job.results.length }} prospects ajoutés
              </span>
            </p>
          </div>
          <UIcon name="i-lucide-chevron-right" class="h-4 w-4 shrink-0 text-[var(--app-ink-soft)]" />
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { CompletedStat } from '~/types/SearchProspectsPage'
import type { ComputedRef } from 'vue'
import { computed, onMounted } from 'vue'
import { useProspectSearchStore } from '~/stores/prospectSearch'
import { useDrawerStackStore } from '~/stores/drawerStack'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const store = useProspectSearchStore()
const drawerStack = useDrawerStackStore()

/** Stat tiles for a completed job. */
const completedStats: ComputedRef<CompletedStat[]> = computed((): CompletedStat[] => {
  const job = store.currentJob
  if (job === null) return []
  return [
    {
      label: 'Prospects ajoutés',
      value: job.results.length,
      icon: 'i-lucide-user-check',
      iconBg: 'bg-[var(--app-green-soft)]',
      iconColor: 'text-[var(--app-green)]',
    },
    {
      label: 'Prospects trouvés',
      value: job.progress.total,
      icon: 'i-lucide-search',
      iconBg: 'bg-[var(--app-blue-soft)]',
      iconColor: 'text-[var(--app-blue)]',
    },
    {
      label: 'Doublons ignorés',
      value: job.skipped_duplicates,
      icon: 'i-lucide-copy-x',
      iconBg: 'bg-[var(--app-surface-2)]',
      iconColor: 'text-[var(--app-ink-soft)]',
    },
  ]
})

/** Open the search form drawer. */
function openSearchDrawer(): void {
  drawerStack.push({ kind: 'search-prospects' })
}

/**
 * Badge variant class for a job status.
 * @param status - The status.
 * @returns The ``app-badge--*`` modifier.
 */
function jobStatusVariant(status: string): string {
  if (status === 'completed') return 'app-badge--success'
  if (status === 'failed') return 'app-badge--danger'
  if (status === 'running') return 'app-badge--info'
  return ''
}

/**
 * Human label for a job status.
 * @param status - The status.
 * @returns The French label.
 */
function formatStatus(status: string): string {
  const map: Record<string, string> = {
    pending: 'En attente',
    running: 'En cours',
    completed: 'Terminée',
    cancelled: 'Annulée',
    failed: 'Échec',
  }
  return map[status] ?? status
}

onMounted(async (): Promise<void> => {
  await store.loadRecent()
  // Open the form drawer straight away when there's nothing to show.
  if (store.currentJob === null) openSearchDrawer()
})
</script>
