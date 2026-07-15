<template>
  <div class="space-y-3 px-5 py-4">
    <div class="flex items-center justify-between">
      <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Comportement démo</p>
      <span
        v-if="behavior"
        :class="['inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-medium', temperatureClass]"
      >
        <UIcon name="i-lucide-thermometer" class="h-3 w-3" />
        {{ temperatureLabel }}
      </span>
    </div>

    <div v-if="isLoading" class="flex justify-center py-3">
      <UIcon name="i-lucide-loader-circle" class="h-5 w-5 animate-spin text-[var(--app-faint)]" />
    </div>

    <template v-else-if="behavior">
      <!-- No tracking configured -->
      <p v-if="!behavior.tracking_configured" class="text-xs text-[var(--app-ink-soft)]">
        PostHog n'est pas configuré — le suivi comportemental est inactif.
      </p>

      <!-- No data yet -->
      <p v-else-if="!behavior.has_data" class="text-xs text-[var(--app-ink-soft)]">
        Aucune activité détectée sur la démo pour l'instant.
      </p>

      <template v-else>
        <!-- Score + signals -->
        <div class="flex items-center gap-3">
          <div class="text-2xl font-bold text-[var(--app-ink)]">
            {{ behavior.score }}<span class="text-sm text-[var(--app-ink-soft)]">/100</span>
          </div>
          <div class="grid flex-1 grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] text-[var(--app-ink-soft)]">
            <span>Visites : {{ signalNumber('visits') }}</span>
            <span>Temps : {{ signalNumber('total_seconds') }}s</span>
            <span>Clics tel : {{ signalNumber('phone_clicks') }}</span>
            <span>Clics CTA : {{ signalNumber('cta_clicks') }}</span>
          </div>
        </div>

        <!-- Timeline -->
        <div v-if="behavior.timeline.length" class="space-y-1.5">
          <div
            v-for="(entry, i) in behavior.timeline.slice(0, 12)"
            :key="i"
            class="flex items-center gap-2 text-[11px]"
          >
            <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--app-accent-ink)]"></span>
            <span class="text-[var(--app-ink)]">{{ entry.label }}</span>
            <span class="ml-auto text-[var(--app-ink-soft)]">{{ formatTime(entry.timestamp) }}</span>
          </div>
        </div>
      </template>

      <!-- AI summary -->
      <div v-if="summary" class="rounded border border-[var(--app-line)] bg-[var(--app-surface)] p-3">
        <p class="mb-1 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Analyse IA</p>
        <p class="text-xs whitespace-pre-line text-[var(--app-ink)]">{{ summary }}</p>
      </div>

      <!-- Personalized follow-up draft -->
      <div v-if="followup" class="space-y-2 rounded border border-[var(--app-line)] bg-[var(--app-surface)] p-3">
        <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
          Relance personnalisée
        </p>
        <p class="text-xs text-[var(--app-ink-soft)]">
          <span class="font-medium text-[var(--app-ink)]">Objet :</span> {{ followup.subject }}
        </p>
        <iframe
          :srcdoc="followup.body_html"
          class="h-48 w-full rounded border border-[var(--app-line)] bg-white"
          sandbox=""
        ></iframe>
        <button class="btn-primary w-full text-xs" :disabled="isSending || !prospectEmail" @click="handleSendFollowup">
          <UIcon v-if="isSending" name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
          Envoyer la relance
        </button>
      </div>

      <!-- Actions -->
      <div class="flex gap-2">
        <button class="btn-secondary flex-1 text-xs" :disabled="isSummarizing" @click="handleSummary">
          <UIcon
            :name="isSummarizing ? 'i-lucide-loader-circle' : 'i-lucide-wand-sparkles'"
            :class="['h-3.5 w-3.5', isSummarizing && 'animate-spin']"
          />
          Résumé IA
        </button>
        <button class="btn-secondary flex-1 text-xs" :disabled="isDrafting" @click="handleDraft">
          <UIcon
            :name="isDrafting ? 'i-lucide-loader-circle' : 'i-lucide-send'"
            :class="['h-3.5 w-3.5', isDrafting && 'animate-spin']"
          />
          Relance perso
        </button>
      </div>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import { ref, computed, watch } from 'vue'
import type { BehaviorSummary, PersonalizedFollowup, ProspectBehavior } from '~/services/behaviorService'
import {
  draftPersonalizedFollowup,
  getProspectBehavior,
  sendQuickEmail,
  summarizeProspectBehavior,
} from '~/services/behaviorService'
import type { UiProspectBehaviorProps } from '~/types/UiProspectBehavior'
import { useToast } from '~/composables/useToast'

/**
 * Définit les props du composant UiProspectBehavior.
 */
const props: UiProspectBehaviorProps = defineProps({
  prospectId: {
    type: Number as PropType<number | null>,
    default: null,
  },
  prospectEmail: {
    type: String as PropType<string | null>,
    default: null,
  },
  prospectName: {
    type: String,
    default: '',
  },
  open: {
    type: Boolean,
    required: true,
  },
})

const toast = useToast()

const behavior: Ref<ProspectBehavior | null> = ref<ProspectBehavior | null>(null)
const summary: Ref<string | null> = ref<string | null>(null)
const followup: Ref<PersonalizedFollowup | null> = ref<PersonalizedFollowup | null>(null)
const isLoading: Ref<boolean> = ref(false)
const isSummarizing: Ref<boolean> = ref(false)
const isDrafting: Ref<boolean> = ref(false)
const isSending: Ref<boolean> = ref(false)

const TEMPERATURE_LABELS: Record<string, string> = {
  hot: 'Chaud',
  warm: 'Tiède',
  cold: 'Froid',
  unknown: 'Inconnu',
}

const temperatureLabel: ComputedRef<string> = computed(
  (): string => TEMPERATURE_LABELS[behavior.value?.temperature ?? ''] ?? '—',
)

const temperatureClass: ComputedRef<string> = computed((): string => {
  switch (behavior.value?.temperature) {
    case 'hot':
      return 'border border-[var(--app-red)]/40 bg-[var(--app-red)]/10 text-[var(--app-red)]'
    case 'warm':
      return 'border border-[var(--app-accent)]/40 bg-[var(--app-accent)]/10 text-[var(--app-accent)]'
    case 'cold':
      return 'border border-[var(--app-accent-ink)]/40 bg-[var(--app-accent-ink)]/10 text-[var(--app-accent-ink)]'
    default:
      return 'border border-[var(--app-line)] bg-[var(--app-surface)] text-[var(--app-ink-soft)]'
  }
})

/**
 * Read a numeric signal value safely.
 * @param key - Signal key.
 * @returns The numeric value (0 when absent).
 */
function signalNumber(key: string): number {
  const value = behavior.value?.signals?.[key]
  return typeof value === 'number' ? value : 0
}

/**
 * Format an ISO timestamp to a short French time.
 * @param ts - ISO timestamp or null.
 * @returns Formatted date-time, or empty string.
 */
function formatTime(ts: string | null): string {
  if (!ts) return ''
  return new Date(ts).toLocaleString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

/** Load the prospect behaviour. */
async function load(): Promise<void> {
  if (!props.prospectId) return
  isLoading.value = true
  try {
    behavior.value = await getProspectBehavior(props.prospectId)
  } catch {
    behavior.value = null
  } finally {
    isLoading.value = false
  }
}

/** Generate the AI behaviour summary. */
async function handleSummary(): Promise<void> {
  if (!props.prospectId) return
  isSummarizing.value = true
  try {
    const result: BehaviorSummary = await summarizeProspectBehavior(props.prospectId)
    summary.value = result.summary
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec du résumé')
  } finally {
    isSummarizing.value = false
  }
}

/** Generate a behaviour-personalised follow-up draft. */
async function handleDraft(): Promise<void> {
  if (!props.prospectId) return
  isDrafting.value = true
  try {
    followup.value = await draftPersonalizedFollowup(props.prospectId)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la génération')
  } finally {
    isDrafting.value = false
  }
}

/** Send the drafted personalised follow-up to the prospect. */
async function handleSendFollowup(): Promise<void> {
  if (!props.prospectId || !props.prospectEmail || !followup.value) return
  isSending.value = true
  try {
    const result = await sendQuickEmail({
      recipient_email: props.prospectEmail,
      recipient_name: props.prospectName,
      subject: followup.value.subject,
      body_html: followup.value.body_html,
      prospect_id: String(props.prospectId),
    })
    if (result.success) {
      toast.success('Relance envoyée')
      followup.value = null
    } else {
      toast.error(result.error ?? "Échec de l'envoi")
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'envoi")
  } finally {
    isSending.value = false
  }
}

watch(
  (): [boolean, number | null] => [props.open, props.prospectId],
  ([open, pid]): void => {
    if (open && pid) {
      summary.value = null
      followup.value = null
      void load()
    }
  },
  { immediate: true },
)
</script>
