<template>
  <ul :class="props.shouldShowLabels ? 'space-y-2' : 'inline-flex shrink-0 items-center gap-1'">
    <li
      v-for="criterion in criteria"
      :key="criterion.key"
      :class="props.shouldShowLabels ? 'flex items-center gap-2.5' : 'flex'"
    >
      <span
        class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
        :class="CRITERION_STATE_CLASSES[criterion.state]"
        :title="props.shouldShowLabels ? undefined : criterion.label"
        :role="props.shouldShowLabels ? undefined : 'img'"
        :aria-label="props.shouldShowLabels ? undefined : criterion.label"
        :aria-hidden="props.shouldShowLabels ? 'true' : undefined"
      >
        <UIcon :name="criterion.icon" class="h-3.5 w-3.5" />
      </span>
      <span
        v-if="props.shouldShowLabels"
        class="min-w-0 text-xs leading-relaxed break-words"
        :class="criterion.state === 'missing' ? 'text-[var(--app-ink-soft)]' : 'text-[var(--app-ink)]'"
      >
        {{ criterion.label }}
      </span>
    </li>
  </ul>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type {
  ProspectSearchCandidate,
  ProspectSearchLeadCriterion,
  ProspectSearchLeadCriterionState,
} from '~/types/ProspectSearch'
import type { ProspectSearchLeadCriteriaProps } from '~/types/ProspectSearchLeadCriteria'
import { computed } from 'vue'
import { ProspectSearches } from '~/utils/prospectSearches'

/** Email, mobile, no website and Google rating of a lead: green when verified, amber to check, grey when absent. */
const props: ProspectSearchLeadCriteriaProps = defineProps({
  candidate: {
    type: Object as PropType<ProspectSearchCandidate>,
    required: true,
  },
  shouldShowLabels: {
    type: Boolean,
    default: false,
  },
})

const CRITERION_STATE_CLASSES: Record<ProspectSearchLeadCriterionState, string> = {
  verified: 'bg-[var(--app-green-soft)] text-[var(--app-green)]',
  toCheck: 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]',
  missing: 'bg-[var(--app-surface-2)] text-[var(--app-faint)]',
}

const criteria: ComputedRef<ProspectSearchLeadCriterion[]> = computed((): ProspectSearchLeadCriterion[] =>
  ProspectSearches.leadCriteria(props.candidate),
)
</script>
