<template>
  <Teleport defer :to="`#${TOAST_STACK_EXTENSION_ID}`">
    <TransitionGroup name="lead-notification">
      <div
        v-for="candidate in visibleNotifications"
        :key="candidate.id"
        role="status"
        class="pointer-events-auto flex w-[min(40rem,calc(100vw-2rem))] flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-3.5 py-2.5 shadow-lg shadow-black/5"
        @mouseenter="keepNotificationWhileHovered(candidate.id)"
        @mouseleave="restartDismissalAfterHover(candidate.id)"
      >
        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--app-accent-soft)]">
          <UIcon name="i-lucide-user-round-plus" class="h-4 w-4 text-[var(--app-accent-ink)]" />
        </span>
        <div class="min-w-0 flex-1 basis-40">
          <p class="truncate text-sm font-semibold text-[var(--app-ink)]">{{ candidate.name }}</p>
          <p class="truncate text-[11px] text-[var(--app-ink-soft)]">
            Lead à valider · {{ store.buildTradeAndTownLabel(candidate) }}
          </p>
        </div>
        <ProspectSearchLeadCriteria :candidate="candidate" />
        <div class="ml-auto flex shrink-0 items-center gap-1.5">
          <button
            type="button"
            class="app-btn-secondary h-8 min-h-8 px-3 text-xs pointer-coarse:min-h-11 pointer-coarse:text-sm"
            :disabled="store.busyCandidateIds.includes(candidate.id)"
            @click="decisions.rejectLead(candidate)"
          >
            Refuser
          </button>
          <button
            type="button"
            class="app-btn-primary h-8 min-h-8 px-3 text-xs pointer-coarse:min-h-11 pointer-coarse:text-sm"
            :disabled="store.busyCandidateIds.includes(candidate.id)"
            @click="decisions.acceptLead(candidate)"
          >
            <UIcon
              :name="store.busyCandidateIds.includes(candidate.id) ? 'i-lucide-loader-circle' : 'i-lucide-check'"
              :class="['h-3.5 w-3.5', store.busyCandidateIds.includes(candidate.id) && 'animate-spin']"
            />
            Accepter
          </button>
          <button
            type="button"
            class="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Ouvrir la fiche du lead"
            :aria-label="`Ouvrir la fiche de ${candidate.name}`"
            @click="openLead(candidate)"
          >
            <UIcon name="i-lucide-panel-right-open" class="h-4 w-4" />
          </button>
        </div>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import type { UseProspectSearchDecisionsReturn } from '~/types/Composables'
import type { ProspectSearchCandidate } from '~/types/ProspectSearch'
import { computed, onBeforeUnmount, watch } from 'vue'
import { useProspectSearchDecisions } from '~/composables/useProspectSearchDecisions'
import { TOAST_STACK_EXTENSION_ID } from '~/constants/toastStack'
import { useProspectSearchStore } from '~/stores/prospectSearch'

const store: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()
const decisions: UseProspectSearchDecisionsReturn = useProspectSearchDecisions()

const MAXIMUM_VISIBLE_NOTIFICATIONS: number = 3

const NOTIFICATION_LIFETIME_MS: number = 10_000

const dismissalTimers: Map<number, ReturnType<typeof setTimeout>> = new Map()
const hoveredCandidateIds: Set<number> = new Set()

const visibleNotifications: ComputedRef<ProspectSearchCandidate[]> = computed((): ProspectSearchCandidate[] =>
  store.leadNotifications.slice(0, MAXIMUM_VISIBLE_NOTIFICATIONS),
)

/**
 * Drop the countdown of a notification.
 * @param candidateId - The lead the notification announces.
 */
function cancelDismissal(candidateId: number): void {
  clearTimeout(dismissalTimers.get(candidateId))
  dismissalTimers.delete(candidateId)
}

/**
 * Let a notification leave the screen by itself after its lifetime.
 * @param candidateId - The lead the notification announces.
 */
function planDismissal(candidateId: number): void {
  cancelDismissal(candidateId)
  const timer: ReturnType<typeof setTimeout> = setTimeout((): void => {
    dismissalTimers.delete(candidateId)
    store.dismissLeadNotification(candidateId)
  }, NOTIFICATION_LIFETIME_MS)
  dismissalTimers.set(candidateId, timer)
}

/**
 * Keep a notification on screen while the pointer is over it.
 * @param candidateId - The lead the notification announces.
 */
function keepNotificationWhileHovered(candidateId: number): void {
  hoveredCandidateIds.add(candidateId)
  cancelDismissal(candidateId)
}

/**
 * Start the countdown again once the pointer left the notification.
 * @param candidateId - The lead the notification announces.
 */
function restartDismissalAfterHover(candidateId: number): void {
  hoveredCandidateIds.delete(candidateId)
  planDismissal(candidateId)
}

/**
 * Open the record of the announced lead and take its notification away.
 * @param candidate - The lead to show.
 */
function openLead(candidate: ProspectSearchCandidate): void {
  store.dismissLeadNotification(candidate.id)
  decisions.openLead(candidate)
}

watch(
  visibleNotifications,
  (notifications: ProspectSearchCandidate[]): void => {
    const visibleIds: number[] = notifications.map((candidate: ProspectSearchCandidate): number => candidate.id)
    for (const candidateId of [...dismissalTimers.keys()]) {
      if (!visibleIds.includes(candidateId)) cancelDismissal(candidateId)
    }
    for (const candidateId of [...hoveredCandidateIds]) {
      if (!visibleIds.includes(candidateId)) hoveredCandidateIds.delete(candidateId)
    }
    for (const candidateId of visibleIds) {
      const isWaitingForCountdown: boolean = !dismissalTimers.has(candidateId) && !hoveredCandidateIds.has(candidateId)
      if (isWaitingForCountdown) planDismissal(candidateId)
    }
  },
  { immediate: true },
)

onBeforeUnmount((): void => {
  for (const timer of dismissalTimers.values()) clearTimeout(timer)
  dismissalTimers.clear()
})
</script>

<style scoped>
.lead-notification-enter-active,
.lead-notification-leave-active {
  transition:
    transform 0.22s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.22s ease;
}
.lead-notification-enter-from {
  transform: translateY(8px);
  opacity: 0;
}
.lead-notification-leave-to {
  transform: translateX(12px);
  opacity: 0;
}
.lead-notification-move {
  transition: transform 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

@media (prefers-reduced-motion: reduce) {
  .lead-notification-enter-active,
  .lead-notification-leave-active,
  .lead-notification-move {
    transition: none;
  }
}
</style>
