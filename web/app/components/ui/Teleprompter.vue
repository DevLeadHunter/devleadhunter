<template>
  <div :class="wrapperClass" role="region" aria-label="Texte à lire" @click="advance">
    <div :class="innerClass">
      <p v-if="variant === 'card'" class="app-label mb-4 text-center">Lisez à voix haute</p>

      <ol :class="listClass">
        <li
          v-for="(beat, index) in beats"
          :key="`${index}-${beat}`"
          class="flex gap-3 leading-relaxed transition-colors duration-300"
          :class="[beatSizeClass, index === activeIndex ? activeBeatClass : inactiveBeatClass]"
        >
          <span
            class="mt-1.5 w-0.5 shrink-0 rounded-full transition-colors duration-300"
            :class="index === activeIndex ? 'bg-[var(--app-accent)]' : 'bg-transparent'"
            aria-hidden="true"
          />
          <span>{{ beat }}</span>
        </li>
      </ol>

      <p :class="hintClass">
        {{
          isRunning
            ? 'La ligne avance toute seule — cliquez pour passer à la suivante'
            : 'Le repère suivra votre lecture'
        }}
      </p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import type { UiTeleprompterProps, UiTeleprompterVariant } from '~/types/UiTeleprompter'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { estimateBeatSeconds, splitIntoBeats } from '~/composables/useProspectionScript'

/** Beat-by-beat teleprompter for video takes; `overlay` superposes the camera preview. */
const props: UiTeleprompterProps = defineProps({
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
  variant: {
    type: String as PropType<UiTeleprompterVariant>,
    default: 'card',
  },
})

const activeIndex: Ref<number> = ref(0)
const beats: ComputedRef<string[]> = computed((): string[] => splitIntoBeats(props.text))

const wrapperClass: ComputedRef<string> = computed((): string =>
  props.variant === 'overlay'
    ? 'absolute inset-0 flex cursor-pointer flex-col overflow-y-auto bg-gradient-to-b from-black/75 via-black/40 to-black/75 px-6 pt-12 pb-6 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden'
    : 'rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-5 py-6 sm:px-8 sm:py-8',
)

const innerClass: ComputedRef<string> = computed((): string =>
  props.variant === 'overlay' ? 'my-auto flex w-full flex-col items-center gap-4' : '',
)

const listClass: ComputedRef<string> = computed((): string =>
  props.variant === 'overlay' ? 'flex max-w-[60ch] flex-col gap-2.5' : 'mx-auto flex max-w-[32ch] flex-col gap-3',
)

const beatSizeClass: ComputedRef<string> = computed((): string =>
  props.variant === 'overlay' ? 'text-base sm:text-lg' : 'text-xl sm:text-2xl',
)

const activeBeatClass: ComputedRef<string> = computed((): string =>
  props.variant === 'overlay'
    ? 'font-semibold text-white [text-shadow:0_1px_10px_rgba(0,0,0,0.85)]'
    : 'font-medium text-[var(--app-ink)]',
)

const inactiveBeatClass: ComputedRef<string> = computed((): string =>
  props.variant === 'overlay' ? 'text-white/45 [text-shadow:0_1px_10px_rgba(0,0,0,0.85)]' : 'text-[var(--app-faint)]',
)

const hintClass: ComputedRef<string> = computed((): string =>
  props.variant === 'overlay' ? 'text-center text-xs text-white/65' : 'text-muted mt-6 text-center text-xs',
)

let advanceHandle: ReturnType<typeof setTimeout> | null = null

/** Cancel a pending auto-advance timer. */
function clearPendingAdvance(): void {
  if (advanceHandle !== null) {
    clearTimeout(advanceHandle)
    advanceHandle = null
  }
}

/** Queue the move to the next beat based on estimated speaking time. */
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

/** Jump to the next beat immediately. */
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
