<template>
  <div class="space-y-6">
    <div>
      <label class="app-label mb-1.5 block" for="sp-daily-cap">Emails maximum par jour</label>
      <input id="sp-daily-cap" v-model.number="dailyCap" type="number" min="1" max="500" class="app-input w-32" />
    </div>

    <div>
      <p class="app-label mb-2">Jours d'envoi</p>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="(label, index) in DAY_LABELS"
          :key="label"
          type="button"
          class="cursor-pointer rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors"
          :class="
            modelValue.days_of_week.includes(index)
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
        <select id="sp-win-start" v-model.number="windowStartHour" class="app-input">
          <option v-for="h in 24" :key="h - 1" :value="h - 1">{{ String(h - 1).padStart(2, '0') }}:00</option>
        </select>
      </div>
      <div>
        <label class="app-label mb-1.5 block" for="sp-win-end">Fin de journée</label>
        <select id="sp-win-end" v-model.number="windowEndHour" class="app-input">
          <option v-for="h in 24" :key="h" :value="h">{{ String(h).padStart(2, '0') }}:00</option>
        </select>
      </div>
    </div>

    <div>
      <label class="app-label mb-1.5 block" for="sp-spacing">Délai minimum entre deux envois (min)</label>
      <input id="sp-spacing" v-model.number="spacingMinutes" type="number" min="1" max="1440" class="app-input w-32" />
    </div>

    <p
      class="flex items-start gap-2 rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-3.5 text-[11px] text-[var(--app-ink-soft)]"
    >
      <UIcon name="i-lucide-info" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>
        Max <strong class="text-[var(--app-ink)]">{{ modelValue.daily_cap }}</strong
        >/jour, {{ selectedDaysLabel }}, de
        <strong class="text-[var(--app-ink)]">{{ String(modelValue.window_start_hour).padStart(2, '0') }}h</strong> à
        <strong class="text-[var(--app-ink)]">{{ String(modelValue.window_end_hour).padStart(2, '0') }}h</strong>, 1
        toutes les {{ modelValue.spacing_minutes }} min.
      </span>
    </p>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, WritableComputedRef } from 'vue'
import { computed } from 'vue'
import type { SendPolicy } from '~/types/Automation'
import type { UiSendPolicyFieldsEmits, UiSendPolicyFieldsProps } from '~/types/UiSendPolicyFields'

/** Send-policy form fields shared by the drawer and setup wizard. */
const props: UiSendPolicyFieldsProps = defineProps({
  modelValue: {
    type: Object as PropType<SendPolicy>,
    required: true,
  },
})

const emit: EmitFn<UiSendPolicyFieldsEmits> = defineEmits<UiSendPolicyFieldsEmits>()

/** Weekday labels (index 0 = Monday). */
const DAY_LABELS: string[] = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']

/** Maximum emails sent per day. */
const dailyCap: WritableComputedRef<number> = computed({
  get: (): number => props.modelValue.daily_cap,
  set: (value: number): void => patch({ daily_cap: value }),
})

/** First hour of the daily sending window. */
const windowStartHour: WritableComputedRef<number> = computed({
  get: (): number => props.modelValue.window_start_hour,
  set: (value: number): void => patch({ window_start_hour: value }),
})

/** Last hour of the daily sending window. */
const windowEndHour: WritableComputedRef<number> = computed({
  get: (): number => props.modelValue.window_end_hour,
  set: (value: number): void => patch({ window_end_hour: value }),
})

/** Minimum delay between two sends, in minutes. */
const spacingMinutes: WritableComputedRef<number> = computed({
  get: (): number => props.modelValue.spacing_minutes,
  set: (value: number): void => patch({ spacing_minutes: value }),
})

/** Human list of the selected days. */
const selectedDaysLabel: ComputedRef<string> = computed((): string => {
  const days: number[] = [...props.modelValue.days_of_week].sort((a: number, b: number): number => a - b)
  return days.length ? days.map((day: number): string => DAY_LABELS[day] ?? '').join(', ') : 'aucun jour'
})

/**
 * Emit an updated policy with the given fields replaced.
 * @param changes - Fields to override on the current policy.
 */
function patch(changes: Partial<SendPolicy>): void {
  emit('update:modelValue', { ...props.modelValue, ...changes })
}

/**
 * Toggle a weekday in the policy.
 * @param index - Weekday index (0 = Monday).
 */
function toggleDay(index: number): void {
  const days: Set<number> = new Set<number>(props.modelValue.days_of_week)
  if (days.has(index)) days.delete(index)
  else days.add(index)
  patch({ days_of_week: [...days].sort((a: number, b: number): number => a - b) })
}
</script>
