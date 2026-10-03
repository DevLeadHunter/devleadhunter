<template>
  <section class="app-card flex min-w-0 flex-col overflow-hidden" aria-labelledby="campaign-results-sends-title">
    <header class="px-[18px] pt-4">
      <h3 id="campaign-results-sends-title" class="text-[15px] font-medium text-[var(--app-ink)]">{{ title }}</h3>
      <p class="mt-0.5 text-[13px] text-[var(--app-ink-soft)]">Ce que chaque envoi a déclenché.</p>
    </header>

    <div class="mt-3.5 overflow-x-auto">
      <table class="w-full border-separate border-spacing-0 text-[13.5px]">
        <thead>
          <tr>
            <th
              v-for="(heading, headingIndex) in headings"
              :key="heading"
              class="app-label h-[34px] border-y border-[var(--app-line-soft)] bg-[var(--app-surface-2)] px-2 whitespace-nowrap first:pl-[18px] last:pr-[18px] @xl:px-3"
              :class="headingIndex === 0 ? 'text-left' : 'text-right'"
            >
              {{ heading }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="step in props.steps" :key="step.step">
            <td class="border-b border-[var(--app-line-soft)] py-3 pr-2 pl-[18px] align-top @xl:pr-3">
              <b class="block text-sm leading-tight font-medium text-[var(--app-ink)]">{{ step.label }}</b>
              <span class="text-xs text-[var(--app-ink-soft)]">{{ step.timingLabel }}</span>
            </td>
            <template v-if="step.sent > 0 || step.planned === 0">
              <td class="border-b border-[var(--app-line-soft)] px-2 py-3 text-right align-top @xl:px-3">
                <b class="block text-[17px] leading-tight font-medium text-[var(--app-ink)] tabular-nums">{{
                  step.sent
                }}</b>
                <span class="text-xs whitespace-nowrap text-[var(--app-ink-soft)]">{{ sentDetailOf(step) }}</span>
              </td>
              <td
                v-if="props.isVisitTrackingAvailable"
                class="border-b border-[var(--app-line-soft)] px-2 py-3 text-right align-top @xl:px-3"
              >
                <b class="block text-[17px] leading-tight font-medium text-[var(--app-ink)] tabular-nums">{{
                  step.visitors
                }}</b>
                <span class="text-xs text-[var(--app-ink-soft)] tabular-nums">
                  {{ CampaignResultsFormat.percent(step.visitors, step.sent) }} %
                </span>
              </td>
              <td class="border-b border-[var(--app-line-soft)] py-3 pr-[18px] pl-2 text-right align-top @xl:pl-3">
                <b class="block text-[17px] leading-tight font-medium text-[var(--app-ink)] tabular-nums">{{
                  step.replies.length
                }}</b>
                <span class="inline-flex min-h-4 items-center justify-end gap-[3px]">
                  <span
                    v-for="reply in step.replies"
                    :key="reply.id"
                    class="h-[7px] w-[7px] rounded-full"
                    :class="CAMPAIGN_RESULTS_VERDICT_DOT_CLASSES[reply.verdict]"
                    :title="`${props.prospectNames[reply.prospect_id] ?? 'Prospect'} · ${CAMPAIGN_RESULTS_VERDICT_LABELS[reply.verdict].toLocaleLowerCase('fr-FR')}`"
                  ></span>
                </span>
              </td>
            </template>
            <td
              v-else
              :colspan="props.isVisitTrackingAvailable ? 3 : 2"
              class="border-b border-[var(--app-line-soft)] py-3 pr-[18px] pl-2 align-middle text-[13px] text-[var(--app-ink-soft)] @xl:pl-3"
            >
              {{ CampaignResultsFormat.count(step.planned, 'prévue', 'prévues')
              }}{{ step.firstPlannedAt ? `, la première ${formatScheduledMoment(step.firstPlannedAt)}` : '' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="mt-auto px-[18px] pt-3 pb-4 text-[12.5px] leading-snug text-[var(--app-ink-soft)]">{{ props.note }}</p>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { CampaignChannelWords } from '~/types/CampaignChannelWords'
import type { CampaignResultsStepSummary } from '~/types/CampaignResults'
import type { CampaignResultsSendsCardProps } from '~/types/CampaignResultsSendsCard'
import { computed } from 'vue'
import { CAMPAIGN_RESULTS_VERDICT_DOT_CLASSES, CAMPAIGN_RESULTS_VERDICT_LABELS } from '~/constants/campaignResults'
import { CampaignResultsFormat } from '~/utils/campaignResultsFormat'
import { formatScheduledMoment } from '~/utils/date'

const props: CampaignResultsSendsCardProps = defineProps({
  steps: {
    type: Array as PropType<CampaignResultsStepSummary[]>,
    required: true,
  },
  prospectNames: {
    type: Object as PropType<Record<number, string>>,
    required: true,
  },
  prospectCount: {
    type: Number,
    required: true,
  },
  note: {
    type: String,
    required: true,
  },
  isVisitTrackingAvailable: {
    type: Boolean,
    required: true,
  },
  words: {
    type: Object as PropType<CampaignChannelWords>,
    required: true,
  },
})

const title: ComputedRef<string> = computed((): string => {
  const followUpCount: number = props.steps.length - 1
  const firstMessage: string = `Premier ${props.words.messageNoun}`
  if (followUpCount <= 0) return firstMessage
  return followUpCount === 1 ? `${firstMessage} et relance` : `${firstMessage} et relances`
})

const headings: ComputedRef<string[]> = computed((): string[] =>
  props.isVisitTrackingAvailable ? ['Envoi', 'Envoyés', 'Site ouvert', 'Réponses'] : ['Envoi', 'Envoyés', 'Réponses'],
)

/**
 * Under a step's sent count: how many it reached for the first message, the cancelled ones for a follow-up.
 * @param step - The step summary.
 * @returns The detail, a non-breaking space when there is nothing to add.
 */
function sentDetailOf(step: CampaignResultsStepSummary): string {
  if (step.step === 0) {
    if (step.planned > 0) return `+ ${step.planned} ${step.planned > 1 ? 'prévus' : 'prévu'}`
    return step.sent === props.prospectCount ? `les ${props.prospectCount}` : `sur ${props.prospectCount}`
  }
  if (step.planned > 0) return `+ ${step.planned} ${step.planned > 1 ? 'prévues' : 'prévue'}`
  return step.cancelled > 0 ? CampaignResultsFormat.count(step.cancelled, 'annulée', 'annulées') : ' '
}
</script>
