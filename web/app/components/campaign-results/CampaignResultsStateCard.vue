<template>
  <section
    class="app-card @container flex min-w-0 flex-col overflow-hidden"
    aria-labelledby="campaign-results-state-title"
  >
    <div class="flex-1" :class="hasSideFacts ? 'grid @3xl:grid-cols-2' : 'flex flex-col'">
      <div class="min-w-0 pb-3.5">
        <header class="px-[18px] pt-4">
          <h3 id="campaign-results-state-title" class="text-[15px] font-medium text-[var(--app-ink)]">
            {{ props.prospectCount > 1 ? `Où en sont les ${props.prospectCount}` : 'Où en est le prospect' }}
          </h3>
          <p class="mt-0.5 text-[13px] text-[var(--app-ink-soft)]">
            {{
              props.isSending
                ? "Un carré par prospect. Les carrés vides n'ont pas encore reçu de mail."
                : "Un carré par prospect, à l'étape la plus avancée qu'il a atteinte."
            }}
          </p>
        </header>

        <UiUnitChart
          class="px-[18px] pt-[18px]"
          :units="units"
          :label="unitsLabel"
          @select="emit('select-prospect', $event)"
        />

        <ul class="mt-3.5 grid max-w-xl grid-cols-1 gap-x-5 gap-y-0.5 px-[18px] @md:grid-cols-2">
          <li v-for="group in props.groups" :key="group.state">
            <button
              type="button"
              class="group/legend flex w-full cursor-pointer items-center gap-2 py-1.5 text-left text-[13px] text-[var(--app-ink)]/80 transition-colors hover:text-[var(--app-ink)]"
              @click="emit('select-state', group.state)"
            >
              <span
                class="h-[9px] w-[9px] shrink-0 rounded-[2px]"
                :class="UNIT_CHART_TONE_CLASSES[CAMPAIGN_RESULTS_STATE_TONES[group.state]]"
              ></span>
              <span class="decoration-[var(--app-faint)] underline-offset-[3px] group-hover/legend:underline">{{
                CAMPAIGN_RESULTS_STATE_GROUP_LABELS[group.state]
              }}</span>
              <span class="ml-auto font-medium text-[var(--app-ink)] tabular-nums">{{ group.rows.length }}</span>
            </button>
          </li>
        </ul>
      </div>

      <div
        class="flex min-w-0 flex-col border-t border-[var(--app-line-soft)]"
        :class="hasSideFacts ? '@3xl:border-t-0 @3xl:border-l' : 'mt-auto'"
      >
        <dl v-if="props.facts.length > 0">
          <div
            v-for="fact in props.facts"
            :key="fact.label"
            class="flex items-baseline justify-between gap-4 border-b border-[var(--app-line-soft)] px-[18px] py-2.5 text-[13px]"
          >
            <dt class="shrink-0 text-[var(--app-ink-soft)]">{{ fact.label }}</dt>
            <dd class="min-w-0 text-right font-medium text-[var(--app-ink)]">
              {{ fact.value }}
              <span v-if="fact.detail" class="font-normal text-[var(--app-ink-soft)]">· {{ fact.detail }}</span>
            </dd>
          </div>
        </dl>

        <div class="px-[18px] pt-3 pb-4">
          <button
            type="button"
            class="inline-flex cursor-pointer items-center gap-1.5 text-[13.5px] font-medium whitespace-nowrap text-[var(--app-ink)] transition-[gap] hover:gap-2.5"
            @click="openFooterTarget"
          >
            {{ footerActionLabel }}
            <UIcon name="i-lucide-arrow-right" class="h-[15px] w-[15px]" />
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type { CampaignResultsRow, CampaignResultsStateFact, CampaignResultsStateGroup } from '~/types/CampaignResults'
import type { CampaignResultsStateCardEmits, CampaignResultsStateCardProps } from '~/types/CampaignResultsStateCard'
import type { UiUnitChartUnit } from '~/types/UiUnitChart'
import { computed } from 'vue'
import { CAMPAIGN_RESULTS_STATE_GROUP_LABELS, CAMPAIGN_RESULTS_STATE_TONES } from '~/constants/campaignResults'
import { UNIT_CHART_TONE_CLASSES } from '~/constants/unitChartTones'
import { CampaignResults } from '~/utils/campaignResults'

const props: CampaignResultsStateCardProps = defineProps({
  groups: {
    type: Array as PropType<CampaignResultsStateGroup[]>,
    required: true,
  },
  facts: {
    type: Array as PropType<CampaignResultsStateFact[]>,
    required: true,
  },
  prospectCount: {
    type: Number,
    required: true,
  },
  isSending: {
    type: Boolean,
    required: true,
  },
  isAloneOnRow: {
    type: Boolean,
    required: true,
  },
})

const emit: EmitFn<CampaignResultsStateCardEmits> = defineEmits<CampaignResultsStateCardEmits>()

const units: ComputedRef<UiUnitChartUnit[]> = computed((): UiUnitChartUnit[] =>
  props.groups.flatMap((group: CampaignResultsStateGroup): UiUnitChartUnit[] =>
    group.rows.map((row: CampaignResultsRow): UiUnitChartUnit => CampaignResults.unitOf(row)),
  ),
)

const unitsLabel: ComputedRef<string> = computed((): string =>
  props.groups
    .map(
      (group: CampaignResultsStateGroup): string =>
        `${group.rows.length} ${CAMPAIGN_RESULTS_STATE_GROUP_LABELS[group.state].toLocaleLowerCase('fr-FR')}`,
    )
    .join(', '),
)

const hasSideFacts: ComputedRef<boolean> = computed((): boolean => props.isAloneOnRow && props.facts.length > 0)

const footerActionLabel: ComputedRef<string> = computed((): string => {
  if (props.isSending) return "Ouvrir la file d'attente"
  if (props.prospectCount > 1) return `Voir les ${props.prospectCount} prospects`
  return 'Voir le prospect'
})

/** Open the send queue while mails are planned, the prospects table once they all left. */
function openFooterTarget(): void {
  if (props.isSending) {
    emit('open-queue')
    return
  }
  emit('show-prospects')
}
</script>
