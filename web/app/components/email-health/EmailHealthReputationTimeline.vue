<template>
  <div>
    <div class="flex flex-wrap gap-1">
      <span
        v-for="day in days"
        :key="day.date"
        class="h-4 w-4 rounded-[3px]"
        :style="{ backgroundColor: reputationColor(day.reputation) }"
        :title="`${formatDay(day.date)} — ${reputationLabel(day.reputation)}`"
      ></span>
    </div>
    <div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-[var(--app-ink-soft)]">
      <span v-for="entry in LEGEND" :key="entry.label" class="flex items-center gap-1">
        <span class="h-2.5 w-2.5 rounded-[2px]" :style="{ backgroundColor: entry.color }"></span>
        {{ entry.label }}
      </span>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { ReputationTimelineDay } from '~/types/EmailHealthReputationTimeline'

/**
 * Gmail Postmaster domain-reputation history: one colored square per day
 * (GitHub-contributions style), with a hover title and a legend.
 */
defineProps({
  days: {
    type: Array as PropType<ReputationTimelineDay[]>,
    required: true,
  },
})

/** Legend entries in reputation order. */
const LEGEND: ReadonlyArray<{ label: string; color: string }> = [
  { label: 'Excellente', color: 'var(--app-green)' },
  { label: 'Moyenne', color: 'var(--app-accent)' },
  { label: 'Faible', color: '#c47a3d' },
  { label: 'Mauvaise', color: 'var(--app-red)' },
  { label: 'Pas de donnée', color: 'var(--app-line)' },
]

/**
 * Square color for one Postmaster reputation value.
 * @param reputation - HIGH | MEDIUM | LOW | BAD | null.
 * @returns A CSS color.
 */
function reputationColor(reputation: string | null): string {
  switch ((reputation ?? '').toUpperCase()) {
    case 'HIGH':
      return 'var(--app-green)'
    case 'MEDIUM':
      return 'var(--app-accent)'
    case 'LOW':
      return '#c47a3d'
    case 'BAD':
      return 'var(--app-red)'
    default:
      return 'var(--app-line)'
  }
}

/**
 * French label for one Postmaster reputation value.
 * @param reputation - HIGH | MEDIUM | LOW | BAD | null.
 * @returns The tooltip label.
 */
function reputationLabel(reputation: string | null): string {
  switch ((reputation ?? '').toUpperCase()) {
    case 'HIGH':
      return 'Excellente'
    case 'MEDIUM':
      return 'Moyenne'
    case 'LOW':
      return 'Faible'
    case 'BAD':
      return 'Mauvaise'
    default:
      return 'Pas de donnée'
  }
}

/**
 * Format an ISO date as a full French date.
 * @param iso - ISO date (YYYY-MM-DD).
 * @returns Localized date.
 */
function formatDay(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}
</script>
