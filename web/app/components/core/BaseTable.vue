<template>
  <!-- Positioned, so a screen-reader-only header (absolute) stays inside the scroll box instead of widening the page. -->
  <div class="relative md:overflow-x-auto">
    <table
      class="dlh-card-table w-full border-collapse"
      :class="props.isStackedOnTouchTablet && 'dlh-card-table--touch'"
      :style="tableStyle"
    >
      <thead v-if="$slots.head">
        <tr class="bg-[var(--app-surface-2)]">
          <slot name="head" />
        </tr>
      </thead>
      <TransitionGroup
        v-if="props.animateRowMoves"
        tag="tbody"
        move-class="transition-transform duration-200 ease-out motion-reduce:transition-none"
      >
        <slot />
      </TransitionGroup>
      <tbody v-else>
        <slot />
      </tbody>
    </table>
  </div>
</template>

<script lang="ts" setup>
import type { BaseTableProps } from '~/types/BaseTable'
import type { ComputedRef } from 'vue'
import { computed } from 'vue'

/**
 * Table whose rows become stacked cards on a phone — and on an iPad held upright with `isStackedOnTouchTablet`,
 * for the tables too wide for it.
 */
const props: BaseTableProps = defineProps({
  minWidth: {
    type: String,
    default: '720px',
  },
  animateRowMoves: {
    type: Boolean,
    default: false,
  },
  isStackedOnTouchTablet: {
    type: Boolean,
    default: false,
  },
})

const tableStyle: ComputedRef<{ minWidth: string } | undefined> = computed((): { minWidth: string } | undefined =>
  props.minWidth ? { minWidth: props.minWidth } : undefined,
)
</script>
