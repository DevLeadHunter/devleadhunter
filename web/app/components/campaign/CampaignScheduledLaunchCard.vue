<template>
  <div v-if="scheduledMoment || props.isPickerOpen" class="space-y-2">
    <div
      v-if="scheduledMoment"
      :class="[
        'flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border px-3 py-2.5',
        hasMissedLaunch
          ? 'border-[var(--app-red)]/30 bg-[var(--app-red-soft)]'
          : 'border-[var(--app-line)] bg-[var(--app-surface)]',
      ]"
    >
      <UIcon
        :name="hasMissedLaunch ? 'i-lucide-triangle-alert' : 'i-lucide-calendar-clock'"
        :class="['h-4 w-4 shrink-0', hasMissedLaunch ? 'text-[var(--app-red)]' : 'text-[var(--app-ink-soft)]']"
      />
      <div class="min-w-0 flex-1 basis-56">
        <template v-if="hasMissedLaunch">
          <p class="text-sm font-medium text-[var(--app-ink)]">
            Le lancement programmé {{ scheduledLabel }} n'est pas parti
          </p>
          <p class="mt-0.5 text-xs [overflow-wrap:anywhere] text-[var(--app-ink-soft)]">
            {{ props.scheduledLaunchError }}
          </p>
        </template>
        <template v-else>
          <p class="text-sm font-medium text-[var(--app-ink)]">Lancement programmé {{ scheduledLabel }}</p>
          <p class="text-muted mt-0.5 text-xs">
            La campagne démarre toute seule, puis ses envois se posent sur les prochains créneaux de votre cadence.
          </p>
        </template>
      </div>
      <div class="flex shrink-0 items-center gap-1">
        <button
          type="button"
          class="inline-flex min-h-8 cursor-pointer items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium text-[var(--app-ink)] transition-colors enabled:hover:bg-[var(--app-surface-2)] disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="props.isBusy"
          :aria-expanded="props.isPickerOpen"
          @click="togglePicker"
        >
          <UIcon name="i-lucide-pencil" class="h-3.5 w-3.5" />
          {{ hasMissedLaunch ? 'Reprogrammer' : 'Modifier' }}
        </button>
        <button
          type="button"
          :class="[
            'inline-flex min-h-8 cursor-pointer items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium transition-colors enabled:hover:bg-[var(--app-surface-2)] disabled:cursor-not-allowed disabled:opacity-50',
            isConfirmingCancel
              ? 'text-[var(--app-red)]'
              : 'text-[var(--app-ink-soft)] enabled:hover:text-[var(--app-ink)]',
          ]"
          :disabled="props.isBusy"
          @click="cancel"
        >
          <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
          {{ cancelLabel }}
        </button>
      </div>
    </div>

    <UiScheduleMomentPicker
      v-if="props.isPickerOpen"
      class="@xl:ml-auto @xl:max-w-sm"
      :title="scheduledMoment ? 'Modifier le lancement' : 'Programmer le lancement'"
      :is-busy="props.isBusy"
      :initial-moment="scheduledMoment"
      @schedule="emit('schedule', $event)"
    />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type {
  CampaignScheduledLaunchCardEmits,
  CampaignScheduledLaunchCardProps,
} from '~/types/CampaignScheduledLaunchCard'
import { formatScheduledMoment, parseApiDate } from '~/utils/date'

const props: CampaignScheduledLaunchCardProps = defineProps({
  scheduledLaunchAt: {
    type: String as PropType<string | null>,
    default: null,
  },
  scheduledLaunchError: {
    type: String as PropType<string | null>,
    default: null,
  },
  isPickerOpen: {
    type: Boolean,
    default: false,
  },
  isBusy: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<CampaignScheduledLaunchCardEmits> = defineEmits<CampaignScheduledLaunchCardEmits>()

const isConfirmingCancel: Ref<boolean> = ref(false)

const scheduledMoment: ComputedRef<Date | null> = computed((): Date | null =>
  props.scheduledLaunchAt ? parseApiDate(props.scheduledLaunchAt) : null,
)

const scheduledLabel: ComputedRef<string> = computed((): string =>
  scheduledMoment.value ? formatScheduledMoment(scheduledMoment.value) : '',
)

const hasMissedLaunch: ComputedRef<boolean> = computed((): boolean => Boolean(props.scheduledLaunchError))

const cancelLabel: ComputedRef<string> = computed((): string => {
  if (hasMissedLaunch.value) {
    return 'Fermer'
  }

  return isConfirmingCancel.value ? "Confirmer l'annulation" : 'Annuler'
})

/** Open or close the panel that picks the launch time. */
function togglePicker(): void {
  isConfirmingCancel.value = false
  emit('update:isPickerOpen', !props.isPickerOpen)
}

/** Cancel the scheduled launch after a second click; a missed launch is dismissed at once. */
function cancel(): void {
  if (!hasMissedLaunch.value && !isConfirmingCancel.value) {
    isConfirmingCancel.value = true
    return
  }

  isConfirmingCancel.value = false
  emit('cancel')
}

watch(
  (): string | null => props.scheduledLaunchAt,
  (): void => {
    isConfirmingCancel.value = false
  },
)
</script>
