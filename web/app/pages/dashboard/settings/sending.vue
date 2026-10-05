<template>
  <div class="max-w-3xl space-y-6">
    <UiPageHeader
      eyebrow="Prospection"
      title="Configuration d'envoi"
      description="Choisissez et configurez la méthode d'envoi de vos emails de prospection : votre domaine (via Resend) ou Gmail."
    />

    <EmailSendingConfig />

    <section>
      <div class="app-card p-5">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div class="flex items-start gap-3">
            <span
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
            >
              <UIcon name="i-lucide-sliders-horizontal" class="h-4 w-4 text-[var(--app-ink-soft)]" />
            </span>
            <div>
              <h2 class="text-sm font-semibold text-[var(--app-ink)]">Cadence d'envoi</h2>
              <p class="mt-0.5 text-xs text-[var(--app-ink-soft)]">
                Le rythme global de vos cold emails — il protège votre réputation d'expéditeur.
              </p>
            </div>
          </div>
          <button type="button" class="app-btn-secondary h-8 px-3 text-xs" @click="openSendPolicyDrawer">
            <UIcon name="i-lucide-square-pen" class="h-3.5 w-3.5" />
            Modifier
          </button>
        </div>

        <div
          v-if="isLoadingPolicy"
          class="mt-4 h-7 animate-pulse rounded-full border-t border-[var(--app-line-soft)] bg-[var(--app-surface-2)]"
        ></div>
        <div v-else-if="sendPolicy" class="mt-4 flex flex-wrap gap-2 border-t border-[var(--app-line-soft)] pt-4">
          <span class="app-badge">
            <UIcon name="i-lucide-gauge" class="h-3 w-3" />
            {{ sendPolicy.daily_cap }} emails/jour max
          </span>
          <span class="app-badge">
            <UIcon name="i-lucide-calendar-days" class="h-3 w-3" />
            {{ sendingDaysLabel }}
          </span>
          <span class="app-badge">
            <UIcon name="i-lucide-clock" class="h-3 w-3" />
            {{ formatHour(sendPolicy.window_start_hour) }} – {{ formatHour(sendPolicy.window_end_hour) }}
          </span>
          <span class="app-badge">
            <UIcon name="i-lucide-timer" class="h-3 w-3" />
            1 toutes les {{ sendPolicy.spacing_minutes }} min
          </span>
        </div>
      </div>
    </section>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref, watch } from 'vue'
import type { SendPolicy } from '~/types/Automation'
import { formatSendPolicyDays } from '~/utils/sendPolicy'
import { SendPolicyService } from '~/services/sendPolicyService'
import { useDrawerStackStore } from '~/stores/drawerStack'

definePageMeta({ layout: 'dashboard', middleware: ['auth'] })

const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

const sendPolicy: Ref<SendPolicy | null> = ref(null)
const isLoadingPolicy: Ref<boolean> = ref(true)

/** Selected sending days, as a range ("Lun – Ven") when contiguous, a list otherwise. */
const sendingDaysLabel: ComputedRef<string> = computed((): string =>
  formatSendPolicyDays(sendPolicy.value?.days_of_week ?? []),
)

/**
 * Format an hour of day for the summary chips.
 * @param hour - Hour of day (0-24).
 * @returns Zero-padded label, e.g. "07h".
 */
function formatHour(hour: number): string {
  return `${String(hour).padStart(2, '0')}h`
}

/**
 * Load the current sending policy for the summary chips.
 */
async function loadSendPolicy(): Promise<void> {
  isLoadingPolicy.value = true
  try {
    sendPolicy.value = await SendPolicyService.getSendPolicy()
  } catch {
    sendPolicy.value = null
  } finally {
    isLoadingPolicy.value = false
  }
}

/**
 * Open the cadence drawer on top of the page.
 */
function openSendPolicyDrawer(): void {
  drawerStack.push({ kind: 'send-policy' })
}

// The drawer saves the policy itself: refresh the summary once it closes.
watch(
  (): string | undefined => drawerStack.topEntry?.kind,
  (current: string | undefined, previous: string | undefined): void => {
    if (previous === 'send-policy' && current !== 'send-policy') void loadSendPolicy()
  },
)

onMounted((): void => {
  void loadSendPolicy()
})
</script>
