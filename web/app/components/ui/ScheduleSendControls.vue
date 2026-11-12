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
      <UiScheduleMomentPicker
        v-if="isPanelOpen && props.canSend"
        class="mt-2"
        :is-busy="props.isBusy"
        @schedule="emit('schedule', $event)"
      />
    </Transition>
  </div>
</template>

<script lang="ts" setup>
import type { EmitFn, Ref } from 'vue'
import type { UiScheduleSendControlsEmits, UiScheduleSendControlsProps } from '~/types/UiScheduleSendControls'

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

const isPanelOpen: Ref<boolean> = ref(false)

/** Open or close the schedule panel. */
function togglePanel(): void {
  isPanelOpen.value = !isPanelOpen.value
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
