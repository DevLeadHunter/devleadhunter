<template>
  <section class="app-card min-w-0" aria-labelledby="campaign-results-chart-title">
    <header class="flex flex-wrap items-start gap-x-4 gap-y-3 px-[18px] pt-4">
      <div class="min-w-0 flex-[1_1_220px]">
        <h3 id="campaign-results-chart-title" class="text-[15px] font-medium text-[var(--app-ink)]">Jour par jour</h3>
        <p class="mt-0.5 text-[13px] text-[var(--app-ink-soft)]">
          {{
            props.isVisitTrackingAvailable
              ? `Visites des sites, mails envoyés et réponses, ${props.periodLabel}.`
              : `Mails envoyés et réponses, ${props.periodLabel}.`
          }}
        </p>
      </div>
      <div class="ml-auto flex flex-wrap items-center gap-x-3.5 gap-y-2">
        <div
          class="flex flex-wrap items-center gap-x-3.5 gap-y-1 text-[12.5px] text-[var(--app-ink)]/80"
          aria-hidden="true"
        >
          <span v-if="props.isVisitTrackingAvailable" class="inline-flex items-center gap-1.5">
            <span class="h-0.5 w-3.5 rounded-full bg-[var(--app-blue)]"></span>Visites
          </span>
          <span class="inline-flex items-center gap-1.5">
            <span class="h-[11px] w-2 rounded-t-[2px] bg-[var(--app-ink)]"></span>Premiers mails
          </span>
          <span class="inline-flex items-center gap-1.5">
            <span class="h-[11px] w-2 rounded-t-[2px] bg-[var(--app-faint)]"></span>Relances
          </span>
          <span v-if="hasPlannedMails" class="inline-flex items-center gap-1.5">
            <span class="h-[11px] w-2 rounded-[2px] border border-dashed border-[var(--app-ink-soft)]"></span>Prévus
          </span>
          <span class="inline-flex items-center gap-1.5">
            <span class="h-[9px] w-3.5 rounded-full bg-[var(--app-ink)]"></span>Réponses
          </span>
        </div>
        <UiSegmentedControl v-model="displayMode" :options="DISPLAY_MODE_OPTIONS" label="Affichage du jour par jour" />
      </div>
    </header>

    <div
      v-show="displayMode === 'chart'"
      ref="chartFrame"
      class="relative touch-pan-y pt-2.5 pr-3 pb-1.5 pl-1.5 outline-none select-none focus-visible:ring-2 focus-visible:ring-[var(--app-ink-soft)] focus-visible:ring-inset"
      tabindex="0"
      role="group"
      aria-label="Graphique jour par jour. Flèches gauche et droite pour parcourir les jours."
      @keydown="moveActiveDay"
      @blur="activeDayIndex = null"
      @pointerleave="hideOnMouseLeave"
    >
      <svg
        v-if="geometry"
        ref="chartSvg"
        :viewBox="`0 0 ${geometry.width} ${geometry.height}`"
        :width="geometry.width"
        :height="geometry.height"
        role="img"
        :aria-label="chartSummary"
        class="block overflow-visible"
      >
        <g v-for="band in weekendBands" :key="band.key">
          <rect
            :x="band.x"
            :y="geometry.top"
            :width="band.width"
            :height="geometry.stripBottom - geometry.top"
            class="fill-[var(--app-ink)]"
            fill-opacity="0.03"
          />
          <text
            v-if="band.isLabelled"
            :x="band.x + band.width / 2"
            :y="geometry.plotBottom - 10"
            text-anchor="middle"
            class="fill-[var(--app-faint)] text-[10.5px]"
          >
            week-end
          </text>
        </g>

        <g v-for="(tick, tickIndex) in visitScale.ticks" :key="tick">
          <line
            :x1="geometry.left"
            :x2="geometry.width - geometry.right"
            :y1="visitY(tick)"
            :y2="visitY(tick)"
            :class="tick === 0 ? 'stroke-[var(--app-line)]' : 'stroke-[var(--app-line-soft)]'"
          />
          <text
            v-if="
              props.isVisitTrackingAvailable &&
              (!geometry.isNarrow || tickIndex % 2 === 0 || tickIndex === visitScale.ticks.length - 1)
            "
            :x="geometry.left - 8"
            :y="visitY(tick) + 4"
            text-anchor="end"
            class="fill-[var(--app-ink-soft)] text-[11px] tabular-nums"
          >
            {{ tick }}
          </text>
        </g>

        <g v-for="pill in replyPills" :key="pill.key">
          <line
            v-for="markerX in pill.markerXs"
            :key="markerX"
            :x1="markerX"
            :x2="markerX"
            :y1="geometry.top - REPLY_PILL_RISE + REPLY_PILL_HEIGHT"
            :y2="geometry.plotBottom"
            class="stroke-[var(--app-ink)]"
            stroke-opacity="0.35"
            stroke-dasharray="2 3"
          />
          <rect
            :x="pill.x"
            :y="geometry.top - REPLY_PILL_RISE"
            :width="pill.width"
            :height="REPLY_PILL_HEIGHT"
            :rx="REPLY_PILL_HEIGHT / 2"
            class="fill-[var(--app-ink)]"
          />
          <text
            :x="pill.x + pill.width / 2"
            :y="geometry.top - REPLY_PILL_RISE + REPLY_PILL_HEIGHT / 2"
            text-anchor="middle"
            dominant-baseline="central"
            class="fill-[var(--app-surface)] text-[10.5px] font-medium"
          >
            {{ pill.label }}
          </text>
        </g>

        <template v-if="visitLinePath">
          <path :d="visitAreaPath" class="fill-[var(--app-blue)]" fill-opacity="0.1" />
          <path
            :d="visitLinePath"
            class="fill-none stroke-[var(--app-blue)]"
            stroke-width="2"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
        </template>
        <g v-if="visitPeak">
          <circle
            :cx="visitPeak.x"
            :cy="visitPeak.y"
            r="4"
            class="fill-[var(--app-blue)] stroke-[var(--app-surface)]"
            stroke-width="2"
          />
          <text
            :x="visitPeak.isLabelBefore ? visitPeak.x - 9 : visitPeak.x + 9"
            :y="visitPeak.y - 6"
            :text-anchor="visitPeak.isLabelBefore ? 'end' : 'start'"
            class="fill-[var(--app-ink)] text-[11px] font-medium"
          >
            {{ visitPeak.label }}
          </text>
        </g>

        <g v-if="upcomingEdgeX !== null">
          <line
            :x1="upcomingEdgeX"
            :x2="upcomingEdgeX"
            :y1="geometry.top - 4"
            :y2="geometry.stripBottom"
            class="stroke-[var(--app-ink)]"
          />
          <text :x="upcomingEdgeX + 6" :y="geometry.top + 8" class="fill-[var(--app-ink)] text-[10.5px] font-medium">
            À venir
          </text>
        </g>

        <text
          v-if="!geometry.isNarrow"
          :x="geometry.left - 8"
          :y="geometry.stripBottom - 4"
          text-anchor="end"
          class="fill-[var(--app-ink-soft)] text-[11px]"
        >
          Mails
        </text>
        <line
          :x1="geometry.left"
          :x2="geometry.width - geometry.right"
          :y1="geometry.stripBottom"
          :y2="geometry.stripBottom"
          class="stroke-[var(--app-line)]"
        />
        <template v-for="segment in mailSegments" :key="segment.key">
          <rect
            v-if="segment.kind === 'planned'"
            :x="segment.x + 0.5"
            :y="segment.y + 0.5"
            :width="Math.max(0, segment.width - 1)"
            :height="Math.max(0, segment.height - 1)"
            rx="2"
            class="fill-none stroke-[var(--app-ink-soft)]"
            stroke-dasharray="3 2"
          />
          <path
            v-else-if="segment.isTop"
            :d="roundedTopBarPath(segment)"
            :class="segment.kind === 'firstMails' ? 'fill-[var(--app-ink)]' : 'fill-[var(--app-faint)]'"
          />
          <rect
            v-else
            :x="segment.x"
            :y="segment.y"
            :width="segment.width"
            :height="segment.height"
            :class="segment.kind === 'firstMails' ? 'fill-[var(--app-ink)]' : 'fill-[var(--app-faint)]'"
          />
        </template>
        <text
          v-for="label in mailLabels"
          :key="label.key"
          :x="label.x"
          :y="label.y"
          text-anchor="middle"
          class="text-[10.5px] tabular-nums"
          :class="label.isPlannedOnly ? 'fill-[var(--app-ink-soft)]' : 'fill-[var(--app-ink)]'"
        >
          {{ label.text }}
        </text>

        <text
          v-for="label in dayLabels"
          :key="label.key"
          :x="label.x"
          :y="geometry.height - 4"
          text-anchor="middle"
          class="text-[11px] tabular-nums"
          :class="label.isToday ? 'fill-[var(--app-ink)] font-medium' : 'fill-[var(--app-ink-soft)]'"
        >
          {{ label.text }}
        </text>

        <g v-if="activeDayIndex !== null && activeDay">
          <line
            :x1="dayCenterX(activeDayIndex)"
            :x2="dayCenterX(activeDayIndex)"
            :y1="geometry.top"
            :y2="geometry.stripBottom"
            class="stroke-[var(--app-ink)]"
            stroke-opacity="0.22"
          />
          <circle
            v-if="!activeDay.isFuture && props.isVisitTrackingAvailable"
            :cx="dayCenterX(activeDayIndex)"
            :cy="visitY(activeDay.visits)"
            r="4.5"
            class="fill-[var(--app-surface)] stroke-[var(--app-blue)]"
            stroke-width="2"
          />
        </g>
        <rect
          :x="geometry.left"
          :y="geometry.top - REPLY_PILL_RISE"
          :width="geometry.width - geometry.left - geometry.right"
          :height="geometry.stripBottom - geometry.top + REPLY_PILL_RISE"
          fill="transparent"
          class="cursor-crosshair"
          @pointermove="pointToDay"
          @pointerdown="pointToDay"
        />
      </svg>

      <div
        v-if="activeDay && activeDayIndex !== null"
        class="pointer-events-none absolute top-7 z-10 w-max max-w-[260px] min-w-[196px] rounded-[10px] border border-[var(--app-line)] bg-[var(--app-surface)] px-3 py-2.5 text-[13px] shadow-[var(--app-shadow-lift)]"
        :style="tooltipPosition"
      >
        <p class="app-label mb-2">
          {{ CampaignResultsFormat.shortWeekday(activeDay.date) }}{{ activeDay.isToday ? " · aujourd'hui" : '' }}
        </p>
        <div class="grid gap-1">
          <div
            v-for="tooltipRow in activeDayRows"
            :key="tooltipRow.key"
            class="flex items-center justify-between gap-3.5"
          >
            <span
              class="inline-flex items-center gap-2"
              :class="tooltipRow.isDetail ? 'pl-[22px] text-[var(--app-ink-soft)]' : 'text-[var(--app-ink)]/80'"
            >
              <span v-if="tooltipRow.swatch" :class="TOOLTIP_SWATCH_CLASSES[tooltipRow.swatch]"></span>
              {{ tooltipRow.label }}
            </span>
            <span class="font-medium text-[var(--app-ink)] tabular-nums">{{ tooltipRow.value }}</span>
          </div>
        </div>
        <div
          v-if="!activeDay.isFuture && activeDay.replies.length > 0"
          class="mt-2 grid gap-1 border-t border-[var(--app-line-soft)] pt-2 text-[12.5px] text-[var(--app-ink)]/80"
        >
          <p v-for="reply in activeDay.replies" :key="reply.id" class="flex items-center gap-1.5">
            <span
              class="h-[7px] w-[7px] shrink-0 rounded-full"
              :class="CAMPAIGN_RESULTS_VERDICT_DOT_CLASSES[reply.verdict]"
            ></span>
            {{ props.prospectNames[reply.prospect_id] ?? 'Prospect' }} ·
            {{ CAMPAIGN_RESULTS_VERDICT_LABELS[reply.verdict].toLocaleLowerCase('fr-FR') }},
            {{ CampaignResultsFormat.clock(parseApiDate(reply.received_at)) }}
          </p>
        </div>
      </div>
    </div>

    <div v-show="displayMode === 'table'" class="mt-3 border-t border-[var(--app-line-soft)]">
      <BaseTable min-width="640px" class="max-md:p-3">
        <template #head>
          <BaseTableTh>Jour</BaseTableTh>
          <BaseTableTh align="right">Premiers mails</BaseTableTh>
          <BaseTableTh align="right">Relances</BaseTableTh>
          <BaseTableTh v-if="props.isVisitTrackingAvailable" align="right">Visites</BaseTableTh>
          <BaseTableTh v-if="props.isVisitTrackingAvailable" align="right">Nouveaux visiteurs</BaseTableTh>
          <BaseTableTh>Réponses</BaseTableTh>
        </template>
        <BaseTableTr v-for="day in props.days" :key="day.key">
          <BaseTableTd class="text-sm whitespace-nowrap text-[var(--app-ink)]">
            {{ CampaignResultsFormat.shortWeekday(day.date) }}
          </BaseTableTd>
          <BaseTableTd label="Premiers mails" align="right" class="text-sm text-[var(--app-ink)] tabular-nums">
            {{ day.firstMails }}
            <span v-if="day.plannedFirstMails > 0" class="text-[var(--app-ink-soft)]">
              + {{ day.plannedFirstMails }} {{ day.plannedFirstMails > 1 ? 'prévus' : 'prévu' }}
            </span>
          </BaseTableTd>
          <BaseTableTd label="Relances" align="right" class="text-sm text-[var(--app-ink)] tabular-nums">
            {{ day.followUps }}
            <span v-if="day.plannedFollowUps > 0" class="text-[var(--app-ink-soft)]">
              + {{ day.plannedFollowUps }} {{ day.plannedFollowUps > 1 ? 'prévues' : 'prévue' }}
            </span>
          </BaseTableTd>
          <BaseTableTd
            v-if="props.isVisitTrackingAvailable"
            label="Visites"
            align="right"
            class="text-sm text-[var(--app-ink)] tabular-nums"
          >
            {{ day.isFuture ? '—' : day.visits }}
          </BaseTableTd>
          <BaseTableTd
            v-if="props.isVisitTrackingAvailable"
            label="Nouveaux visiteurs"
            align="right"
            class="text-sm text-[var(--app-ink)] tabular-nums"
          >
            {{ day.isFuture ? '—' : day.newVisitors }}
          </BaseTableTd>
          <BaseTableTd label="Réponses" class="text-sm text-[var(--app-ink)]">
            <template v-if="day.replies.length > 0">{{ replyAuthorsOf(day) }}</template>
            <span v-else class="text-[var(--app-ink-soft)]">—</span>
          </BaseTableTd>
        </BaseTableTr>
      </BaseTable>
    </div>

    <dl
      v-if="props.isVisitTrackingAvailable && props.marks.visits > 0"
      class="mt-1 grid grid-cols-2 border-t border-[var(--app-line-soft)] @3xl:grid-cols-4"
    >
      <div
        v-for="(mark, markIndex) in visitMarkCells"
        :key="mark.key"
        class="border-[var(--app-line-soft)] px-[18px] pt-3 pb-3.5"
        :class="{
          'border-l': markIndex % 2 === 1,
          'border-t @3xl:border-t-0': markIndex >= 2,
          '@3xl:border-l': markIndex === 2,
        }"
      >
        <dt class="app-label">{{ mark.label }}</dt>
        <dd class="mt-1.5 text-[17px] font-medium tracking-[-0.01em] text-[var(--app-ink)] tabular-nums">
          {{ mark.value
          }}<small class="text-[13px] font-normal tracking-normal text-[var(--app-ink-soft)]">{{ mark.suffix }}</small>
        </dd>
      </div>
    </dl>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import type { CampaignResultsDay, CampaignResultsReply, CampaignResultsVisitMarks } from '~/types/CampaignResults'
import type {
  CampaignResultsDailyChartBand,
  CampaignResultsDailyChartDayLabel,
  CampaignResultsDailyChartDisplayMode,
  CampaignResultsDailyChartGeometry,
  CampaignResultsDailyChartMailLabel,
  CampaignResultsDailyChartMailPart,
  CampaignResultsDailyChartMailSegment,
  CampaignResultsDailyChartMark,
  CampaignResultsDailyChartPeak,
  CampaignResultsDailyChartProps,
  CampaignResultsDailyChartReplyPill,
  CampaignResultsDailyChartTooltipRow,
  CampaignResultsDailyChartTooltipSwatch,
  CampaignResultsDailyChartVisitScale,
} from '~/types/CampaignResultsDailyChart'
import type { SelectFieldOption } from '~/types/SelectField'
import { useResizeObserver } from '@vueuse/core'
import { computed, ref } from 'vue'
import { CAMPAIGN_RESULTS_VERDICT_DOT_CLASSES, CAMPAIGN_RESULTS_VERDICT_LABELS } from '~/constants/campaignResults'
import { CampaignResultsFormat } from '~/utils/campaignResultsFormat'
import { parseApiDate } from '~/utils/date'

const props: CampaignResultsDailyChartProps = defineProps({
  days: {
    type: Array as PropType<CampaignResultsDay[]>,
    required: true,
  },
  prospectNames: {
    type: Object as PropType<Record<number, string>>,
    required: true,
  },
  marks: {
    type: Object as PropType<CampaignResultsVisitMarks>,
    required: true,
  },
  isVisitTrackingAvailable: {
    type: Boolean,
    required: true,
  },
  periodLabel: {
    type: String,
    required: true,
  },
})

const DISPLAY_MODE_OPTIONS: SelectFieldOption<CampaignResultsDailyChartDisplayMode>[] = [
  { value: 'chart', label: 'Graphique' },
  { value: 'table', label: 'Tableau' },
]

const TOOLTIP_SWATCH_CLASSES: Record<CampaignResultsDailyChartTooltipSwatch, string> = {
  visits: 'h-0.5 w-3.5 rounded-full bg-[var(--app-blue)]',
  firstMails: 'h-2.5 w-2 rounded-[2px] bg-[var(--app-ink)]',
  followUps: 'h-2.5 w-2 rounded-[2px] bg-[var(--app-faint)]',
}

const FRAME_PADDING_LEFT: number = 6
const FRAME_PADDING_RIGHT: number = 12
const MINIMUM_CHART_WIDTH: number = 300
const NARROW_CHART_BELOW: number = 560
const AXIS_WIDTH: number = 48
const NARROW_AXIS_WIDTH: number = 28
const PLOT_RIGHT_MARGIN: number = 6
const PLOT_TOP: number = 36
const PLOT_HEIGHT: number = 180
const NARROW_PLOT_HEIGHT: number = 140
const STRIP_GAP: number = 20
const STRIP_HEIGHT: number = 48
const DAY_LABELS_HEIGHT: number = 22
const DAY_CENTER_RATIO: number = 0.5
const DAY_LABEL_SPACING: number = 54
const NARROW_DAY_LABEL_SPACING: number = 20
const VISIT_TICK_STEPS: number[] = [1, 2, 5, 10, 20, 25, 50, 100, 250, 500]
const LARGEST_VISIT_TICK_STEP: number = 1000
const MINIMUM_VISIT_SCALE_STEPS: number = 2
const MAXIMUM_VISIT_SCALE_STEPS: number = 4
const PEAK_LABEL_WIDTH: number = 80
const WEEKEND_LABEL_MIN_WIDTH: number = 70
const BAND_JOIN_TOLERANCE: number = 0.5
const REPLY_PILL_RISE: number = 30
const REPLY_PILL_HEIGHT: number = 18
const REPLY_PILL_GAP: number = 6
const REPLY_PILL_CHARACTER_WIDTH: number = 6.1
const REPLY_PILL_PADDING: number = 18
const BAR_MAXIMUM_WIDTH: number = 22
const BAR_MINIMUM_WIDTH: number = 6
const BAR_WIDTH_RATIO: number = 0.42
const NARROW_BAR_WIDTH_RATIO: number = 0.8
const BAR_SEGMENT_GAP: number = 2
const BAR_CORNER_RADIUS: number = 3
const MAIL_LABEL_HEIGHT: number = 14
const MAIL_LABEL_OFFSET: number = 5
const MAIL_LABEL_MIN_BAND_WIDTH: number = 16
const TOOLTIP_OFFSET: number = 18
const TOOLTIP_FLIP_RATIO: number = 0.6
const MONOTONE_TANGENT_LIMIT: number = 3
const BEZIER_HANDLE_DIVISOR: number = 3

const chartFrame: Ref<HTMLElement | null> = ref(null)
const chartSvg: Ref<SVGSVGElement | null> = ref(null)
const chartWidth: Ref<number> = ref(0)
const displayMode: Ref<CampaignResultsDailyChartDisplayMode> = ref('chart')
const activeDayIndex: Ref<number | null> = ref(null)

const geometry: ComputedRef<CampaignResultsDailyChartGeometry | null> = computed(
  (): CampaignResultsDailyChartGeometry | null => {
    if (chartWidth.value <= 0 || props.days.length === 0) return null
    const width: number = Math.max(MINIMUM_CHART_WIDTH, Math.floor(chartWidth.value))
    const isNarrow: boolean = width < NARROW_CHART_BELOW
    const left: number = isNarrow ? NARROW_AXIS_WIDTH : AXIS_WIDTH
    const plotHeight: number = isNarrow ? NARROW_PLOT_HEIGHT : PLOT_HEIGHT
    const plotBottom: number = PLOT_TOP + plotHeight
    const stripBottom: number = plotBottom + STRIP_GAP + STRIP_HEIGHT
    return {
      width,
      height: stripBottom + DAY_LABELS_HEIGHT,
      isNarrow,
      left,
      right: PLOT_RIGHT_MARGIN,
      top: PLOT_TOP,
      plotHeight,
      plotBottom,
      stripBottom,
      bandWidth: (width - left - PLOT_RIGHT_MARGIN) / props.days.length,
    }
  },
)

const visitScale: ComputedRef<CampaignResultsDailyChartVisitScale> = computed(
  (): CampaignResultsDailyChartVisitScale => {
    const peak: number = Math.max(0, ...props.days.map((day: CampaignResultsDay): number => day.visits))
    const step: number =
      VISIT_TICK_STEPS.find((candidate: number): boolean => Math.ceil(peak / candidate) <= MAXIMUM_VISIT_SCALE_STEPS) ??
      LARGEST_VISIT_TICK_STEP
    const maximum: number = Math.max(step * MINIMUM_VISIT_SCALE_STEPS, Math.ceil(peak / step) * step)
    return {
      maximum,
      ticks: Array.from({ length: maximum / step + 1 }, (_: unknown, index: number): number => index * step),
    }
  },
)

const observedDayCount: ComputedRef<number> = computed(
  (): number => props.days.filter((day: CampaignResultsDay): boolean => !day.isFuture).length,
)

const hasPlannedMails: ComputedRef<boolean> = computed((): boolean =>
  props.days.some((day: CampaignResultsDay): boolean => day.plannedFirstMails + day.plannedFollowUps > 0),
)

const weekendBands: ComputedRef<CampaignResultsDailyChartBand[]> = computed((): CampaignResultsDailyChartBand[] => {
  const chart: CampaignResultsDailyChartGeometry | null = geometry.value
  if (!chart) return []
  const bands: CampaignResultsDailyChartBand[] = []
  props.days.forEach((day: CampaignResultsDay, index: number): void => {
    if (!day.isWeekend) return
    const previous: CampaignResultsDailyChartBand | undefined = bands[bands.length - 1]
    const x: number = chart.left + chart.bandWidth * index
    if (previous && Math.abs(previous.x + previous.width - x) < BAND_JOIN_TOLERANCE) {
      previous.width += chart.bandWidth
      previous.isLabelled = previous.width > WEEKEND_LABEL_MIN_WIDTH
      return
    }
    bands.push({ key: day.key, x, width: chart.bandWidth, isLabelled: chart.bandWidth > WEEKEND_LABEL_MIN_WIDTH })
  })
  return bands
})

const replyPills: ComputedRef<CampaignResultsDailyChartReplyPill[]> = computed(
  (): CampaignResultsDailyChartReplyPill[] => {
    const chart: CampaignResultsDailyChartGeometry | null = geometry.value
    if (!chart) return []
    const pills: CampaignResultsDailyChartReplyPill[] = []
    const placePill: (centerX: number, width: number) => number = (centerX: number, width: number): number =>
      Math.max(chart.left, Math.min(centerX - width / 2, chart.width - chart.right - width))
    props.days.forEach((day: CampaignResultsDay, index: number): void => {
      if (day.replies.length === 0) return
      const centerX: number = dayCenterX(index)
      const label: string = CampaignResultsFormat.count(day.replies.length, 'réponse')
      const width: number = pillWidth(label)
      const previous: CampaignResultsDailyChartReplyPill | undefined = pills[pills.length - 1]
      const x: number = placePill(centerX, width)
      if (previous && x < previous.x + previous.width + REPLY_PILL_GAP) {
        previous.replyCount += day.replies.length
        previous.markerXs.push(centerX)
        previous.label = CampaignResultsFormat.count(previous.replyCount, 'réponse')
        previous.width = pillWidth(previous.label)
        previous.x = placePill(((previous.markerXs[0] ?? centerX) + centerX) / 2, previous.width)
        return
      }
      pills.push({ key: day.key, x, width, label, replyCount: day.replies.length, markerXs: [centerX] })
    })
    return pills
  },
)

const visitLinePoints: ComputedRef<[number, number][]> = computed((): [number, number][] => {
  if (!geometry.value || !props.isVisitTrackingAvailable) return []
  return props.days
    .slice(0, observedDayCount.value)
    .map((day: CampaignResultsDay, index: number): [number, number] => [dayCenterX(index), visitY(day.visits)])
})

const visitLinePath: ComputedRef<string> = computed((): string => monotonePath(visitLinePoints.value))

const visitAreaPath: ComputedRef<string> = computed((): string => {
  const chart: CampaignResultsDailyChartGeometry | null = geometry.value
  const first: [number, number] | undefined = visitLinePoints.value[0]
  const last: [number, number] | undefined = visitLinePoints.value[visitLinePoints.value.length - 1]
  if (!chart || !first || !last || !visitLinePath.value) return ''
  return `${visitLinePath.value} L${last[0]} ${chart.plotBottom} L${first[0]} ${chart.plotBottom} Z`
})

const visitPeak: ComputedRef<CampaignResultsDailyChartPeak | null> = computed(
  (): CampaignResultsDailyChartPeak | null => {
    const chart: CampaignResultsDailyChartGeometry | null = geometry.value
    if (!chart || !props.isVisitTrackingAvailable) return null
    const observedDays: CampaignResultsDay[] = props.days.slice(0, observedDayCount.value)
    const peakVisits: number = Math.max(0, ...observedDays.map((day: CampaignResultsDay): number => day.visits))
    if (peakVisits === 0) return null
    const peakIndex: number = observedDays.findIndex((day: CampaignResultsDay): boolean => day.visits === peakVisits)
    const x: number = dayCenterX(peakIndex)
    return {
      x,
      y: visitY(peakVisits),
      label: CampaignResultsFormat.count(peakVisits, 'visite'),
      isLabelBefore: x + PEAK_LABEL_WIDTH > chart.width - chart.right,
    }
  },
)

const upcomingEdgeX: ComputedRef<number | null> = computed((): number | null => {
  const chart: CampaignResultsDailyChartGeometry | null = geometry.value
  if (!chart || observedDayCount.value >= props.days.length) return null
  return chart.left + chart.bandWidth * observedDayCount.value
})

const mailUnitHeight: ComputedRef<number> = computed((): number => {
  const busiestDay: number = Math.max(
    1,
    ...props.days.map(
      (day: CampaignResultsDay): number =>
        day.firstMails + day.followUps + day.plannedFirstMails + day.plannedFollowUps,
    ),
  )
  return (STRIP_HEIGHT - MAIL_LABEL_HEIGHT) / busiestDay
})

const mailSegments: ComputedRef<CampaignResultsDailyChartMailSegment[]> = computed(
  (): CampaignResultsDailyChartMailSegment[] => {
    const chart: CampaignResultsDailyChartGeometry | null = geometry.value
    if (!chart) return []
    const barWidth: number = Math.min(
      BAR_MAXIMUM_WIDTH,
      Math.max(
        chart.bandWidth * BAR_WIDTH_RATIO,
        Math.min(BAR_MINIMUM_WIDTH, chart.bandWidth * NARROW_BAR_WIDTH_RATIO),
      ),
    )
    return props.days.flatMap((day: CampaignResultsDay, index: number): CampaignResultsDailyChartMailSegment[] => {
      const parts: CampaignResultsDailyChartMailPart[] = mailPartsOf(day)
      let bottom: number = chart.stripBottom
      return parts.map(
        (part: CampaignResultsDailyChartMailPart, partIndex: number): CampaignResultsDailyChartMailSegment => {
          const height: number = part.count * mailUnitHeight.value
          const segment: CampaignResultsDailyChartMailSegment = {
            key: `${day.key}-${part.kind}`,
            kind: part.kind,
            x: dayCenterX(index) - barWidth / 2,
            y: bottom - height,
            width: barWidth,
            height,
            isTop: partIndex === parts.length - 1,
          }
          bottom = segment.y - BAR_SEGMENT_GAP
          return segment
        },
      )
    })
  },
)

const mailLabels: ComputedRef<CampaignResultsDailyChartMailLabel[]> = computed(
  (): CampaignResultsDailyChartMailLabel[] => {
    const chart: CampaignResultsDailyChartGeometry | null = geometry.value
    if (!chart || chart.bandWidth < MAIL_LABEL_MIN_BAND_WIDTH) return []
    return props.days.flatMap((day: CampaignResultsDay, index: number): CampaignResultsDailyChartMailLabel[] => {
      const sent: number = day.firstMails + day.followUps
      const planned: number = day.plannedFirstMails + day.plannedFollowUps
      if (sent + planned === 0) return []
      const stackedParts: number = mailPartsOf(day).length
      const barTop: number =
        chart.stripBottom - (sent + planned) * mailUnitHeight.value - (stackedParts - 1) * BAR_SEGMENT_GAP
      return [
        {
          key: day.key,
          x: dayCenterX(index),
          y: barTop - MAIL_LABEL_OFFSET,
          text: mailLabelText(sent, planned),
          isPlannedOnly: sent === 0,
        },
      ]
    })
  },
)

const dayLabels: ComputedRef<CampaignResultsDailyChartDayLabel[]> = computed(
  (): CampaignResultsDailyChartDayLabel[] => {
    const chart: CampaignResultsDailyChartGeometry | null = geometry.value
    if (!chart) return []
    const labelSpacing: number = chart.isNarrow ? NARROW_DAY_LABEL_SPACING : DAY_LABEL_SPACING
    const labelEvery: number = Math.max(1, Math.ceil(labelSpacing / chart.bandWidth))
    return props.days
      .map(
        (day: CampaignResultsDay, index: number): CampaignResultsDailyChartDayLabel => ({
          key: day.key,
          x: dayCenterX(index),
          text: chart.isNarrow ? CampaignResultsFormat.dayOfMonth(day.date) : CampaignResultsFormat.shortDay(day.date),
          isToday: day.isToday,
        }),
      )
      .filter((_: CampaignResultsDailyChartDayLabel, index: number): boolean => index % labelEvery === 0)
  },
)

const activeDay: ComputedRef<CampaignResultsDay | null> = computed((): CampaignResultsDay | null =>
  activeDayIndex.value === null ? null : (props.days[activeDayIndex.value] ?? null),
)

const activeDayRows: ComputedRef<CampaignResultsDailyChartTooltipRow[]> = computed(
  (): CampaignResultsDailyChartTooltipRow[] => {
    const day: CampaignResultsDay | null = activeDay.value
    if (!day) return []
    if (day.isFuture) {
      return [
        {
          key: 'planned-first',
          swatch: 'firstMails',
          label: 'Premiers mails prévus',
          value: String(day.plannedFirstMails),
          isDetail: false,
        },
        {
          key: 'planned-follow-ups',
          swatch: 'followUps',
          label: 'Relances prévues',
          value: String(day.plannedFollowUps),
          isDetail: false,
        },
      ]
    }
    const rows: CampaignResultsDailyChartTooltipRow[] = []
    if (props.isVisitTrackingAvailable) {
      rows.push({ key: 'visits', swatch: 'visits', label: 'Visites', value: String(day.visits), isDetail: false })
      rows.push({
        key: 'new-visitors',
        swatch: null,
        label: 'dont nouveaux visiteurs',
        value: String(day.newVisitors),
        isDetail: true,
      })
    }
    rows.push({
      key: 'first-mails',
      swatch: 'firstMails',
      label: 'Premiers mails',
      value: day.plannedFirstMails > 0 ? `${day.firstMails} + ${day.plannedFirstMails} prévus` : String(day.firstMails),
      isDetail: false,
    })
    rows.push({
      key: 'follow-ups',
      swatch: 'followUps',
      label: 'Relances',
      value: day.plannedFollowUps > 0 ? `${day.followUps} + ${day.plannedFollowUps} prévues` : String(day.followUps),
      isDetail: false,
    })
    return rows
  },
)

const tooltipPosition: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
  const chart: CampaignResultsDailyChartGeometry | null = geometry.value
  if (!chart || activeDayIndex.value === null) return {}
  const frameX: number = FRAME_PADDING_LEFT + dayCenterX(activeDayIndex.value)
  const frameWidth: number = chart.width + FRAME_PADDING_LEFT + FRAME_PADDING_RIGHT
  if (frameX > frameWidth * TOOLTIP_FLIP_RATIO) return { right: `${frameWidth - frameX + TOOLTIP_OFFSET}px` }
  return { left: `${frameX + TOOLTIP_OFFSET}px` }
})

const chartSummary: ComputedRef<string> = computed((): string => {
  const sumOf: (pick: (day: CampaignResultsDay) => number) => number = (
    pick: (day: CampaignResultsDay) => number,
  ): number => props.days.reduce((total: number, day: CampaignResultsDay): number => total + pick(day), 0)
  const visits: string = props.isVisitTrackingAvailable
    ? `${CampaignResultsFormat.count(
        sumOf((day: CampaignResultsDay): number => day.visits),
        'visite',
      )}, `
    : ''
  return `${visits}${CampaignResultsFormat.count(
    sumOf((day: CampaignResultsDay): number => day.firstMails),
    'premier mail envoyé',
    'premiers mails envoyés',
  )}, ${CampaignResultsFormat.count(
    sumOf((day: CampaignResultsDay): number => day.followUps),
    'relance envoyée',
    'relances envoyées',
  )} et ${CampaignResultsFormat.count(
    sumOf((day: CampaignResultsDay): number => day.replies.length),
    'réponse',
  )} ${props.periodLabel}.`
})

const visitMarkCells: ComputedRef<CampaignResultsDailyChartMark[]> = computed((): CampaignResultsDailyChartMark[] => [
  {
    key: 'median-delay',
    label: 'Délai médian envoi → visite',
    value: props.marks.medianDelayMinutes === null ? '—' : CampaignResultsFormat.delay(props.marks.medianDelayMinutes),
    suffix: '',
  },
  {
    key: 'within-hour',
    label: "Visiteurs venus dans l'heure",
    value: String(props.marks.visitorsWithinHour),
    suffix: ` sur ${props.marks.visitors}`,
  },
  {
    key: 'phone',
    label: 'Visites sur téléphone',
    value: String(props.marks.phoneVisits),
    suffix: ` sur ${props.marks.visits}`,
  },
  {
    key: 'evening',
    label: 'Visites après 18 h',
    value: String(props.marks.eveningVisits),
    suffix: ` sur ${props.marks.visits}`,
  },
])

/**
 * Horizontal centre of a day on the chart.
 * @param dayIndex - The day's index.
 * @returns The x coordinate.
 */
function dayCenterX(dayIndex: number): number {
  const chart: CampaignResultsDailyChartGeometry | null = geometry.value
  return chart ? chart.left + chart.bandWidth * (dayIndex + DAY_CENTER_RATIO) : 0
}

/**
 * Height of a visit count on the chart.
 * @param visits - Visits of a day.
 * @returns The y coordinate.
 */
function visitY(visits: number): number {
  const chart: CampaignResultsDailyChartGeometry | null = geometry.value
  return chart ? chart.plotBottom - (visits / visitScale.value.maximum) * chart.plotHeight : 0
}

/**
 * Who replied on a day and how, for the table view: « TP Motorsport (intéressé), Chergui (refus) ».
 * @param day - The day.
 * @returns The authors with their verdicts.
 */
function replyAuthorsOf(day: CampaignResultsDay): string {
  return day.replies
    .map(
      (reply: CampaignResultsReply): string =>
        `${props.prospectNames[reply.prospect_id] ?? 'Prospect'} (${CAMPAIGN_RESULTS_VERDICT_LABELS[reply.verdict].toLocaleLowerCase('fr-FR')})`,
    )
    .join(', ')
}

/**
 * The stacked parts of a day's mail bar, from the bottom: first mails, follow-ups, then the planned ones.
 * @param day - The day.
 * @returns The parts holding at least one mail.
 */
function mailPartsOf(day: CampaignResultsDay): CampaignResultsDailyChartMailPart[] {
  const parts: CampaignResultsDailyChartMailPart[] = []
  if (day.firstMails > 0) parts.push({ kind: 'firstMails', count: day.firstMails })
  if (day.followUps > 0) parts.push({ kind: 'followUps', count: day.followUps })
  const planned: number = day.plannedFirstMails + day.plannedFollowUps
  if (planned > 0) parts.push({ kind: 'planned', count: planned })
  return parts
}

/**
 * The count above a day's mail bar: the mails sent, then the planned ones after a « + ».
 * @param sent - Mails sent that day.
 * @param planned - Mails still planned that day.
 * @returns « 6 », « 6 +2 », or « 2 » when none left yet.
 */
function mailLabelText(sent: number, planned: number): string {
  if (sent === 0) return String(planned)
  if (planned === 0) return String(sent)
  return `${sent} +${planned}`
}

/**
 * Width of a reply pill for its label.
 * @param label - The pill's text.
 * @returns The width.
 */
function pillWidth(label: string): number {
  return label.length * REPLY_PILL_CHARACTER_WIDTH + REPLY_PILL_PADDING
}

/**
 * Outline of the top part of a stacked bar, its two upper corners rounded.
 * @param segment - The bar segment.
 * @returns The SVG path.
 */
function roundedTopBarPath(segment: CampaignResultsDailyChartMailSegment): string {
  const radius: number = Math.min(BAR_CORNER_RADIUS, segment.height, segment.width / 2)
  const right: number = segment.x + segment.width
  const bottom: number = segment.y + segment.height
  return `M${segment.x} ${bottom} V${segment.y + radius} Q${segment.x} ${segment.y} ${segment.x + radius} ${segment.y} H${right - radius} Q${right} ${segment.y} ${right} ${segment.y + radius} V${bottom} Z`
}

/**
 * Smooth curve through the points that never overshoots them (monotone cubic interpolation).
 * @param points - The points, left to right.
 * @returns The SVG path, empty under two points.
 */
function monotonePath(points: [number, number][]): string {
  if (points.length < 2) return ''
  const xs: number[] = points.map((point: [number, number]): number => point[0])
  const ys: number[] = points.map((point: [number, number]): number => point[1])
  const widths: number[] = []
  const slopes: number[] = []
  for (let index: number = 0; index < points.length - 1; index += 1) {
    const width: number = (xs[index + 1] ?? 0) - (xs[index] ?? 0)
    widths.push(width)
    slopes.push(((ys[index + 1] ?? 0) - (ys[index] ?? 0)) / width)
  }
  const tangents: number[] = [slopes[0] ?? 0]
  for (let index: number = 1; index < points.length - 1; index += 1) {
    const before: number = slopes[index - 1] ?? 0
    const after: number = slopes[index] ?? 0
    tangents.push(before * after <= 0 ? 0 : (before + after) / 2)
  }
  tangents.push(slopes[slopes.length - 1] ?? 0)
  for (let index: number = 0; index < slopes.length; index += 1) {
    const slope: number = slopes[index] ?? 0
    if (slope === 0) {
      tangents[index] = 0
      tangents[index + 1] = 0
      continue
    }
    const alpha: number = (tangents[index] ?? 0) / slope
    const beta: number = (tangents[index + 1] ?? 0) / slope
    const magnitude: number = alpha * alpha + beta * beta
    if (magnitude > MONOTONE_TANGENT_LIMIT ** 2) {
      const scale: number = MONOTONE_TANGENT_LIMIT / Math.sqrt(magnitude)
      tangents[index] = scale * alpha * slope
      tangents[index + 1] = scale * beta * slope
    }
  }
  let path: string = `M${xs[0]} ${ys[0]}`
  for (let index: number = 0; index < points.length - 1; index += 1) {
    const handle: number = (widths[index] ?? 0) / BEZIER_HANDLE_DIVISOR
    const startX: number = xs[index] ?? 0
    const startY: number = ys[index] ?? 0
    const endX: number = xs[index + 1] ?? 0
    const endY: number = ys[index + 1] ?? 0
    path += ` C${startX + handle} ${startY + (tangents[index] ?? 0) * handle} ${endX - handle} ${endY - (tangents[index + 1] ?? 0) * handle} ${endX} ${endY}`
  }
  return path
}

/**
 * Show the day under the pointer: hovered with a mouse, touched or dragged with a finger.
 * @param event - The pointer event on the chart.
 */
function pointToDay(event: PointerEvent): void {
  const chart: CampaignResultsDailyChartGeometry | null = geometry.value
  const bounds: DOMRect | undefined = chartSvg.value?.getBoundingClientRect()
  if (!chart || !bounds || bounds.width === 0) return
  const x: number = (event.clientX - bounds.left) * (chart.width / bounds.width)
  activeDayIndex.value = Math.min(props.days.length - 1, Math.max(0, Math.floor((x - chart.left) / chart.bandWidth)))
}

/**
 * Hide the day's tooltip when the mouse leaves the chart; a finger keeps it until the next touch.
 * @param event - The pointer leaving the chart.
 */
function hideOnMouseLeave(event: PointerEvent): void {
  if (event.pointerType === 'mouse') activeDayIndex.value = null
}

/**
 * Walk through the days with the arrow keys, Escape closing the tooltip.
 * @param event - The key pressed on the focused chart.
 */
function moveActiveDay(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    activeDayIndex.value = null
    return
  }
  if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return
  event.preventDefault()
  const step: number = event.key === 'ArrowRight' ? 1 : -1
  const current: number = activeDayIndex.value ?? (step > 0 ? -1 : props.days.length)
  activeDayIndex.value = Math.min(props.days.length - 1, Math.max(0, current + step))
}

useResizeObserver(chartFrame, (entries: ResizeObserverEntry[]): void => {
  const width: number = entries[0]?.contentRect.width ?? 0
  if (width > 0) chartWidth.value = width
})
</script>
