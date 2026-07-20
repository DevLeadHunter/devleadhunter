<template>
  <div
    class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-5 py-6 sm:px-8 sm:py-8"
    role="region"
    aria-label="Texte à lire"
    @click="advance"
  >
    <p class="app-label mb-4 text-center">Lisez à voix haute</p>

    <!-- Colonne étroite : une ligne courte se lit d'un coup d'œil, là où un
         paragraphe large fait balayer les yeux de gauche à droite. -->
    <ol class="mx-auto flex max-w-[32ch] flex-col gap-3">
      <li
        v-for="(beat, index) in beats"
        :key="`${index}-${beat}`"
        class="flex gap-3 text-xl leading-relaxed transition-colors duration-300 sm:text-2xl"
        :class="index === activeIndex ? 'font-medium text-[var(--app-ink)]' : 'text-[var(--app-faint)]'"
      >
        <span
          class="mt-1.5 w-0.5 shrink-0 rounded-full transition-colors duration-300"
          :class="index === activeIndex ? 'bg-[var(--app-accent)]' : 'bg-transparent'"
          aria-hidden="true"
        />
        <span>{{ beat }}</span>
      </li>
    </ol>

    <p class="text-muted mt-6 text-center text-xs">
      {{
        isRunning ? 'La ligne avance toute seule — cliquez pour passer à la suivante' : 'Le repère suivra votre lecture'
      }}
    </p>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { estimateBeatSeconds, splitIntoBeats } from '~/composables/useProspectionScript'

/**
 * Teleprompter shown while a take is being recorded.
 *
 * Every beat stays on screen and only the highlight moves: nothing scrolls out
 * from under the reader, so falling behind costs a glance instead of a retake.
 * Props are typed via {@link import('~/types/UiTeleprompter').UiTeleprompterProps}.
 */
const props = defineProps({
  text: {
    type: String,
    required: true,
  },
  isRunning: {
    type: Boolean,
    default: false,
  },
  restartToken: {
    type: Number,
    default: 0,
  },
})

const activeIndex: Ref<number> = ref<number>(0)

/** The take split into the short lines the highlight walks through. */
const beats: ComputedRef<string[]> = computed((): string[] => splitIntoBeats(props.text))

/** Handle of the auto-advance timer, if one is pending. */
let advanceHandle: ReturnType<typeof setTimeout> | null = null

/** Cancel any pending auto-advance. */
function clearPendingAdvance(): void {
  if (advanceHandle !== null) {
    clearTimeout(advanceHandle)
    advanceHandle = null
  }
}

/** Queue the move to the next beat, timed on how long the current one takes to say. */
function scheduleNextBeat(): void {
  clearPendingAdvance()
  if (!props.isRunning) return
  const beat: string | undefined = beats.value[activeIndex.value]
  if (beat === undefined || activeIndex.value >= beats.value.length - 1) return
  advanceHandle = setTimeout(
    (): void => {
      activeIndex.value += 1
      scheduleNextBeat()
    },
    estimateBeatSeconds(beat) * 1000,
  )
}

/** Jump to the next beat right away (the reader is ahead of the timer). */
function advance(): void {
  if (!props.isRunning) return
  if (activeIndex.value < beats.value.length - 1) activeIndex.value += 1
  scheduleNextBeat()
}

watch(
  (): boolean => props.isRunning,
  (running: boolean): void => {
    activeIndex.value = 0
    if (running) scheduleNextBeat()
    else clearPendingAdvance()
  },
)

watch(
  (): number => props.restartToken,
  (): void => {
    activeIndex.value = 0
    if (props.isRunning) scheduleNextBeat()
  },
)

onBeforeUnmount((): void => {
  clearPendingAdvance()
})
</script>
