<template>
  <section class="app-card min-w-0 overflow-hidden" aria-labelledby="campaign-results-replies-title">
    <header class="flex flex-wrap items-start gap-x-4 gap-y-3 px-[18px] pt-4">
      <div class="min-w-0 flex-[1_1_220px]">
        <h3 id="campaign-results-replies-title" class="text-[15px] font-medium text-[var(--app-ink)]">Réponses</h3>
        <p class="mt-0.5 text-[13px] text-[var(--app-ink-soft)]">{{ props.words.repliesOriginNote }}</p>
      </div>
      <div class="ml-auto flex items-center gap-3.5">
        <span v-if="props.replies.length > 0" class="text-sm text-[var(--app-ink-soft)] tabular-nums">
          {{ props.replies.length }}
        </span>
        <button type="button" class="app-btn-secondary h-8 px-3 text-xs" @click="emit('add-reply')">
          <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
          Ajouter une réponse
        </button>
      </div>
    </header>

    <ul v-if="replyLines.length > 0" class="mt-3">
      <li
        aria-hidden="true"
        class="hidden h-[34px] grid-cols-[104px_260px_minmax(0,1fr)_230px] items-center gap-x-[22px] border-t border-[var(--app-line-soft)] bg-[var(--app-surface-2)] px-[18px] @4xl:grid"
      >
        <span class="app-label">Reçue le</span>
        <span class="app-label">Prospect</span>
        <span class="app-label">Ce qu'il a écrit</span>
        <span class="app-label">Par où</span>
      </li>
      <li
        v-for="line in replyLines"
        :key="line.reply.id"
        class="grid cursor-pointer grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-1 border-t border-[var(--app-line-soft)] px-[18px] py-[13px] transition-colors hover:bg-[var(--app-surface-2)]/40 @4xl:grid-cols-[104px_260px_minmax(0,1fr)_230px] @4xl:items-baseline @4xl:gap-x-[22px] @4xl:gap-y-0"
        @click="emit('open-prospect', line.reply.prospect_id)"
      >
        <span class="flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1 @4xl:col-start-2 @4xl:row-start-1">
          <button
            type="button"
            class="cursor-pointer text-left text-sm font-medium text-[var(--app-ink)] hover:underline hover:decoration-[var(--app-faint)] hover:underline-offset-[3px]"
            @click.stop="emit('open-prospect', line.reply.prospect_id)"
          >
            {{ line.prospectName }}
          </button>
          <span class="app-badge" :class="CAMPAIGN_RESULTS_VERDICT_BADGE_CLASSES[line.reply.verdict]">
            {{ CAMPAIGN_RESULTS_VERDICT_LABELS[line.reply.verdict] }}
          </span>
        </span>
        <span
          class="text-[12.5px] whitespace-nowrap text-[var(--app-ink-soft)] tabular-nums @4xl:col-start-1 @4xl:row-start-1"
        >
          {{ line.receivedLabel }}
        </span>
        <p
          class="col-span-2 line-clamp-2 text-[13.5px] leading-snug text-[var(--app-ink)] @4xl:col-span-1 @4xl:col-start-3 @4xl:row-start-1"
        >
          {{ line.reply.excerpt ? `« ${line.reply.excerpt} »` : 'Sans texte.' }}
        </p>
        <p
          class="col-span-2 text-[12.5px] leading-snug text-[var(--app-ink-soft)] @4xl:col-span-1 @4xl:col-start-4 @4xl:row-start-1"
        >
          <span class="font-medium text-[var(--app-ink)]/80">{{
            CAMPAIGN_RESULTS_CHANNEL_LABELS[line.reply.channel]
          }}</span
          >{{ line.originLabel ? `, ${line.originLabel}` : '' }}
        </p>
      </li>
    </ul>

    <p
      v-else
      class="mt-3 border-t border-[var(--app-line-soft)] px-[18px] pt-4 pb-5 text-[13.5px] text-[var(--app-ink-soft)]"
    >
      Aucune réponse pour l'instant. Une réponse reçue par téléphone ou dans une autre boîte s'ajoute à la main.
    </p>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type { CampaignResultsReply, CampaignResultsRow, CampaignResultsSend } from '~/types/CampaignResults'
import type { CampaignChannelWords } from '~/types/CampaignChannelWords'
import type {
  CampaignResultsRepliesCardEmits,
  CampaignResultsRepliesCardProps,
  CampaignResultsReplyLine,
} from '~/types/CampaignResultsRepliesCard'
import { computed } from 'vue'
import {
  CAMPAIGN_RESULTS_CHANNEL_LABELS,
  CAMPAIGN_RESULTS_VERDICT_BADGE_CLASSES,
  CAMPAIGN_RESULTS_VERDICT_LABELS,
} from '~/constants/campaignResults'
import { CampaignResults } from '~/utils/campaignResults'
import { CampaignResultsFormat } from '~/utils/campaignResultsFormat'
import { parseApiDate } from '~/utils/date'

const props: CampaignResultsRepliesCardProps = defineProps({
  replies: {
    type: Array as PropType<CampaignResultsReply[]>,
    required: true,
  },
  rows: {
    type: Array as PropType<CampaignResultsRow[]>,
    required: true,
  },
  words: {
    type: Object as PropType<CampaignChannelWords>,
    required: true,
  },
})

const emit: EmitFn<CampaignResultsRepliesCardEmits> = defineEmits<CampaignResultsRepliesCardEmits>()

const rowByProspectId: ComputedRef<Map<number, CampaignResultsRow>> = computed(
  (): Map<number, CampaignResultsRow> =>
    new Map(props.rows.map((row: CampaignResultsRow): [number, CampaignResultsRow] => [row.prospect.id, row])),
)

const replyLines: ComputedRef<CampaignResultsReplyLine[]> = computed((): CampaignResultsReplyLine[] =>
  [...props.replies]
    .sort(
      (first: CampaignResultsReply, second: CampaignResultsReply): number =>
        parseApiDate(second.received_at).getTime() - parseApiDate(first.received_at).getTime(),
    )
    .map((reply: CampaignResultsReply): CampaignResultsReplyLine => {
      const receivedAt: Date = parseApiDate(reply.received_at)
      return {
        reply,
        prospectName: rowByProspectId.value.get(reply.prospect_id)?.prospect.name ?? 'Prospect',
        receivedLabel: `${CampaignResultsFormat.numericDay(receivedAt)} · ${CampaignResultsFormat.clock(receivedAt)}`,
        originLabel: originLabelOf(reply, receivedAt),
      }
    }),
)

/**
 * How long after which message a reply came: « 2 h après le premier mail », « 1 j 9 h après la relance ».
 * @param reply - The reply.
 * @param receivedAt - When it was received.
 * @returns The label, empty when the answered message is unknown.
 */
function originLabelOf(reply: CampaignResultsReply, receivedAt: Date): string {
  const sends: CampaignResultsSend[] = rowByProspectId.value.get(reply.prospect_id)?.prospect.sends ?? []
  const answeredSend: CampaignResultsSend | undefined = sends.find(
    (send: CampaignResultsSend): boolean => send.step === reply.answered_step && send.status === 'sent',
  )
  if (!answeredSend) return ''
  const minutes: number = Math.max(
    0,
    Math.round((receivedAt.getTime() - parseApiDate(answeredSend.at).getTime()) / 60000),
  )
  const lastStep: number = Math.max(0, ...sends.map((send: CampaignResultsSend): number => send.step))
  const stepName: string = CampaignResultsFormat.lowercaseFirst(
    CampaignResults.stepLabel(reply.answered_step, lastStep, props.words),
  )
  return `${CampaignResultsFormat.delay(minutes)} après ${reply.answered_step === 0 ? 'le' : 'la'} ${stepName}`
}
</script>
