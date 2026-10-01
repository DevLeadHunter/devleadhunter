<template>
  <dl class="grid">
    <div
      v-for="row in props.rows"
      :key="row.label"
      class="grid gap-0.5 border-b border-dashed border-[#e3dccd] py-3 last:border-b-0 md:grid-cols-[11rem_minmax(0,1fr)] md:gap-4"
    >
      <dt class="font-label pt-0.5 text-[0.68rem] tracking-[0.14em] text-[#6b6355] uppercase">{{ row.label }}</dt>
      <dd class="min-w-0 break-words text-[#1b1813] tabular-nums">
        {{ row.value }}
        <span v-if="row.note" class="block text-sm text-[#6b6355]">{{ row.note }}</span>
      </dd>
    </div>
  </dl>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { LandingLegalDetailsProps, LegalDetailRow } from '~/types/LandingLegalDetails'

const props: LandingLegalDetailsProps = defineProps({
  rows: {
    type: Array as PropType<LegalDetailRow[]>,
    required: true,
  },
})
</script>
