<template>
  <!-- Étroit : une seule ligne qui défile au doigt jusqu'aux bords de l'écran (les marges négatives rendent le rembourrage du `main`), comme les filtres d'une app native ; large : les puces passent à la ligne. -->
  <div
    ref="chipRowElement"
    role="group"
    :aria-label="props.label"
    class="no-scrollbar flex flex-wrap gap-2 @max-3xl:-mx-4 @max-3xl:touch-pan-x @max-3xl:flex-nowrap @max-3xl:overflow-x-auto @max-3xl:overflow-y-hidden @max-3xl:overscroll-x-contain @max-3xl:px-4 md:@max-3xl:-mx-6 md:@max-3xl:px-6"
  >
    <button
      v-for="option in props.options"
      :key="option.value"
      type="button"
      :aria-pressed="option.value === modelValue"
      :class="[
        'h-9 shrink-0 cursor-pointer rounded-full border px-4 text-sm whitespace-nowrap transition-colors @3xl:h-auto @3xl:px-3 @3xl:py-1 @3xl:text-xs',
        option.value === modelValue
          ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-surface)]'
          : 'border-[var(--app-line)] text-[var(--app-ink)] hover:bg-[var(--app-surface-2)]',
      ]"
      @click="modelValue = option.value"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script lang="ts" setup generic="TValue extends SelectFieldValue">
import type { ModelRef, PropType, Ref } from 'vue'
import type { SelectFieldOption, SelectFieldValue } from '~/types/SelectField'
import type { UiChipFiltersProps } from '~/types/UiChipFilters'
import { nextTick, ref, watch } from 'vue'

const modelValue: ModelRef<TValue> = defineModel<TValue>({ required: true })

/** Pills that filter the list below them: a row swiped sideways on a phone, wrapped lines on wider screens. */
const props: UiChipFiltersProps<TValue> = defineProps({
  options: {
    type: Array as PropType<SelectFieldOption<TValue>[]>,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
})

const chipRowElement: Ref<HTMLElement | null> = ref(null)

/**
 * Slide the row so the selected pill is fully visible, without moving the page.
 * @returns A promise resolved once the row is in place.
 */
async function revealSelectedChip(): Promise<void> {
  await nextTick()
  const chipRow: HTMLElement | null = chipRowElement.value
  const selectedChip: HTMLElement | null = chipRow?.querySelector<HTMLElement>('[aria-pressed="true"]') ?? null
  if (chipRow === null || selectedChip === null) return
  const rowBox: DOMRect = chipRow.getBoundingClientRect()
  const chipBox: DOMRect = selectedChip.getBoundingClientRect()
  const padding: number = parseFloat(getComputedStyle(chipRow).paddingLeft) || 0
  if (chipBox.left < rowBox.left + padding) {
    chipRow.scrollBy({ left: chipBox.left - rowBox.left - padding, behavior: 'smooth' })
  } else if (chipBox.right > rowBox.right - padding) {
    chipRow.scrollBy({ left: chipBox.right - rowBox.right + padding, behavior: 'smooth' })
  }
}

watch(
  (): TValue => modelValue.value,
  (): void => {
    revealSelectedChip()
  },
)
</script>
