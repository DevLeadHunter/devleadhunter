<template>
  <div class="overflow-hidden">
    <BaseTable min-width="1040px">
      <template #head>
        <BaseTableTh class="w-12">
          <input
            type="checkbox"
            class="h-4 w-4 cursor-pointer accent-(--app-accent)"
            :checked="allSelected"
            :indeterminate.prop="someSelected && !allSelected"
            aria-label="Tout sélectionner"
            @change="onToggleAll"
          />
        </BaseTableTh>
        <BaseTableTh>Nom</BaseTableTh>
        <BaseTableTh>Téléphone</BaseTableTh>
        <BaseTableTh>Email</BaseTableTh>
        <BaseTableTh>Critères</BaseTableTh>
        <BaseTableTh>Qualité</BaseTableTh>
        <BaseTableTh>Reçu</BaseTableTh>
        <BaseTableTh align="right" sr-only>Décision</BaseTableTh>
      </template>

      <BaseTableTr
        v-for="candidate in props.candidates"
        :key="candidate.id"
        :class="[
          'cursor-pointer',
          isSelected(candidate) ? 'bg-[var(--app-accent-soft)] hover:bg-[var(--app-accent-soft)]' : '',
        ]"
        @click="onRowClick(candidate, $event)"
      >
        <BaseTableTd>
          <input
            type="checkbox"
            class="h-4 w-4 cursor-pointer accent-(--app-accent)"
            :checked="isSelected(candidate)"
            :aria-label="`Sélectionner ${candidate.name}`"
            @change="emit('toggleSelect', candidate)"
          />
        </BaseTableTd>

        <BaseTableTd>
          <button
            type="button"
            class="cursor-pointer text-left text-sm font-semibold text-[var(--app-ink)] underline decoration-transparent underline-offset-4 transition-colors hover:decoration-[var(--app-accent)]"
            @click="emit('open', candidate)"
          >
            {{ candidate.name }}
          </button>
          <p class="mt-0.5 flex items-center gap-1.5 text-[11px] text-[var(--app-ink-soft)]">
            <UiCountryFlag
              v-if="candidate.country !== 'FR'"
              :code="candidate.country"
              :title="ProspectCountries.option(candidate.country).label"
              size="compact"
            />
            <span>{{ store.buildTradeAndTownLabel(candidate) }}</span>
          </p>
        </BaseTableTd>

        <BaseTableTd label="Téléphone" class="whitespace-nowrap">
          <span v-if="candidate.phone" class="inline-flex items-center gap-1.5">
            <span class="font-label text-xs text-[var(--app-ink-soft)] tabular-nums">{{ candidate.phone }}</span>
            <span v-if="candidate.phone_is_mobile" class="app-badge">portable</span>
          </span>
          <span v-else class="text-sm text-[var(--app-faint)]">—</span>
        </BaseTableTd>

        <BaseTableTd label="Email">
          <span v-if="candidate.email" class="block min-w-0 md:max-w-[240px]">
            <span class="font-label block truncate text-xs text-[var(--app-ink)]" :title="candidate.email">
              {{ candidate.email }}
            </span>
            <span
              v-if="candidate.email_proof_level"
              class="mt-0.5 block text-[11px]"
              :class="
                candidate.email_proof_level === 'c' ? 'text-[var(--app-accent-ink)]' : 'text-[var(--app-ink-soft)]'
              "
            >
              {{ PROSPECT_SEARCH_EMAIL_PROOF_LABELS[candidate.email_proof_level] }}
            </span>
          </span>
          <span v-else class="text-sm text-[var(--app-faint)]">—</span>
        </BaseTableTd>

        <BaseTableTd label="Critères">
          <ProspectSearchLeadCriteria :candidate="candidate" />
        </BaseTableTd>

        <BaseTableTd label="Qualité">
          <span :class="['app-badge whitespace-nowrap', ProspectSearches.leadQuality(candidate).badgeClass]">
            {{ ProspectSearches.leadQuality(candidate).label }}
          </span>
        </BaseTableTd>

        <BaseTableTd label="Reçu" class="font-label text-xs whitespace-nowrap text-[var(--app-ink-soft)]">
          {{ formatRelativeTime(candidate.created_at) }}
        </BaseTableTd>

        <BaseTableTd align="right">
          <span class="flex items-center gap-2 md:justify-end">
            <button
              type="button"
              class="app-btn-secondary h-10 min-h-10 flex-1 px-3 text-xs md:h-9 md:min-h-9 md:w-9 md:flex-none md:px-0"
              :disabled="isSendingDecision(candidate)"
              title="Refuser"
              @click="emit('reject', candidate)"
            >
              <UIcon name="i-lucide-x" class="h-3.5 w-3.5 md:h-4 md:w-4" />
              <span class="md:sr-only">Refuser</span>
            </button>
            <button
              type="button"
              class="app-btn-primary h-10 min-h-10 flex-1 px-3 text-xs md:h-9 md:min-h-9 md:w-9 md:flex-none md:px-0"
              :disabled="isSendingDecision(candidate)"
              title="Accepter"
              @click="emit('accept', candidate)"
            >
              <UIcon
                :name="isSendingDecision(candidate) ? 'i-lucide-loader-circle' : 'i-lucide-check'"
                :class="['h-3.5 w-3.5 md:h-4 md:w-4', isSendingDecision(candidate) && 'animate-spin']"
              />
              <span class="md:sr-only">Accepter</span>
            </button>
          </span>
        </BaseTableTd>
      </BaseTableTr>
    </BaseTable>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type { ProspectSearchCandidate } from '~/types/ProspectSearch'
import type { ProspectSearchLeadTableEmits, ProspectSearchLeadTableProps } from '~/types/ProspectSearchLeadTable'
import { computed } from 'vue'
import { PROSPECT_SEARCH_EMAIL_PROOF_LABELS } from '~/constants/prospectSearch'
import { useProspectSearchStore } from '~/stores/prospectSearch'
import { formatRelativeTime } from '~/utils/date'
import { ProspectCountries } from '~/utils/prospectCountries'
import { ProspectSearches } from '~/utils/prospectSearches'

/** Leads waiting for a decision, in the layout of the prospects table; a click outside the controls opens the lead. */
const props: ProspectSearchLeadTableProps = defineProps({
  candidates: {
    type: Array as PropType<ProspectSearchCandidate[]>,
    required: true,
  },
  selectedCandidateIds: {
    type: Array as PropType<number[]>,
    default: () => [],
  },
})

const emit: EmitFn<ProspectSearchLeadTableEmits> = defineEmits<ProspectSearchLeadTableEmits>()

const store: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()

const selectedIds: ComputedRef<Set<number>> = computed((): Set<number> => new Set(props.selectedCandidateIds ?? []))

const allSelected: ComputedRef<boolean> = computed(
  (): boolean =>
    props.candidates.length > 0 &&
    props.candidates.every((candidate: ProspectSearchCandidate): boolean => selectedIds.value.has(candidate.id)),
)

const someSelected: ComputedRef<boolean> = computed((): boolean =>
  props.candidates.some((candidate: ProspectSearchCandidate): boolean => selectedIds.value.has(candidate.id)),
)

/**
 * Whether a lead is part of the selection.
 * @param candidate - The lead of the row.
 * @returns True when its checkbox is ticked.
 */
function isSelected(candidate: ProspectSearchCandidate): boolean {
  return selectedIds.value.has(candidate.id)
}

/**
 * Whether a decision on a lead is being sent.
 * @param candidate - The lead of the row.
 * @returns True while its buttons must stay still.
 */
function isSendingDecision(candidate: ProspectSearchCandidate): boolean {
  return store.busyCandidateIds.includes(candidate.id)
}

/**
 * Relay the header checkbox to the page.
 * @param event - The native change event.
 */
function onToggleAll(event: Event): void {
  emit('toggleSelectAll', (event.target as HTMLInputElement).checked)
}

/**
 * Open the lead when a bare part of its row is clicked, leaving the controls to their own handlers.
 * @param candidate - The lead of the clicked row.
 * @param event - The native click event.
 */
function onRowClick(candidate: ProspectSearchCandidate, event: MouseEvent): void {
  const target: HTMLElement | null = event.target instanceof HTMLElement ? event.target : null
  if (target?.closest('button, a, input, label, select, textarea')) return
  emit('open', candidate)
}
</script>
