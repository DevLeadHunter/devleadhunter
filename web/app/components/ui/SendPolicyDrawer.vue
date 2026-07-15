<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[460px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
      >
        <!-- Header -->
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>
          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon name="i-lucide-sliders-horizontal" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>
          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Réglages d'envoi</h2>
            <p class="mt-0.5 text-[11px] text-[var(--app-ink-soft)]">Cadence globale de tes cold emails</p>
          </div>
          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto px-5 py-4">
          <div v-if="isLoading" class="flex items-center justify-center py-16">
            <UIcon name="i-lucide-loader-circle" class="h-7 w-7 animate-spin text-[var(--app-accent)]" />
          </div>

          <form v-else id="send-policy-form" class="space-y-6" @submit.prevent="save">
            <div>
              <label class="app-label mb-1.5 block" for="sp-daily-cap">Emails maximum par jour</label>
              <input
                id="sp-daily-cap"
                v-model.number="form.daily_cap"
                type="number"
                min="1"
                max="500"
                class="app-input w-32"
              />
            </div>

            <div>
              <p class="app-label mb-2">Jours d'envoi</p>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="(label, index) in dayLabels"
                  :key="label"
                  type="button"
                  class="rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors"
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

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="app-label mb-1.5 block" for="sp-win-start">Début de journée</label>
                <select id="sp-win-start" v-model.number="form.window_start_hour" class="app-input">
                  <option v-for="h in 24" :key="h - 1" :value="h - 1">{{ String(h - 1).padStart(2, '0') }}:00</option>
                </select>
              </div>
              <div>
                <label class="app-label mb-1.5 block" for="sp-win-end">Fin de journée</label>
                <select id="sp-win-end" v-model.number="form.window_end_hour" class="app-input">
                  <option v-for="h in 24" :key="h" :value="h">{{ String(h).padStart(2, '0') }}:00</option>
                </select>
              </div>
            </div>

            <div>
              <label class="app-label mb-1.5 block" for="sp-spacing">Délai minimum entre deux envois (min)</label>
              <input
                id="sp-spacing"
                v-model.number="form.spacing_minutes"
                type="number"
                min="1"
                max="1440"
                class="app-input w-32"
              />
            </div>

            <p
              class="flex items-start gap-2 rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-3.5 text-[11px] text-[var(--app-ink-soft)]"
            >
              <UIcon name="i-lucide-info" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>
                Max <strong class="text-[var(--app-ink)]">{{ form.daily_cap }}</strong
                >/jour, {{ selectedDaysLabel }}, de
                <strong class="text-[var(--app-ink)]">{{ String(form.window_start_hour).padStart(2, '0') }}h</strong> à
                <strong class="text-[var(--app-ink)]">{{ String(form.window_end_hour).padStart(2, '0') }}h</strong>, 1
                toutes les {{ form.spacing_minutes }} min.
              </span>
            </p>
          </form>
        </div>

        <!-- Footer -->
        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="app-btn-secondary flex-1" @click="emit('close')">Fermer</button>
          <button
            type="submit"
            form="send-policy-form"
            class="app-btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isSaving || isLoading || !isWindowValid"
          >
            <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
            {{ isSaving ? 'Enregistrement…' : 'Enregistrer' }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type { SendPolicyDrawerProps } from '~/types/SendPolicyDrawer'
import type { SendPolicy } from '~/types/Automation'
import { getSendPolicy, updateSendPolicy } from '~/services/sendPolicyService'
import { useToast } from '~/composables/useToast'

/**
 * Defines the component props.
 */
const props: SendPolicyDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits<{
  /** Close every drawer. */
  close: []
  /** Go back to the previous drawer of the stack. */
  back: []
}>()

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
 * Load the current policy from the API.
 * @returns A promise resolved once loaded.
 */
async function load(): Promise<void> {
  isLoading.value = true
  try {
    form.value = await getSendPolicy()
  } catch {
    // Keep defaults on failure.
  } finally {
    isLoading.value = false
  }
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
    emit('close')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Erreur lors de l'enregistrement")
  } finally {
    isSaving.value = false
  }
}

// Load the policy each time the drawer opens.
watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (open) void load()
  },
  { immediate: true },
)
</script>

<style scoped>
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
