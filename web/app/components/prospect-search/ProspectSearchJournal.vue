<template>
  <p v-if="props.lines.length === 0" class="px-5 py-10 text-center text-sm text-[var(--app-ink-soft)]">
    Le journal se remplit dès que la recherche avance.
  </p>
  <div
    v-else
    ref="scrollContainer"
    class="font-label max-h-[26rem] overflow-y-auto px-4 py-3.5 text-xs leading-relaxed text-[var(--app-ink)] @2xl:px-5"
  >
    <p v-for="(line, index) in props.lines" :key="`${index}-${line.at}`" class="break-words whitespace-pre-wrap">
      <span class="text-[var(--app-ink-soft)] tabular-nums">{{ formatClockTime(line.at) }}</span>
      {{ line.message }}
    </p>
  </div>
</template>

<script lang="ts" setup>
import type { PropType, Ref } from 'vue'
import type { ProspectSearchJournalLine } from '~/types/ProspectSearch'
import type { ProspectSearchJournalProps } from '~/types/ProspectSearchJournal'
import { nextTick, onMounted, ref, watch } from 'vue'
import { formatClockTime } from '~/utils/date'

/** Journal of a search, newest line at the bottom; it follows new lines unless the user scrolled back up. */
const props: ProspectSearchJournalProps = defineProps({
  lines: {
    type: Array as PropType<ProspectSearchJournalLine[]>,
    required: true,
  },
})

const FOLLOW_THRESHOLD_PX: number = 48

const scrollContainer: Ref<HTMLElement | null> = ref(null)

/**
 * Scroll to the newest line once it is rendered.
 * @returns A promise resolved once the journal is scrolled.
 */
async function scrollToNewestLine(): Promise<void> {
  await nextTick()
  const container: HTMLElement | null = scrollContainer.value
  if (container) container.scrollTop = container.scrollHeight
}

watch(
  (): string => `${props.lines.length}:${props.lines[props.lines.length - 1]?.at ?? ''}`,
  (): void => {
    const container: HTMLElement | null = scrollContainer.value
    const isFollowingNewestLine: boolean =
      container === null || container.scrollHeight - container.scrollTop - container.clientHeight < FOLLOW_THRESHOLD_PX
    if (isFollowingNewestLine) scrollToNewestLine()
  },
)

onMounted((): void => {
  scrollToNewestLine()
})
</script>
