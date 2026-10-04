<template>
  <ul class="space-y-2.5 rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] p-3">
    <li v-for="line in displayedEvidence" :key="line.key" class="text-xs leading-relaxed">
      <p class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span class="app-label">{{ line.factLabel }}</span>
        <span class="min-w-0 font-medium break-all text-[var(--app-ink)]">{{ line.value }}</span>
      </p>
      <p class="mt-0.5 text-[var(--app-ink-soft)]">
        Source :
        <a
          v-if="line.sourceHref"
          :href="line.sourceHref"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1 break-all text-[var(--app-ink)] underline underline-offset-2 transition-opacity hover:opacity-70"
        >
          {{ line.source }}
          <UIcon name="i-lucide-external-link" class="h-3 w-3 shrink-0" />
        </a>
        <span v-else class="text-[var(--app-ink)]">{{ line.source }}</span>
      </p>
      <blockquote
        v-if="line.snippet"
        class="mt-1 border-l-2 border-[var(--app-line)] pl-2.5 break-words text-[var(--app-ink-soft)] italic"
      >
        {{ line.snippet }}
      </blockquote>
    </li>
  </ul>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { ProspectSearchEvidenceLine } from '~/types/ProspectSearch'
import type {
  ProspectSearchDisplayedEvidence,
  ProspectSearchEvidenceListProps,
} from '~/types/ProspectSearchEvidenceList'
import { computed } from 'vue'
import { PROSPECT_SEARCH_EVIDENCE_FACT_LABELS } from '~/constants/prospectSearch'
import { ProspectSearches } from '~/utils/prospectSearches'

/** Proofs of a candidate: what each one establishes, its value, the page it was read on and the words read. */
const props: ProspectSearchEvidenceListProps = defineProps({
  evidence: {
    type: Array as PropType<ProspectSearchEvidenceLine[]>,
    required: true,
  },
})

const displayedEvidence: ComputedRef<ProspectSearchDisplayedEvidence[]> = computed(
  (): ProspectSearchDisplayedEvidence[] =>
    props.evidence.map(
      (line: ProspectSearchEvidenceLine, index: number): ProspectSearchDisplayedEvidence => ({
        key: `${index}-${line.fact}`,
        factLabel: PROSPECT_SEARCH_EVIDENCE_FACT_LABELS[line.fact] ?? line.fact,
        value: line.value,
        source: line.source,
        sourceHref: ProspectSearches.externalHref(line.url),
        snippet: line.snippet ?? null,
      }),
    ),
)
</script>
