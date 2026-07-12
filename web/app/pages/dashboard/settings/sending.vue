<template>
  <div class="mx-auto max-w-xl space-y-5">
    <div>
      <NuxtLink
        to="/dashboard/automations"
        class="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
      >
        <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
        Automatisations
      </NuxtLink>
      <h1 class="app-page-title mt-3">Réglages d'envoi</h1>
      <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
        La cadence globale de tes cold emails — s'applique à toutes tes automatisations et campagnes.
      </p>
    </div>

    <div v-if="isLoading" class="card animate-pulse space-y-3">
      <div class="h-4 w-1/3 rounded bg-[var(--app-surface-2)]" />
      <div class="h-3 w-1/2 rounded bg-[var(--app-surface-2)]" />
    </div>

    <form v-else class="card space-y-5" @submit.prevent="save">
      <!-- Daily cap -->
      <div>
        <label class="text-muted mb-1.5 block text-xs font-medium" for="daily-cap">Emails maximum par jour</label>
        <input
          id="daily-cap"
          v-model.number="form.daily_cap"
          type="number"
          min="1"
          max="500"
          class="input-field w-32"
        />
      </div>

      <!-- Days -->
      <div>
        <p class="text-muted mb-1.5 text-xs font-medium">Jours d'envoi</p>
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="(label, index) in dayLabels"
            :key="label"
            type="button"
            class="rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors"
            :class="
              form.days_of_week.includes(index)
                ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-surface)]'
                : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)]'
            "
            @click="toggleDay(index)"
          >
            {{ label }}
          </button>
        </div>
      </div>

      <!-- Window -->
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium" for="win-start">Début de journée</label>
          <select id="win-start" v-model.number="form.window_start_hour" class="input-field">
            <option v-for="h in 24" :key="h - 1" :value="h - 1">{{ String(h - 1).padStart(2, '0') }}:00</option>
          </select>
        </div>
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium" for="win-end">Fin de journée</label>
          <select id="win-end" v-model.number="form.window_end_hour" class="input-field">
            <option v-for="h in 24" :key="h" :value="h">{{ String(h).padStart(2, '0') }}:00</option>
          </select>
        </div>
      </div>

      <!-- Spacing -->
      <div>
        <label class="text-muted mb-1.5 block text-xs font-medium" for="spacing"
          >Délai minimum entre deux envois (min)</label
        >
        <input
          id="spacing"
          v-model.number="form.spacing_minutes"
          type="number"
          min="1"
          max="1440"
          class="input-field w-32"
        />
      </div>

      <p
        class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2 text-[11px] text-[var(--app-ink-soft)]"
      >
        <UIcon name="i-lucide-info" class="mr-1 inline h-3 w-3" />
        Résumé : max <strong>{{ form.daily_cap }}</strong
        >/jour, {{ selectedDaysLabel }}, de <strong>{{ String(form.window_start_hour).padStart(2, '0') }}h</strong> à
        <strong>{{ String(form.window_end_hour).padStart(2, '0') }}h</strong>, 1 toutes les
        {{ form.spacing_minutes }} min.
      </p>

      <div class="flex justify-end">
        <button type="submit" class="btn-primary disabled:opacity-50" :disabled="isSaving || !isWindowValid">
          <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
          {{ isSaving ? 'Enregistrement…' : 'Enregistrer' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import type { SendPolicy } from '~/types/Automation'
import { getSendPolicy, updateSendPolicy } from '~/services/sendPolicyService'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const toast = useToast()

/** Whether the policy is loading. */
const isLoading: Ref<boolean> = ref<boolean>(true)
/** Whether a save is in flight. */
const isSaving: Ref<boolean> = ref<boolean>(false)

/** The editable policy. */
const form: Ref<SendPolicy> = ref<SendPolicy>({
  daily_cap: 20,
  days_of_week: [0, 1, 2, 3, 4],
  window_start_hour: 7,
  window_end_hour: 18,
  spacing_minutes: 20,
})

/** Weekday labels (index 0 = Monday). */
const dayLabels: ReadonlyArray<string> = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']

/** Whether the end hour is strictly after the start hour. */
const isWindowValid: ComputedRef<boolean> = computed(
  (): boolean => form.value.window_end_hour > form.value.window_start_hour,
)

/** Human list of the selected days. */
const selectedDaysLabel: ComputedRef<string> = computed((): string => {
  const days: number[] = [...form.value.days_of_week].sort((a: number, b: number): number => a - b)
  return days.length ? days.map((d: number): string => dayLabels[d] ?? '').join(', ') : 'aucun jour'
})

/**
 * Toggle a weekday in the policy.
 * @param index - Weekday index (0 = Monday).
 */
function toggleDay(index: number): void {
  const set: Set<number> = new Set<number>(form.value.days_of_week)
  if (set.has(index)) set.delete(index)
  else set.add(index)
  form.value.days_of_week = [...set].sort((a: number, b: number): number => a - b)
}

/**
 * Save the policy.
 * @returns A promise resolved once saved.
 */
async function save(): Promise<void> {
  if (!isWindowValid.value) {
    toast.error('La fin de journée doit être après le début')
    return
  }
  if (form.value.days_of_week.length === 0) {
    toast.error('Choisis au moins un jour')
    return
  }
  isSaving.value = true
  try {
    form.value = await updateSendPolicy(form.value)
    toast.success("Réglages d'envoi enregistrés")
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Erreur lors de l'enregistrement")
  } finally {
    isSaving.value = false
  }
}

onMounted(async (): Promise<void> => {
  try {
    form.value = await getSendPolicy()
  } catch {
    // Keep the defaults on failure.
  } finally {
    isLoading.value = false
  }
})
</script>
