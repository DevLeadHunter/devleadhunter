<template>
  <div class="space-y-5">
    <!-- Résumé de la semaine -->
    <div class="grid grid-cols-2 gap-3 @4xl:grid-cols-4">
      <div class="card p-3.5">
        <p class="app-label">Envois cette semaine</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-ink)] tabular-nums">{{ totalItems }}</p>
      </div>
      <div class="card p-3.5">
        <p class="app-label">Emails J1</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-ink)] tabular-nums">{{ initialCount }}</p>
      </div>
      <div class="card p-3.5">
        <p class="app-label">Relances</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-accent-ink)] tabular-nums">{{ followupCount }}</p>
      </div>
      <div class="card p-3.5">
        <p class="app-label">Sites vérifiés</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-green)] tabular-nums">
          {{ weekReview.reviewed }} / {{ weekReview.total }}
        </p>
      </div>
    </div>

    <!-- Navigation de semaine + progression -->
    <div class="card p-3">
      <div class="flex flex-col gap-3 @2xl:flex-row @2xl:items-center @2xl:justify-between">
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--app-line)] text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            aria-label="Semaine précédente"
            @click="shiftWeek(-1)"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>
          <span class="min-w-[190px] text-center text-sm font-semibold text-[var(--app-ink)]">{{ weekLabel }}</span>
          <button
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--app-line)] text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            aria-label="Semaine suivante"
            @click="shiftWeek(1)"
          >
            <UIcon name="i-lucide-chevron-right" class="h-4 w-4" />
          </button>
          <button
            v-if="!isCurrentWeek"
            type="button"
            class="app-btn-secondary ml-1 h-9 px-3 text-xs"
            @click="goToCurrentWeek"
          >
            Cette semaine
          </button>
        </div>

        <div class="flex items-center gap-3">
          <button
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--app-line)] text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)] disabled:opacity-50"
            title="Actualiser"
            :disabled="isLoading"
            @click="load"
          >
            <UIcon name="i-lucide-rotate-cw" :class="['h-4 w-4', { 'animate-spin': isLoading }]" />
          </button>
          <div class="flex items-center gap-2" title="Sites vérifiés cette semaine">
            <span class="app-label">Vérifiés</span>
            <span class="h-1.5 w-24 overflow-hidden rounded-full bg-[var(--app-surface-2)]">
              <span
                class="block h-full rounded-full bg-[var(--app-green)] transition-all"
                :style="{ width: `${weekReviewPercent}%` }"
              ></span>
            </span>
            <span class="font-label text-xs text-[var(--app-ink-soft)]">
              {{ weekReview.reviewed }}/{{ weekReview.total }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Bande des 7 jours -->
    <div class="grid grid-cols-7 gap-2">
      <button
        v-for="day in days"
        :key="`pill-${day.key}`"
        type="button"
        :class="[
          'rounded-xl border p-2.5 text-center transition-all hover:-translate-y-0.5',
          day.isToday ? 'border-[var(--app-ink)] shadow-[var(--app-shadow-soft)]' : 'border-[var(--app-line)]',
          day.items.length === 0 ? 'opacity-55' : '',
          'bg-[var(--app-surface)]',
        ]"
        @click="scrollToDay(day.key)"
      >
        <span class="font-label text-[10px] text-[var(--app-ink-soft)]">{{ day.weekdayShort }}</span>
        <span
          :class="[
            'mt-0.5 block text-lg font-semibold tabular-nums',
            day.isToday ? 'text-[var(--app-accent-ink)]' : 'text-[var(--app-ink)]',
          ]"
        >
          {{ day.dayNum }}
        </span>
        <span class="mt-1 block text-[11px] text-[var(--app-ink-soft)]">
          <template v-if="day.items.length > 0">
            <span class="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-[var(--app-accent)] align-middle"></span>
            {{ day.items.length }}
          </template>
          <template v-else>—</template>
        </span>
      </button>
    </div>

    <!-- Chargement -->
    <div v-if="isLoading && totalItems === 0" class="flex items-center justify-center py-16">
      <UIcon name="i-lucide-loader-circle" class="h-7 w-7 animate-spin text-[var(--app-ink-soft)]" />
    </div>

    <!-- Semaine vide -->
    <div v-else-if="totalItems === 0" class="card px-6 py-14 text-center">
      <UIcon name="i-lucide-calendar-check-2" class="mx-auto h-8 w-8 text-[var(--app-faint)]" />
      <h3 class="font-display mt-4 text-lg font-semibold text-[var(--app-ink)]">Aucun envoi cette semaine</h3>
      <p class="text-muted mx-auto mt-2 max-w-sm text-sm leading-relaxed">
        Aucune campagne active n'a d'envoi programmé sur cette période. Lancez une campagne ou changez de semaine.
      </p>
    </div>

    <!-- Jours -->
    <template v-else>
      <section v-for="day in days" :id="`forecast-day-${day.key}`" :key="day.key" class="scroll-mt-4">
        <div class="flex flex-wrap items-baseline justify-between gap-2 px-1 pb-2.5">
          <div class="flex items-baseline gap-3">
            <h2 class="text-sm font-semibold text-[var(--app-ink)] capitalize">{{ day.weekday }}</h2>
            <span class="font-label text-xs text-[var(--app-ink-soft)]">{{ day.dateLabel }}</span>
            <span v-if="day.isToday" class="app-badge app-badge--progress !text-[0.6rem]">Aujourd'hui</span>
            <span v-if="day.items.length > 0" class="font-label text-[11px] text-[var(--app-faint)]">
              {{ day.items.length }} envoi{{ day.items.length > 1 ? 's' : '' }}
            </span>
          </div>
          <div v-if="day.review.total > 0" class="flex items-center gap-2">
            <span class="app-label">Vérifiés</span>
            <span class="h-1.5 w-16 overflow-hidden rounded-full bg-[var(--app-surface-2)]">
              <span
                class="block h-full rounded-full bg-[var(--app-green)] transition-all"
                :style="{ width: `${day.review.total ? (day.review.reviewed / day.review.total) * 100 : 0}%` }"
              ></span>
            </span>
            <span class="font-label text-xs text-[var(--app-ink-soft)]"
              >{{ day.review.reviewed }}/{{ day.review.total }}</span
            >
          </div>
        </div>

        <!-- Jour sans envoi -->
        <div
          v-if="day.items.length === 0"
          class="flex items-center gap-2.5 rounded-xl border border-dashed border-[var(--app-line)] px-4 py-3.5 text-sm text-[var(--app-faint)]"
        >
          <UIcon name="i-lucide-minus-circle" class="h-4 w-4" />
          Aucun envoi programmé
        </div>

        <!-- Lignes du jour -->
        <div v-else class="card overflow-hidden">
          <div
            v-for="item in day.items"
            :key="item.rowKey"
            :class="[
              'flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 transition-colors first:border-t-0',
              'border-t border-[var(--app-line-soft)]',
              item.isWarning ? 'bg-[var(--app-red-soft)]' : 'hover:bg-[var(--app-surface-2)]',
              item.reviewed ? 'opacity-60' : '',
            ]"
          >
            <span class="font-label w-14 shrink-0 text-sm font-medium text-[var(--app-ink)] tabular-nums">
              {{ item.timeLabel }}
            </span>

            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="truncate text-sm font-semibold text-[var(--app-ink)]">{{
                  item.prospect_name || `#${item.prospect_id}`
                }}</span>
                <span
                  v-if="item.isAutoSms"
                  class="font-label inline-flex shrink-0 items-center gap-1 rounded bg-[var(--app-violet-soft)] px-1.5 py-0.5 text-[10px] font-bold text-[var(--app-violet)]"
                  title="Envoi automatique SMS — heure estimée (fenêtre légale, 3 par passe, plafond quotidien)"
                >
                  <UIcon name="i-lucide-message-square-text" class="h-3 w-3" />
                  {{ item.queue_type === 'sms_relance' ? 'SMS J+30 auto' : 'SMS 1er contact auto' }}
                </span>
                <span
                  v-else
                  :class="[
                    'app-badge !py-0.5',
                    item.queue_type === 'initial' ? 'app-badge--info' : 'app-badge--progress',
                  ]"
                >
                  {{ item.queue_type === 'initial' ? 'J1' : `Relance ${item.follow_up_index}` }}
                </span>
                <span
                  v-if="item.ab_variant"
                  :class="[
                    'font-label rounded px-1.5 py-0.5 text-[10px] font-bold',
                    item.ab_variant === 'A'
                      ? 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
                      : 'bg-[var(--app-violet-soft)] text-[var(--app-violet)]',
                  ]"
                >
                  {{ item.ab_variant }}
                </span>
              </div>
              <p class="font-label mt-0.5 truncate text-[11.5px] text-[var(--app-ink-soft)]">
                <template v-if="item.metaLine">{{ item.metaLine }} · </template>
                <span class="text-[var(--app-faint)]">{{ item.campaign_name }}</span>
              </p>
            </div>

            <!-- Envoi bloqué (site expiré, etc.) -->
            <div v-if="item.isWarning" class="flex items-center gap-1.5 text-xs font-medium text-[var(--app-red)]">
              <UIcon name="i-lucide-triangle-alert" class="h-3.5 w-3.5 shrink-0" />
              {{ item.skip_reason }} — non envoyé
            </div>

            <!-- Lien du site + case vérifié -->
            <div v-else class="flex items-center gap-2.5">
              <a
                v-if="item.link"
                :href="openHref(item.link)"
                target="_blank"
                rel="noopener"
                :class="[
                  'font-label inline-flex max-w-[260px] items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs transition-colors',
                  'border-[var(--app-line)] bg-[var(--app-surface)] text-[var(--app-ink)] hover:border-[var(--app-accent)] hover:bg-[var(--app-accent-soft)] hover:text-[var(--app-accent-ink)]',
                  item.reviewed ? 'line-through' : '',
                ]"
                :title="item.link"
              >
                <UIcon name="i-lucide-globe" class="h-3.5 w-3.5 shrink-0" />
                <span class="truncate">{{ displayHost(item.link) }}</span>
                <UIcon name="i-lucide-arrow-up-right" class="h-3 w-3 shrink-0 opacity-70" />
              </a>
              <span v-else class="font-label text-xs text-[var(--app-faint)]">Pas de site</span>

              <span
                v-if="item.isSent"
                class="font-label inline-flex shrink-0 items-center gap-1 text-xs font-medium text-[var(--app-green)]"
                title="Cet e-mail est déjà parti"
              >
                <UIcon name="i-lucide-circle-check" class="h-3.5 w-3.5" />
                Envoyé
              </span>

              <button
                v-else-if="item.demo_site_id"
                type="button"
                :aria-pressed="item.reviewed"
                :disabled="pendingReviewIds.has(item.demo_site_id)"
                :title="item.reviewed ? 'Marquer comme non vérifié' : 'Marquer ce site comme vérifié'"
                :class="[
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors disabled:opacity-50',
                  item.reviewed
                    ? 'border-[var(--app-green)] bg-[var(--app-green)] text-white'
                    : 'border-[var(--app-line)] bg-[var(--app-surface)] text-transparent hover:border-[var(--app-green)] hover:text-[var(--app-green)]',
                ]"
                @click="toggleReview(item)"
              >
                <UIcon
                  :name="pendingReviewIds.has(item.demo_site_id) ? 'i-lucide-loader-circle' : 'i-lucide-check'"
                  :class="[
                    'h-4 w-4',
                    { 'animate-spin text-[var(--app-ink-soft)]': pendingReviewIds.has(item.demo_site_id) },
                  ]"
                />
              </button>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { CampaignService } from '~/services/campaignService'
import type { CampaignForecastItem, CampaignForecastResponse } from '~/services/campaignService'
import { DemoSiteService } from '~/services/demoSiteService'
import type { DemoSite } from '~/services/demoSiteService'
import { parseApiDate } from '~/utils/date'
import { useToast } from '~/composables/useToast'
import type { UseToastReturn } from '~/types/Composables'

/** A forecast item enriched with display fields and its live review state. */
type ForecastRow = CampaignForecastItem & {
  rowKey: string
  timeLabel: string
  metaLine: string
  isWarning: boolean
  isSent: boolean
  isAutoSms: boolean
  reviewed: boolean
}

/** One day bucket of the week, with its rows and review progress. */
type ForecastDay = {
  key: string
  date: Date
  weekdayShort: string
  weekday: string
  dayNum: number
  dateLabel: string
  isToday: boolean
  items: ForecastRow[]
  review: { reviewed: number; total: number }
}

const toast: UseToastReturn = useToast()

const LOCALE: string = 'fr-FR'

const weekStart: Ref<Date> = ref(startOfWeek(new Date()))
const items: Ref<CampaignForecastItem[]> = ref([])
const isLoading: Ref<boolean> = ref(false)
/** Demo-site ids whose review toggle is in flight (to disable the button meanwhile). */
const pendingReviewIds: Ref<Set<number>> = ref(new Set<number>())

/** Whether the viewed week is the one containing today. */
const isCurrentWeek: ComputedRef<boolean> = computed(
  (): boolean => weekStart.value.getTime() === startOfWeek(new Date()).getTime(),
)

/** `Semaine 35 · 25 – 31 août` (or spanning two months when needed). */
const weekLabel: ComputedRef<string> = computed((): string => {
  const end: Date = addDays(weekStart.value, 6)
  const startDay: string = weekStart.value.toLocaleDateString(LOCALE, { day: 'numeric' })
  const sameMonth: boolean = weekStart.value.getMonth() === end.getMonth()
  const startPart: string = sameMonth
    ? startDay
    : weekStart.value.toLocaleDateString(LOCALE, { day: 'numeric', month: 'short' })
  const endPart: string = end.toLocaleDateString(LOCALE, { day: 'numeric', month: 'short' })
  return `Semaine ${isoWeekNumber(weekStart.value)} · ${startPart} – ${endPart}`
})

/** The seven day buckets, each filled with the items scheduled on that local day. */
const days: ComputedRef<ForecastDay[]> = computed((): ForecastDay[] => {
  const today: string = dateKey(new Date())
  const buckets: ForecastDay[] = []
  for (let offset: number = 0; offset < 7; offset++) {
    const date: Date = addDays(weekStart.value, offset)
    const key: string = dateKey(date)
    const rows: ForecastRow[] = items.value
      .filter((item: CampaignForecastItem): boolean => dateKey(parseApiDate(item.scheduled_at)) === key)
      .map(toRow)
    buckets.push({
      key,
      date,
      weekdayShort: date.toLocaleDateString(LOCALE, { weekday: 'short' }).replace('.', ''),
      weekday: date.toLocaleDateString(LOCALE, { weekday: 'long' }),
      dayNum: date.getDate(),
      dateLabel: date.toLocaleDateString(LOCALE, { day: 'numeric', month: 'short' }),
      isToday: key === today,
      items: rows,
      review: reviewStats(rows),
    })
  }
  return buckets
})

const totalItems: ComputedRef<number> = computed((): number => items.value.length)

const initialCount: ComputedRef<number> = computed(
  (): number => items.value.filter((item: CampaignForecastItem): boolean => item.queue_type === 'initial').length,
)

const followupCount: ComputedRef<number> = computed(
  (): number => items.value.filter((item: CampaignForecastItem): boolean => item.queue_type === 'followup').length,
)

/** Distinct reviewable sites for the whole week, and how many are signed off. */
const weekReview: ComputedRef<{ reviewed: number; total: number }> = computed((): { reviewed: number; total: number } =>
  reviewStats(items.value.map(toRow)),
)

const weekReviewPercent: ComputedRef<number> = computed((): number =>
  weekReview.value.total ? Math.round((weekReview.value.reviewed / weekReview.value.total) * 100) : 0,
)

/**
 * The Monday 00:00 (local) of the week containing a date.
 * @param date - Any date in the target week.
 * @returns A new date at the local start of that week.
 */
function startOfWeek(date: Date): Date {
  const result: Date = new Date(date)
  result.setHours(0, 0, 0, 0)
  const weekday: number = (result.getDay() + 6) % 7 // Monday = 0
  result.setDate(result.getDate() - weekday)
  return result
}

/**
 * Add a number of days to a date without mutating the input.
 * @param date - Base date.
 * @param count - Days to add (may be negative).
 * @returns A new shifted date.
 */
function addDays(date: Date, count: number): Date {
  const result: Date = new Date(date)
  result.setDate(result.getDate() + count)
  return result
}

/**
 * ISO 8601 week number (weeks start Monday; week 1 holds the year's first Thursday).
 * @param date - Any date in the target week.
 * @returns The week number, 1 to 53.
 */
function isoWeekNumber(date: Date): number {
  const thursday: Date = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  thursday.setUTCDate(thursday.getUTCDate() - ((thursday.getUTCDay() + 6) % 7) + 3)
  const firstThursday: Date = new Date(Date.UTC(thursday.getUTCFullYear(), 0, 4))
  firstThursday.setUTCDate(firstThursday.getUTCDate() - ((firstThursday.getUTCDay() + 6) % 7) + 3)
  const msPerWeek: number = 7 * 24 * 3600 * 1000
  return 1 + Math.round((thursday.getTime() - firstThursday.getTime()) / msPerWeek)
}

/**
 * Local `YYYY-MM-DD` key used to bucket items by day.
 * @param date - Date to key.
 * @returns The zero-padded local date key.
 */
function dateKey(date: Date): string {
  const y: number = date.getFullYear()
  const m: string = String(date.getMonth() + 1).padStart(2, '0')
  const d: string = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/**
 * Enrich a raw forecast item with the fields the row template needs.
 * @param item - Raw forecast item from the API.
 * @returns A display-ready row.
 */
function toRow(item: CampaignForecastItem): ForecastRow {
  const metaParts: string[] = []
  if (item.prospect_city) metaParts.push(item.prospect_city)
  if (item.prospect_category) metaParts.push(item.prospect_category)
  const isAutoSms: boolean = item.queue_type === 'sms_relance' || item.queue_type === 'sms_cold'
  const time: string = parseApiDate(item.scheduled_at).toLocaleTimeString(LOCALE, {
    hour: '2-digit',
    minute: '2-digit',
  })
  return {
    ...item,
    rowKey: item.queue_id !== null ? `q-${item.queue_id}` : `sms-${item.queue_type}-${item.prospect_id}`,
    // An automated SMS has no queue row: its pass time is an estimate, flagged as such.
    timeLabel: isAutoSms ? `~${time}` : time,
    metaLine: metaParts.join(' · '),
    isWarning: item.status === 'skipped',
    isSent: item.status === 'sent',
    isAutoSms,
    reviewed: item.site_reviewed_at !== null && item.site_reviewed_at !== undefined,
  }
}

/**
 * Count distinct reviewable sites (pending rows with a demo site) and how many are reviewed.
 * @param rows - Rows to aggregate.
 * @returns The reviewed/total pair over distinct demo site ids.
 */
function reviewStats(rows: ForecastRow[]): { reviewed: number; total: number } {
  const reviewedById: Map<number, boolean> = new Map<number, boolean>()
  for (const row of rows) {
    // Sent rows can no longer be reviewed before sending, so they leave the review tally.
    if (row.isWarning || row.isSent || row.demo_site_id === null || row.demo_site_id === undefined) continue
    // A site counts as reviewed if any of its rows carries the sign-off (they share one state).
    reviewedById.set(row.demo_site_id, (reviewedById.get(row.demo_site_id) ?? false) || row.reviewed)
  }
  let reviewed: number = 0
  for (const value of reviewedById.values()) if (value) reviewed++
  return { reviewed, total: reviewedById.size }
}

/**
 * Build the href to open when verifying a site: the real link plus the internal-visit flag so the
 * operator's own visit is excluded from prospect behaviour tracking.
 * @param link - The link the email carries.
 * @returns The link to open in a new tab.
 */
function openHref(link: string): string {
  return DemoSiteService.withInternalFlag(link) ?? link
}

/**
 * Strip the protocol from a link for compact display.
 * @param link - Full URL.
 * @returns The URL without its `https://`/`http://` prefix.
 */
function displayHost(link: string): string {
  return link.replace(/^https?:\/\//, '')
}

/**
 * Fetch the forecast for the currently viewed week.
 * @returns A promise resolved once the items are loaded (or the error surfaced).
 */
async function load(): Promise<void> {
  isLoading.value = true
  try {
    // toISOString gives the UTC instant of the local week start — the backend windows on it directly.
    const response: CampaignForecastResponse = await CampaignService.getForecast(weekStart.value.toISOString(), 7)
    items.value = response.items
  } catch {
    toast.error('Impossible de charger le prévisionnel')
  } finally {
    isLoading.value = false
  }
}

/**
 * Move the viewed week by a number of weeks and reload.
 * @param direction - Weeks to move (-1 previous, +1 next).
 */
function shiftWeek(direction: number): void {
  weekStart.value = addDays(weekStart.value, direction * 7)
  void load()
}

/** Jump back to the current week and reload. */
function goToCurrentWeek(): void {
  weekStart.value = startOfWeek(new Date())
  void load()
}

/**
 * Scroll a day section into view from the week strip.
 * @param key - Day key of the target section.
 */
function scrollToDay(key: string): void {
  document.getElementById(`forecast-day-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/**
 * Toggle the operator's review sign-off for a row's site, updating every row that shares it.
 * @param row - The row whose site is being (un)reviewed.
 * @returns A promise resolved once the sign-off is persisted.
 */
async function toggleReview(row: ForecastRow): Promise<void> {
  const siteId: number | null | undefined = row.demo_site_id
  if (siteId === null || siteId === undefined || pendingReviewIds.value.has(siteId)) return
  const nextReviewed: boolean = !row.reviewed
  pendingReviewIds.value = new Set(pendingReviewIds.value).add(siteId)
  try {
    const site: DemoSite = await DemoSiteService.setSiteReviewed(siteId, nextReviewed)
    const reviewedAt: string | null = site.site_reviewed_at ?? null
    items.value = items.value.map(
      (item: CampaignForecastItem): CampaignForecastItem =>
        item.demo_site_id === siteId ? { ...item, site_reviewed_at: reviewedAt } : item,
    )
  } catch {
    toast.error("Impossible d'enregistrer la vérification")
  } finally {
    const next: Set<number> = new Set(pendingReviewIds.value)
    next.delete(siteId)
    pendingReviewIds.value = next
  }
}

onMounted((): void => {
  void load()
})
</script>
