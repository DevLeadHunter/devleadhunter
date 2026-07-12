<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-semibold text-[var(--app-ink)]">Automatisations</h1>
        <p class="text-muted mt-1 text-sm">Trouver → générer les sites → valider → démarcher, en une passe.</p>
      </div>
      <div class="flex items-center gap-2">
        <NuxtLink to="/dashboard/settings/sending" class="btn-secondary">
          <UIcon name="i-lucide-sliders-horizontal" class="mr-1.5 h-4 w-4" />Réglages d'envoi
        </NuxtLink>
        <NuxtLink to="/dashboard/automations/new" class="btn-primary">
          <UIcon name="i-lucide-plus" class="mr-1.5 h-4 w-4" />Nouvelle automatisation
        </NuxtLink>
      </div>
    </div>

    <!-- Awaiting-review banner -->
    <NuxtLink
      v-if="store.awaitingReviewCount > 0"
      :to="firstAwaitingReviewLink"
      class="card flex items-center gap-2.5 border-[var(--app-blue)] bg-[var(--app-blue-soft)] transition-transform hover:-translate-y-0.5"
    >
      <UIcon name="i-lucide-clipboard-check" class="h-5 w-5 shrink-0 text-[var(--app-blue)]" />
      <p class="text-sm font-medium text-[var(--app-ink)]">
        {{ store.awaitingReviewCount }} automatisation(s) attendent ta validation
      </p>
    </NuxtLink>

    <!-- Loading -->
    <div v-if="store.isLoading && store.automationsCount === 0" class="card animate-pulse space-y-3">
      <div class="h-4 w-1/3 rounded bg-[var(--app-surface-2)]" />
      <div class="h-3 w-1/2 rounded bg-[var(--app-surface-2)]" />
    </div>

    <!-- Content -->
    <div v-else-if="store.automationsCount > 0" class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <NuxtLink
        v-for="auto in store.automations"
        :key="auto.id"
        :to="`/dashboard/automations/${auto.id}`"
        class="group card flex cursor-pointer flex-col gap-3 text-left transition-transform hover:-translate-y-0.5"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="truncate font-semibold text-[var(--app-ink)]">{{ auto.name }}</p>
            <p class="text-muted mt-0.5 text-[11px]">
              {{ auto.mode === 'full_auto' ? 'Full-auto' : 'Semi-auto' }} · {{ formatDate(auto.created_at) }}
            </p>
          </div>
          <span class="app-badge shrink-0" :class="statusBadgeClass(auto.status)">{{ statusLabel(auto.status) }}</span>
        </div>

        <div class="grid grid-cols-4 gap-2">
          <div v-for="kpi in listKpis(auto)" :key="kpi.label" class="rounded-lg bg-[var(--app-surface-2)] px-2 py-1.5">
            <p class="text-[9px] tracking-wide text-[var(--app-faint)] uppercase">{{ kpi.label }}</p>
            <p class="text-sm font-bold text-[var(--app-ink)] tabular-nums">{{ kpi.value }}</p>
          </div>
        </div>

        <p
          v-if="auto.status === 'awaiting_review'"
          class="flex items-center gap-1.5 text-[11px] font-medium text-[var(--app-blue)]"
        >
          <UIcon name="i-lucide-clipboard-check" class="h-3.5 w-3.5" />Des sites attendent ta validation
        </p>
      </NuxtLink>
    </div>

    <!-- Empty -->
    <div v-else class="card px-6 py-12 text-center">
      <UIcon name="i-lucide-workflow" class="mx-auto h-8 w-8 text-[var(--app-faint)]" />
      <p class="mt-3 font-medium text-[var(--app-ink)]">Aucune automatisation pour l'instant</p>
      <p class="text-muted mx-auto mt-1 max-w-md text-sm">
        Choisis des prospects (ou un métier + une ville) et laisse la machine enrichir, générer les sites et démarcher.
      </p>
      <NuxtLink to="/dashboard/automations/new" class="btn-primary mx-auto mt-4 w-fit">
        <UIcon name="i-lucide-plus" class="mr-1.5 h-4 w-4" />Créer une automatisation
      </NuxtLink>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { Automation, AutomationStatus, AutomationStep } from '~/types/Automation'
import { useAutomationsStore } from '~/stores/automations'

/** A compact KPI tile. */
interface Kpi {
  label: string
  value: number
}

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const store = useAutomationsStore()

/** Polling handle for live progress. */
const pollHandle: Ref<ReturnType<typeof setInterval> | null> = ref<ReturnType<typeof setInterval> | null>(null)

/** Link to the first automatisation awaiting review. */
const firstAwaitingReviewLink: ComputedRef<string> = computed((): string => {
  const first: Automation | undefined = store.automations.find(
    (a: Automation): boolean => a.status === 'awaiting_review',
  )
  return first ? `/dashboard/automations/${first.id}` : '/dashboard/automations'
})

/**
 * Count items of an automatisation in any of the given steps.
 * @param auto - The automatisation.
 * @param steps - Steps to sum.
 * @returns The total.
 */
function stepCount(auto: Automation, steps: AutomationStep[]): number {
  return steps.reduce((sum: number, step: AutomationStep): number => sum + (auto.stats.by_step[step] ?? 0), 0)
}

/**
 * KPI tiles for a card.
 * @param auto - The automatisation.
 * @returns Four tiles.
 */
function listKpis(auto: Automation): Kpi[] {
  return [
    { label: 'Total', value: auto.stats.total },
    { label: 'Sites', value: stepCount(auto, ['generated', 'campaigning']) },
    { label: 'Emails', value: auto.stats.emails_sent },
    { label: 'Vendus', value: auto.stats.won },
  ]
}

/**
 * Label for a status.
 * @param status - The status.
 * @returns French label.
 */
function statusLabel(status: AutomationStatus): string {
  const labels: Record<AutomationStatus, string> = {
    draft: 'Brouillon',
    running: 'En cours',
    paused: 'En pause',
    awaiting_review: 'À valider',
    completed: 'Terminée',
    cancelled: 'Annulée',
    failed: 'Échec',
  }
  return labels[status]
}

/**
 * Badge class for a status.
 * @param status - The status.
 * @returns The ``app-badge--*`` modifier.
 */
function statusBadgeClass(status: AutomationStatus): string {
  const classes: Record<AutomationStatus, string> = {
    draft: '',
    running: 'app-badge--progress',
    paused: '',
    awaiting_review: 'app-badge--info',
    completed: 'app-badge--success',
    cancelled: 'app-badge--danger',
    failed: 'app-badge--danger',
  }
  return classes[status]
}

/**
 * Format an ISO date as a short French date.
 * @param iso - ISO date string.
 * @returns The formatted date.
 */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
}

onMounted(async (): Promise<void> => {
  await store.fetchAll()
  pollHandle.value = setInterval((): void => {
    if (store.hasActive) void store.refreshActive()
  }, 5000)
})

onBeforeUnmount((): void => {
  if (pollHandle.value !== null) {
    clearInterval(pollHandle.value)
    pollHandle.value = null
  }
})
</script>
