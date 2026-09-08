<template>
  <div class="md:overflow-x-auto">
    <table class="dlh-card-table w-full border-collapse" :style="tableStyle">
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

const props: BaseTableProps = defineProps({
  minWidth: {
    type: String,
    default: '720px',
  },
  animateRowMoves: {
    type: Boolean,
    default: false,
  },
})

const tableStyle: ComputedRef<{ minWidth: string } | undefined> = computed((): { minWidth: string } | undefined =>
  props.minWidth ? { minWidth: props.minWidth } : undefined,
)
</script>
