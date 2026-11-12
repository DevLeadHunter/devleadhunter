<template>
  <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface-2)] p-3">
    <p class="mb-2 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
      {{ props.title }}
    </p>
    <div class="space-y-1">
      <button
        v-for="preset in presets"
        :key="preset.key"
        type="button"
        class="flex min-h-9 w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 text-left text-sm text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface)]"
        :disabled="props.isBusy"
        @click="emit('schedule', preset.moment)"
      >
        <UIcon name="i-lucide-calendar-clock" class="h-4 w-4 shrink-0 text-[var(--app-ink-soft)]" />
        {{ preset.label }}
      </button>
    </div>
    <div class="mt-2 border-t border-[var(--app-line)] pt-2.5">
      <label class="text-muted mb-1 block text-[11px] font-medium" :for="customInputId">Autre moment</label>
      <div class="flex gap-2">
        <input
          :id="customInputId"
          v-model="customValue"
          type="datetime-local"
          :min="minimumValue"
          class="input-field h-9 min-w-0 flex-1 text-sm"
        />
        <button
          type="button"
          class="btn-secondary shrink-0 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="!customMoment || props.isBusy"
          @click="scheduleCustom"
        >
          Programmer
        </button>
      </div>
      <p v-if="customValue && !customMoment" class="mt-1 text-[11px] text-[var(--app-red)]">
        Choisissez une heure dans le futur.
      </p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type {
  ScheduleSendPreset,
  UiScheduleMomentPickerEmits,
  UiScheduleMomentPickerProps,
} from '~/types/UiScheduleMomentPicker'
import { ScheduleSendPresets } from '~/utils/scheduleSendPresets'
import { parseFutureDatetimeLocalValue, toDatetimeLocalValue } from '~/utils/date'

const props: UiScheduleMomentPickerProps = defineProps({
  title: {
    type: String,
    default: "Programmer l'envoi",
  },
  isBusy: {
    type: Boolean,
    default: false,
  },
  initialMoment: {
    type: Object as PropType<Date | null>,
    default: null,
  },
})

const emit: EmitFn<UiScheduleMomentPickerEmits> = defineEmits<UiScheduleMomentPickerEmits>()

const customInputId: string = useId()

const openedAt: Date = new Date()
const presets: ScheduleSendPreset[] = ScheduleSendPresets.build(openedAt)
const minimumValue: string = toDatetimeLocalValue(openedAt)

const customValue: Ref<string> = ref(
  props.initialMoment && props.initialMoment.getTime() > openedAt.getTime()
    ? toDatetimeLocalValue(props.initialMoment)
    : '',
)

const customMoment: ComputedRef<Date | null> = computed((): Date | null =>
  parseFutureDatetimeLocalValue(customValue.value),
)

/** Pick the free date-time. */
function scheduleCustom(): void {
  if (customMoment.value) {
    emit('schedule', customMoment.value)
  }
}
</script>
