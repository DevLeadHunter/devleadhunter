<template>
  <UiCallout :variant="variant" icon="i-lucide-facebook">
    <template v-if="state === 'needsDesktopApp'">
      {{ waitingCandidatesLabel }}
      {{
        props.waitingPageCount > 1
          ? "L'application DevLeadHunter de votre PC les lira avec son Chrome dès qu'elle sera ouverte : elle démarre avec Windows."
          : "L'application DevLeadHunter de votre PC la lira avec son Chrome dès qu'elle sera ouverte : elle démarre avec Windows."
      }}
    </template>

    <template v-else-if="state === 'readByDesktopApp'">
      {{ waitingCandidatesLabel }}
      {{
        props.waitingPageCount > 1
          ? "Votre PC s'en charge : l'application DevLeadHunter les lit avec son Chrome, en arrière-plan."
          : "Votre PC s'en charge : l'application DevLeadHunter la lit avec son Chrome, en arrière-plan."
      }}
    </template>

    <template v-else-if="state === 'installingChrome'">
      Installation de Chrome sur ce poste (premier lancement, environ 150 Mo). La lecture des pages Facebook démarre
      ensuite.
    </template>

    <template v-else-if="state === 'reading' && props.reading">
      <p>
        <span class="font-medium text-[var(--app-ink)] tabular-nums">
          Lecture des pages Facebook : {{ props.reading.pagesRead }} / {{ props.reading.pagesToRead }}
        </span>
        <span v-if="props.reading.currentBusinessName"> · {{ props.reading.currentBusinessName }}</span>
        <span> (environ une minute par page)</span>
      </p>
      <div class="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[var(--app-surface-2)]">
        <div
          class="h-full rounded-full bg-[var(--app-ink)] transition-[width] duration-300"
          :style="{ width: `${readPercentage}%` }"
        ></div>
      </div>
    </template>

    <template v-else-if="state === 'failed' && props.reading">
      <p>Lecture des pages Facebook interrompue : {{ props.reading.errorMessage }}</p>
      <button
        v-if="props.isSearchActive"
        type="button"
        class="app-btn-secondary mt-2 h-8 min-h-8 px-3 text-xs pointer-coarse:min-h-11 pointer-coarse:text-sm"
        @click="emit('retry')"
      >
        <UIcon name="i-lucide-rotate-cw" class="h-3.5 w-3.5" />
        Réessayer
      </button>
    </template>

    <template v-else-if="state === 'waitingForResume'">
      {{ waitingCandidatesLabel }} Poursuivez la recherche : l'application lira
      {{ props.waitingPageCount > 1 ? 'ces pages' : 'cette page' }} avec le Chrome de ce poste.
    </template>

    <template v-else>
      <span class="inline-flex items-center gap-1.5">
        <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 shrink-0 animate-spin" />
        Préparation du Chrome de ce poste pour lire les pages Facebook…
      </span>
    </template>
  </UiCallout>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type { ProspectSearchFacebookReading } from '~/types/ProspectSearch'
import type {
  ProspectSearchFacebookBannerEmits,
  ProspectSearchFacebookBannerProps,
  ProspectSearchFacebookBannerState,
} from '~/types/ProspectSearchFacebookBanner'
import type { UiCalloutVariant } from '~/types/UiCallout'
import { computed } from 'vue'

/** Tells who reads the Facebook pages a search waits for: the desktop app, and how far it is. */
const props: ProspectSearchFacebookBannerProps = defineProps({
  waitingPageCount: {
    type: Number,
    required: true,
  },
  canReadLocally: {
    type: Boolean,
    required: true,
  },
  isDesktopAppOnline: {
    type: Boolean,
    required: true,
  },
  isSearchActive: {
    type: Boolean,
    required: true,
  },
  reading: {
    type: Object as PropType<ProspectSearchFacebookReading | null>,
    default: null,
  },
})

const emit: EmitFn<ProspectSearchFacebookBannerEmits> = defineEmits<ProspectSearchFacebookBannerEmits>()

const state: ComputedRef<ProspectSearchFacebookBannerState> = computed((): ProspectSearchFacebookBannerState => {
  if (!props.canReadLocally) return props.isDesktopAppOnline ? 'readByDesktopApp' : 'needsDesktopApp'
  if (props.reading?.isChromeInstalling) return 'installingChrome'
  if (props.reading?.isRunning) return props.reading.pagesToRead > 0 ? 'reading' : 'preparing'
  if (props.reading?.errorMessage) return 'failed'
  return props.isSearchActive ? 'preparing' : 'waitingForResume'
})

const variant: ComputedRef<UiCalloutVariant> = computed((): UiCalloutVariant => {
  if (state.value === 'failed') return 'danger'
  return state.value === 'needsDesktopApp' || state.value === 'waitingForResume' ? 'warning' : 'info'
})

const waitingCandidatesLabel: ComputedRef<string> = computed((): string =>
  props.waitingPageCount > 1
    ? `${props.waitingPageCount} candidats attendent la lecture de leur page Facebook.`
    : '1 candidat attend la lecture de sa page Facebook.',
)

const readPercentage: ComputedRef<number> = computed((): number =>
  props.reading && props.reading.pagesToRead > 0
    ? Math.min(100, (props.reading.pagesRead / props.reading.pagesToRead) * 100)
    : 0,
)
</script>
