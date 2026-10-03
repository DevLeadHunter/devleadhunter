<template>
  <div>
    <svg
      ref="journeySvg"
      :viewBox="`0 0 ${CAMPAIGN_RESULTS_JOURNEY_WIDTH} ${JOURNEY_HEIGHT}`"
      :width="CAMPAIGN_RESULTS_JOURNEY_WIDTH"
      :height="JOURNEY_HEIGHT"
      aria-hidden="true"
      class="block h-auto w-full max-w-[280px] overflow-visible max-md:max-w-none"
      @pointermove="showDay"
      @pointerleave="hoveredDayIndex = null"
    >
      <line
        v-if="trackSpan"
        :x1="trackSpan.from"
        :x2="trackSpan.to"
        :y1="CENTER_Y"
        :y2="CENTER_Y"
        class="stroke-[var(--app-line)]"
        stroke-width="1.5"
      />
      <line
        v-if="todayEdgeX !== null"
        :x1="todayEdgeX"
        :x2="todayEdgeX"
        y1="1"
        :y2="JOURNEY_HEIGHT - 1"
        class="stroke-[var(--app-ink)]"
        stroke-opacity="0.5"
      />

      <template v-for="mail in mails" :key="mail.key">
        <rect
          v-if="mail.kind === 'firstMail' || mail.kind === 'followUp'"
          :x="mail.x - MAIL_TICK_WIDTH / 2"
          :y="CENTER_Y - MAIL_TICK_HEIGHT / 2"
          :width="MAIL_TICK_WIDTH"
          :height="MAIL_TICK_HEIGHT"
          :rx="MAIL_TICK_WIDTH / 2"
          :class="mail.kind === 'firstMail' ? 'fill-[var(--app-ink)]' : 'fill-[var(--app-faint)]'"
        />
        <circle
          v-else-if="mail.kind === 'planned'"
          :cx="mail.x"
          :cy="CENTER_Y"
          :r="PLANNED_MAIL_RADIUS"
          class="fill-none stroke-[var(--app-ink-soft)]"
          stroke-width="1.2"
        />
        <path
          v-else
          :d="crossPath(mail.x)"
          :class="mail.kind === 'failed' ? 'stroke-[var(--app-red)]' : 'stroke-[var(--app-ink-soft)]'"
          stroke-width="1.4"
          stroke-linecap="round"
        />
      </template>

      <circle
        v-for="dot in visitDots"
        :key="dot.key"
        :cx="dot.x"
        :cy="CENTER_Y"
        :r="dot.radius"
        class="fill-[var(--app-blue)] stroke-[var(--app-surface)]"
        stroke-width="1.5"
      />

      <rect
        v-for="mark in replyMarks"
        :key="mark.key"
        :x="mark.x - REPLY_MARK_SIZE / 2"
        :y="CENTER_Y - REPLY_MARK_SIZE / 2"
        :width="REPLY_MARK_SIZE"
        :height="REPLY_MARK_SIZE"
        rx="1"
        :transform="`rotate(45 ${mark.x} ${CENTER_Y})`"
        :class="REPLY_MARK_CLASSES[mark.verdict]"
        stroke-width="1.5"
      />
    </svg>

    <UiPointerTooltip :is-open="hoveredDay !== null" :pointer-x="pointerX" :pointer-y="pointerY">
      <template v-if="hoveredDay">
        <p class="font-medium text-[var(--app-ink)]">
          {{ props.row.prospect.name }} · {{ CampaignResultsFormat.shortWeekday(hoveredDay.date) }}
        </p>
        <p v-for="event in hoveredDayEvents" :key="event.key">
          {{ CampaignResultsFormat.clock(event.at) }} · {{ event.label }}
        </p>
        <p v-if="hoveredDayEvents.length === 0">Rien ce jour-là.</p>
      </template>
    </UiPointerTooltip>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import type {
  CampaignResultsDay,
  CampaignResultsReply,
  CampaignResultsReplyVerdict,
  CampaignResultsRow,
  CampaignResultsSend,
  CampaignResultsVisit,
} from '~/types/CampaignResults'
import type { CampaignChannelWords } from '~/types/CampaignChannelWords'
import type {
  CampaignResultsJourneyEvent,
  CampaignResultsJourneyMail,
  CampaignResultsJourneyMailKind,
  CampaignResultsJourneyProps,
  CampaignResultsJourneyReplyMark,
  CampaignResultsJourneyVisitDot,
} from '~/types/CampaignResultsJourney'
import { computed, ref } from 'vue'
import { CAMPAIGN_RESULTS_JOURNEY_WIDTH, CAMPAIGN_RESULTS_VERDICT_LABELS } from '~/constants/campaignResults'
import { CampaignResults } from '~/utils/campaignResults'
import { CampaignResultsFormat } from '~/utils/campaignResultsFormat'
import { parseApiDate } from '~/utils/date'

const props: CampaignResultsJourneyProps = defineProps({
  row: {
    type: Object as PropType<CampaignResultsRow>,
    required: true,
  },
  days: {
    type: Array as PropType<CampaignResultsDay[]>,
    required: true,
  },
  words: {
    type: Object as PropType<CampaignChannelWords>,
    required: true,
  },
})

const JOURNEY_HEIGHT: number = 26
const CENTER_Y: number = JOURNEY_HEIGHT / 2
const MAIL_SLOT_RATIO: number = 0.15
const VISIT_SLOT_RATIO: number = 0.45
const REPLY_SLOT_RATIO: number = 0.85
const MAIL_TICK_WIDTH: number = 2.5
const MAIL_TICK_HEIGHT: number = 14
const PLANNED_MAIL_RADIUS: number = 3.4
const CANCELLED_MAIL_CROSS_SIZE: number = 7
const REPLY_MARK_SIZE: number = 7.8
const VISIT_DOT_RADIUS: number = 3.6
const REPEATED_VISIT_DOT_RADIUS: number = 4.3
const FREQUENT_VISIT_DOT_RADIUS: number = 5
const FREQUENT_VISITS_FROM: number = 3

const REPLY_MARK_CLASSES: Record<CampaignResultsReplyVerdict, string> = {
  interested: 'fill-[var(--app-green)] stroke-[var(--app-surface)]',
  refused: 'fill-[var(--app-red)] stroke-[var(--app-surface)]',
  other: 'fill-[var(--app-violet)] stroke-[var(--app-surface)]',
}

const journeySvg: Ref<SVGSVGElement | null> = ref(null)
const hoveredDayIndex: Ref<number | null> = ref(null)
const pointerX: Ref<number> = ref(0)
const pointerY: Ref<number> = ref(0)

const bandWidth: ComputedRef<number> = computed(
  (): number => CAMPAIGN_RESULTS_JOURNEY_WIDTH / Math.max(props.days.length, 1),
)

const dayIndexByKey: ComputedRef<Map<string, number>> = computed(
  (): Map<string, number> =>
    new Map(props.days.map((day: CampaignResultsDay, index: number): [string, number] => [day.key, index])),
)

const lastStep: ComputedRef<number> = computed((): number =>
  Math.max(0, ...props.row.prospect.sends.map((send: CampaignResultsSend): number => send.step)),
)

const mails: ComputedRef<CampaignResultsJourneyMail[]> = computed((): CampaignResultsJourneyMail[] =>
  props.row.prospect.sends.flatMap((send: CampaignResultsSend, index: number): CampaignResultsJourneyMail[] => {
    const dayIndex: number | undefined = dayIndexOf(send.at)
    if (dayIndex === undefined) return []
    return [{ key: `${send.step}-${index}`, kind: mailKindOf(send), x: slotX(dayIndex, MAIL_SLOT_RATIO) }]
  }),
)

const visitDots: ComputedRef<CampaignResultsJourneyVisitDot[]> = computed((): CampaignResultsJourneyVisitDot[] => {
  const visitsByDay: Map<number, number> = new Map()
  for (const visit of props.row.prospect.visits) {
    const dayIndex: number | undefined = dayIndexOf(visit.started_at)
    if (dayIndex !== undefined) visitsByDay.set(dayIndex, (visitsByDay.get(dayIndex) ?? 0) + 1)
  }
  return [...visitsByDay].map(
    ([dayIndex, visitCount]: [number, number]): CampaignResultsJourneyVisitDot => ({
      key: String(dayIndex),
      x: slotX(dayIndex, VISIT_SLOT_RATIO),
      radius: visitDotRadius(visitCount),
    }),
  )
})

const replyMarks: ComputedRef<CampaignResultsJourneyReplyMark[]> = computed((): CampaignResultsJourneyReplyMark[] => {
  const verdictByDay: Map<number, CampaignResultsReplyVerdict> = new Map()
  for (const reply of props.row.replies) {
    const dayIndex: number | undefined = dayIndexOf(reply.received_at)
    if (dayIndex !== undefined) verdictByDay.set(dayIndex, reply.verdict)
  }
  return [...verdictByDay].map(
    ([dayIndex, verdict]: [number, CampaignResultsReplyVerdict]): CampaignResultsJourneyReplyMark => ({
      key: String(dayIndex),
      x: slotX(dayIndex, REPLY_SLOT_RATIO),
      verdict,
    }),
  )
})

const todayEdgeX: ComputedRef<number | null> = computed((): number | null => {
  const todayIndex: number = props.days.findIndex((day: CampaignResultsDay): boolean => day.isToday)
  const hasDaysToCome: boolean = props.days.some((day: CampaignResultsDay): boolean => day.isFuture)
  return todayIndex >= 0 && hasDaysToCome ? bandWidth.value * (todayIndex + 1) : null
})

const trackSpan: ComputedRef<{ from: number; to: number } | null> = computed(
  (): { from: number; to: number } | null => {
    const firstMailAt: Date | null = props.row.firstMailAt
    if (!firstMailAt) return null
    const dayIndex: number | undefined = dayIndexByKey.value.get(CampaignResults.dayKey(firstMailAt))
    if (dayIndex === undefined) return null
    const from: number = slotX(dayIndex, MAIL_SLOT_RATIO)
    return { from, to: Math.max(from, todayEdgeX.value ?? CAMPAIGN_RESULTS_JOURNEY_WIDTH - 1) }
  },
)

const hoveredDay: ComputedRef<CampaignResultsDay | null> = computed((): CampaignResultsDay | null =>
  hoveredDayIndex.value === null ? null : (props.days[hoveredDayIndex.value] ?? null),
)

const hoveredDayEvents: ComputedRef<CampaignResultsJourneyEvent[]> = computed((): CampaignResultsJourneyEvent[] => {
  const day: CampaignResultsDay | null = hoveredDay.value
  if (!day) return []
  const isOnDay: (moment: Date) => boolean = (moment: Date): boolean => CampaignResults.dayKey(moment) === day.key
  const events: CampaignResultsJourneyEvent[] = [
    ...props.row.prospect.sends.map(
      (send: CampaignResultsSend, index: number): CampaignResultsJourneyEvent => ({
        key: `send-${index}`,
        at: parseApiDate(send.at),
        label: sendLabel(send),
      }),
    ),
    ...props.row.prospect.visits.map(
      (visit: CampaignResultsVisit, index: number): CampaignResultsJourneyEvent => ({
        key: `visit-${index}`,
        at: parseApiDate(visit.started_at),
        label:
          visit.active_seconds > 0
            ? `Visite, ${CampaignResultsFormat.activeTime(visit.active_seconds)} sur la page`
            : 'Visite',
      }),
    ),
    ...props.row.replies.map(
      (reply: CampaignResultsReply): CampaignResultsJourneyEvent => ({
        key: reply.id,
        at: parseApiDate(reply.received_at),
        label:
          reply.verdict === 'other'
            ? 'Réponse'
            : `Réponse : ${CAMPAIGN_RESULTS_VERDICT_LABELS[reply.verdict].toLocaleLowerCase('fr-FR')}`,
      }),
    ),
  ]
  return events
    .filter((event: CampaignResultsJourneyEvent): boolean => isOnDay(event.at))
    .sort(
      (first: CampaignResultsJourneyEvent, second: CampaignResultsJourneyEvent): number =>
        first.at.getTime() - second.at.getTime(),
    )
})

/**
 * Day of the journey a dated event falls on.
 * @param iso - The event's API date.
 * @returns The day's index, undefined outside the campaign's days.
 */
function dayIndexOf(iso: string): number | undefined {
  return dayIndexByKey.value.get(CampaignResults.dayKey(parseApiDate(iso)))
}

/**
 * Horizontal position of a slot inside a day: mails on the left, visits in the middle, replies on the right.
 * @param dayIndex - The day's index.
 * @param slotRatio - Where in the day's band the slot sits, from 0 to 1.
 * @returns The x coordinate.
 */
function slotX(dayIndex: number, slotRatio: number): number {
  return bandWidth.value * (dayIndex + slotRatio)
}

/**
 * Radius of a day's visit dot, larger when the prospect came back that day.
 * @param visitCount - The prospect's visits that day.
 * @returns The radius.
 */
function visitDotRadius(visitCount: number): number {
  if (visitCount >= FREQUENT_VISITS_FROM) return FREQUENT_VISIT_DOT_RADIUS
  if (visitCount > 1) return REPEATED_VISIT_DOT_RADIUS
  return VISIT_DOT_RADIUS
}

/**
 * The cross drawn on a cancelled or failed send.
 * @param centerX - The send's position.
 * @returns The SVG path.
 */
function crossPath(centerX: number): string {
  const half: number = CANCELLED_MAIL_CROSS_SIZE / 2
  const size: number = CANCELLED_MAIL_CROSS_SIZE
  return `M${centerX - half} ${CENTER_Y - half} l${size} ${size} M${centerX + half} ${CENTER_Y - half} l-${size} ${size}`
}

/**
 * How a send is drawn: a tick once sent, a ring while planned, a cross when cancelled or failed.
 * @param send - The send.
 * @returns The mark's kind.
 */
function mailKindOf(send: CampaignResultsSend): CampaignResultsJourneyMailKind {
  if (send.status === 'sent') return send.step === 0 ? 'firstMail' : 'followUp'
  if (send.status === 'planned') return 'planned'
  return send.status === 'failed' ? 'failed' : 'cancelled'
}

/**
 * What a send was, for the tooltip: « Premier mail », « Relance prévue », « Premier SMS, non reçu »…
 * @param send - The send.
 * @returns The label.
 */
function sendLabel(send: CampaignResultsSend): string {
  const name: string = CampaignResults.stepLabel(send.step, lastStep.value, props.words)
  const isFollowUp: boolean = send.step > 0
  if (send.status === 'planned') return `${name} ${isFollowUp ? 'prévue' : 'prévu'}`
  if (send.status === 'skipped') return `${name} ${isFollowUp ? 'annulée' : 'annulé'}`
  if (send.status === 'failed') return `${name}, échec d'envoi`
  return send.is_bounced ? `${name}, ${props.words.failedDeliveryNoun}` : name
}

/**
 * Follow the mouse over the journey and show the events of the day under it.
 * @param event - The pointer move.
 */
function showDay(event: PointerEvent): void {
  const bounds: DOMRect | undefined = journeySvg.value?.getBoundingClientRect()
  if (event.pointerType !== 'mouse' || !bounds || props.days.length === 0) return
  const ratio: number = (event.clientX - bounds.left) / Math.max(bounds.width, 1)
  hoveredDayIndex.value = Math.min(props.days.length - 1, Math.max(0, Math.floor(ratio * props.days.length)))
  pointerX.value = event.clientX
  pointerY.value = event.clientY
}
</script>
