<template>
  <div class="w-full">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <slot name="secondary" />
      <div
        :class="[
          'ml-auto inline-flex h-9 items-stretch overflow-hidden rounded-full bg-[var(--app-btn-bg)] text-[var(--app-btn-text)] transition-opacity',
          (!props.canSend || props.isBusy) && 'opacity-50',
        ]"
      >
        <button
          type="button"
          class="flex cursor-pointer items-center gap-1.5 pr-3 pl-4 text-sm font-semibold enabled:hover:bg-[var(--app-btn-text)]/10 disabled:cursor-not-allowed"
          :disabled="!props.canSend || props.isBusy"
          @click="emit('send')"
        >
          <UIcon
            :name="props.isBusy ? 'i-lucide-loader-circle' : 'i-lucide-reply'"
            :class="['h-4 w-4', props.isBusy && 'animate-spin']"
          />
          {{ props.isBusy ? 'Envoi…' : props.sendLabel }}
        </button>
        <span class="my-2 w-px bg-[var(--app-btn-text)] opacity-25" aria-hidden="true"></span>
        <button
          type="button"
          class="flex w-10 cursor-pointer items-center justify-center enabled:hover:bg-[var(--app-btn-text)]/10 disabled:cursor-not-allowed"
          :disabled="!props.canSend || props.isBusy"
          :aria-expanded="isPanelOpen"
          aria-label="Programmer l'envoi"
          title="Programmer l'envoi"
          @click="togglePanel"
        >
          <UIcon :name="isPanelOpen ? 'i-lucide-chevron-up' : 'i-lucide-clock'" class="h-4 w-4" />
        </button>
      </div>
    </div>

    <Transition name="schedule-panel">
      <div
        v-if="isPanelOpen && props.canSend"
        class="mt-2 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface-2)] p-3"
      >
        <p class="mb-2 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
          Programmer l'envoi
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
    </Transition>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, Ref } from 'vue'
import type {
  ScheduleSendPreset,
  UiScheduleSendControlsEmits,
  UiScheduleSendControlsProps,
} from '~/types/UiScheduleSendControls'
import { ScheduleSendPresets } from '~/utils/scheduleSendPresets'
import { parseFutureDatetimeLocalValue, toDatetimeLocalValue } from '~/utils/date'

const props: UiScheduleSendControlsProps = defineProps({
  canSend: {
    type: Boolean,
    required: true,
  },
  isBusy: {
    type: Boolean,
    default: false,
  },
  sendLabel: {
    type: String,
    default: 'Envoyer',
  },
})

const emit: EmitFn<UiScheduleSendControlsEmits> = defineEmits<UiScheduleSendControlsEmits>()

const customInputId: string = useId()

const isPanelOpen: Ref<boolean> = ref(false)
const customValue: Ref<string> = ref('')
const openedAt: Ref<Date> = ref(new Date())

/** Presets computed when the panel opens, so « demain » stays true past midnight. */
const presets: ComputedRef<ScheduleSendPreset[]> = computed((): ScheduleSendPreset[] =>
  ScheduleSendPresets.build(openedAt.value),
)

const minimumValue: ComputedRef<string> = computed((): string => toDatetimeLocalValue(openedAt.value))

const customMoment: ComputedRef<Date | null> = computed((): Date | null =>
  parseFutureDatetimeLocalValue(customValue.value),
)

/** Open or close the panel, refreshing the presets on open. */
function togglePanel(): void {
  if (!isPanelOpen.value) {
    openedAt.value = new Date()
    customValue.value = ''
  }
  isPanelOpen.value = !isPanelOpen.value
}

/** Plan the send at the free date-time. */
function scheduleCustom(): void {
  if (customMoment.value) emit('schedule', customMoment.value)
}

watch(
  (): boolean => props.canSend,
  (canSend: boolean): void => {
    if (!canSend) isPanelOpen.value = false
  },
)
</script>

<style scoped>
.schedule-panel-enter-active,
.schedule-panel-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}

.schedule-panel-enter-from,
.schedule-panel-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (prefers-reduced-motion: reduce) {
  .schedule-panel-enter-active,
  .schedule-panel-leave-active {
    transition: none;
  }
}
</style>
