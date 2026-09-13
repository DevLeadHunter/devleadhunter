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
            data-forecast-drop-next
            :class="[
              'flex h-9 w-9 items-center justify-center rounded-lg border text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]',
              dropTargetKey === NEXT_WEEK_DROP_KEY
                ? 'border-[var(--app-accent)] ring-2 ring-[var(--app-accent)]'
                : 'border-[var(--app-line)]',
            ]"
            aria-label="Semaine suivante"
            title="Semaine suivante — déposez-y un SMS pour le décaler de 7 jours"
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
        :data-forecast-drop-day="day.key"
        :class="[
          'rounded-xl border p-2.5 text-center transition-all hover:-translate-y-0.5',
          day.isToday ? 'border-[var(--app-ink)] shadow-[var(--app-shadow-soft)]' : 'border-[var(--app-line)]',
          day.items.length === 0 && !isSmsDragActive ? 'opacity-55' : '',
          dropTargetKey === day.key ? 'border-[var(--app-accent)] !opacity-100 ring-2 ring-[var(--app-accent)]' : '',
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

        <!-- Jour sans envoi — cible de drop d'un SMS planifié comme la pastille du haut -->
        <div
          v-if="day.items.length === 0"
          :data-forecast-drop-day="day.key"
          :class="[
            'flex items-center gap-2.5 rounded-xl border border-dashed px-4 py-3.5 text-sm transition-colors',
            dropTargetKey === day.key
              ? 'border-[var(--app-accent)] bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
              : 'border-[var(--app-line)] text-[var(--app-faint)]',
          ]"
        >
          <UIcon :name="isSmsDragActive ? 'i-lucide-calendar-plus' : 'i-lucide-minus-circle'" class="h-4 w-4" />
          {{ isSmsDragActive ? 'Déposer ici pour déplacer cet envoi' : 'Aucun envoi programmé' }}
        </div>

        <!-- Lignes du jour — la carte entière accepte aussi le drop (un jour peut cumuler les envois) -->
        <div
          v-else
          :data-forecast-drop-day="day.key"
          :class="['card overflow-hidden', dropTargetKey === day.key ? 'ring-2 ring-[var(--app-accent)]' : '']"
        >
          <div
            v-for="item in day.items"
            :key="item.rowKey"
            :data-forecast-row="item.rowKey"
            :class="[
              'flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 transition-colors first:border-t-0',
              'border-t border-[var(--app-line-soft)]',
              item.isWarning ? 'bg-[var(--app-red-soft)]' : 'hover:bg-[var(--app-surface-2)]',
              item.reviewed ? 'opacity-60' : '',
            ]"
          >
            <button
              v-if="item.isAutoSms && item.sms_queue_id && !item.isWarning && !item.isSent"
              type="button"
              class="-ml-1.5 flex h-8 w-5 shrink-0 cursor-grab touch-none items-center justify-center rounded text-[var(--app-faint)] transition-colors hover:text-[var(--app-ink)]"
              title="Glisser sur un jour de la semaine (ou « Semaine suivante ») pour déplacer cet envoi"
              @pointerdown="onSmsGripPointerDown($event, item)"
            >
              <UIcon name="i-lucide-grip-vertical" class="h-4 w-4" />
            </button>

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
                  title="Envoi SMS automatique planifié — annulable et déplaçable (fenêtre légale, 3 par passe de 30 min, plafond quotidien)"
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
            <div v-if="item.isWarning" class="flex items-center gap-2 text-xs font-medium text-[var(--app-red)]">
              <UIcon name="i-lucide-triangle-alert" class="h-3.5 w-3.5 shrink-0" />
              {{ item.skip_reason }} — non envoyé
              <button
                v-if="item.isAutoSms && item.sms_queue_id"
                type="button"
                class="app-btn-secondary h-7 shrink-0 px-2 text-[11px]"
                @click="openReschedule(item)"
              >
                Replanifier
              </button>
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

              <template v-if="item.isAutoSms && !item.isSent">
                <button
                  v-if="item.sms_queue_id"
                  type="button"
                  title="Déplacer cet envoi à une autre date"
                  class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-ink-soft)] hover:text-[var(--app-ink)]"
                  @click="openReschedule(item)"
                >
                  <UIcon name="i-lucide-calendar-clock" class="h-4 w-4" />
                </button>

                <button
                  v-if="item.sms_queue_id"
                  type="button"
                  :disabled="pendingCancelIds.has(item.sms_queue_id)"
                  title="Annuler cet envoi planifié"
                  class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-red)] hover:text-[var(--app-red)] disabled:opacity-50"
                  @click="cancelAutoSms(item)"
                >
                  <UIcon
                    :name="pendingCancelIds.has(item.sms_queue_id) ? 'i-lucide-loader-circle' : 'i-lucide-x'"
                    :class="['h-4 w-4', { 'animate-spin': pendingCancelIds.has(item.sms_queue_id) }]"
                  />
                </button>

                <button
                  type="button"
                  :disabled="pendingExcludeIds.has(item.prospect_id)"
                  title="Ne plus jamais envoyer de SMS automatique à ce prospect"
                  class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-red)] hover:text-[var(--app-red)] disabled:opacity-50"
                  @click="excludeAutoSms(item)"
                >
                  <UIcon
                    :name="pendingExcludeIds.has(item.prospect_id) ? 'i-lucide-loader-circle' : 'i-lucide-bell-off'"
                    :class="['h-4 w-4', { 'animate-spin': pendingExcludeIds.has(item.prospect_id) }]"
                  />
                </button>
              </template>
            </div>

            <!-- Déplacement d'un envoi SMS planifié : date + heure exactes, recalées serveur si hors fenêtre. -->
            <div v-if="rescheduleTargetKey === item.rowKey" class="flex w-full flex-wrap items-center gap-2 pt-1">
              <input v-model="rescheduleValue" type="datetime-local" class="input-field h-8 w-auto text-xs" />
              <button
                type="button"
                class="app-btn-primary h-8 px-3 text-xs"
                :disabled="isRescheduling || !rescheduleValue"
                @click="confirmReschedule(item)"
              >
                {{ isRescheduling ? 'Déplacement…' : 'Confirmer' }}
              </button>
              <button
                type="button"
                class="app-btn-secondary h-8 px-3 text-xs"
                :disabled="isRescheduling"
                @click="closeReschedule"
              >
                Annuler
              </button>
              <span class="text-[11px] text-[var(--app-faint)]">
                Hors fenêtre légale, l'envoi est recalé au prochain créneau autorisé.
              </span>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import type { ForecastSmsDragSession } from '~/types/UiCampaignForecast'
import { CampaignService } from '~/services/campaignService'
import type { CampaignForecastItem, CampaignForecastResponse } from '~/services/campaignService'
import { DemoSiteService } from '~/services/demoSiteService'
import type { DemoSite } from '~/services/demoSiteService'
import { ProspectsService } from '~/services/prospectsService'
import { SmsService } from '~/services/smsService'
import type { SmsAutoQueueAction } from '~/services/smsService'
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
/** Prospect ids whose « couper les SMS automatiques » action is in flight. */
const pendingExcludeIds: Ref<Set<number>> = ref(new Set<number>())
/** Planned-SMS row ids whose cancellation is in flight. */
const pendingCancelIds: Ref<Set<number>> = ref(new Set<number>())
/** Row key whose inline « déplacer » editor is open (null = none). */
const rescheduleTargetKey: Ref<string | null> = ref(null)
/** Value of the reschedule datetime-local input. */
const rescheduleValue: Ref<string> = ref('')
const isRescheduling: Ref<boolean> = ref(false)

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
    rowKey: item.queue_id !== null ? `q-${item.queue_id}` : `s-${item.sms_queue_id ?? item.prospect_id}`,
    timeLabel: time,
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

/**
 * Cut every automated SMS for a row's prospect, then reload so its rows show as held back.
 * @param row - The planned-SMS row whose prospect is being excluded.
 * @returns A promise resolved once the exclusion is persisted.
 */
async function excludeAutoSms(row: ForecastRow): Promise<void> {
  const prospectId: number = row.prospect_id
  if (pendingExcludeIds.value.has(prospectId)) return
  pendingExcludeIds.value = new Set(pendingExcludeIds.value).add(prospectId)
  try {
    await ProspectsService.setSmsAutoExcluded(prospectId, true)
    toast.success('SMS automatiques coupés pour ce prospect')
    await load()
  } catch {
    toast.error('Impossible de couper les SMS automatiques de ce prospect')
  } finally {
    const next: Set<number> = new Set(pendingExcludeIds.value)
    next.delete(prospectId)
    pendingExcludeIds.value = next
  }
}

/**
 * Cancel one planned automated SMS, then reload the week.
 * @param row - The planned-SMS row to cancel.
 * @returns A promise resolved once the cancellation is persisted.
 */
async function cancelAutoSms(row: ForecastRow): Promise<void> {
  const rowId: number | null | undefined = row.sms_queue_id
  if (rowId === null || rowId === undefined || pendingCancelIds.value.has(rowId)) return
  pendingCancelIds.value = new Set(pendingCancelIds.value).add(rowId)
  try {
    await SmsService.cancelAutoQueue(rowId)
    toast.success('Envoi SMS annulé')
    await load()
  } catch {
    toast.error("Impossible d'annuler cet envoi")
  } finally {
    const next: Set<number> = new Set(pendingCancelIds.value)
    next.delete(rowId)
    pendingCancelIds.value = next
  }
}

/**
 * `YYYY-MM-DDTHH:mm` local value for a datetime-local input.
 * @param moment - The date to format.
 * @returns The input-ready local value.
 */
function toDatetimeLocalValue(moment: Date): string {
  const pad: (value: number) => string = (value: number): string => String(value).padStart(2, '0')
  return `${moment.getFullYear()}-${pad(moment.getMonth() + 1)}-${pad(moment.getDate())}T${pad(moment.getHours())}:${pad(moment.getMinutes())}`
}

/**
 * Open the inline « déplacer » editor for a row, prefilled with its current slot.
 * @param row - The planned-SMS row to move.
 */
function openReschedule(row: ForecastRow): void {
  rescheduleTargetKey.value = row.rowKey
  rescheduleValue.value = toDatetimeLocalValue(parseApiDate(row.scheduled_at))
}

/** Close the inline « déplacer » editor without saving. */
function closeReschedule(): void {
  rescheduleTargetKey.value = null
  rescheduleValue.value = ''
}

/**
 * Persist the new slot of a planned SMS (snapped server-side to the legal window), then reload.
 * @param row - The planned-SMS row being moved.
 * @returns A promise resolved once the new slot is saved.
 */
async function confirmReschedule(row: ForecastRow): Promise<void> {
  const rowId: number | null | undefined = row.sms_queue_id
  if (rowId === null || rowId === undefined || isRescheduling.value || !rescheduleValue.value) return
  isRescheduling.value = true
  try {
    const result: SmsAutoQueueAction = await SmsService.rescheduleAutoQueue(
      rowId,
      new Date(rescheduleValue.value).toISOString(),
    )
    const retained: string = parseApiDate(result.scheduled_at).toLocaleString(LOCALE, {
      dateStyle: 'long',
      timeStyle: 'short',
    })
    toast.success(`Envoi déplacé au ${retained}`)
    closeReschedule()
    await load()
  } catch {
    toast.error('Impossible de déplacer cet envoi (la date doit être dans le futur)')
  } finally {
    isRescheduling.value = false
  }
}

/** Drop key of the « Semaine suivante » chevron: same weekday and time, seven days later. */
const NEXT_WEEK_DROP_KEY: string = 'next-week'

/** Pointer travel before a press on the grip turns into a drag, so a plain click goes through. */
const SMS_DRAG_START_THRESHOLD_PX: number = 4

/** Drop target under the pointer while dragging a planned SMS (day key or next-week), for the highlight. */
const dropTargetKey: Ref<string | null> = ref(null)

/** Whether a planned SMS is being dragged — day bodies then advertise themselves as drop zones. */
const isSmsDragActive: Ref<boolean> = ref(false)

let smsDrag: ForecastSmsDragSession | null = null

/**
 * Whether a viewport point falls inside a rectangle.
 * @param rect - The rectangle.
 * @param clientX - Viewport x.
 * @param clientY - Viewport y.
 * @returns True when the point is inside.
 */
function rectContains(rect: DOMRect, clientX: number, clientY: number): boolean {
  return clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom
}

/**
 * The drop target under the pointer: a day pill's key, the next-week chevron, or null.
 * @param clientX - Viewport x.
 * @param clientY - Viewport y.
 * @returns The drop key, or null away from every target.
 */
function dropKeyAtPointer(clientX: number, clientY: number): string | null {
  const nextButton: HTMLElement | null = document.querySelector('[data-forecast-drop-next]')
  if (nextButton && rectContains(nextButton.getBoundingClientRect(), clientX, clientY)) return NEXT_WEEK_DROP_KEY
  const pills: HTMLElement[] = Array.from(document.querySelectorAll<HTMLElement>('[data-forecast-drop-day]'))
  for (const pill of pills) {
    if (rectContains(pill.getBoundingClientRect(), clientX, clientY)) return pill.getAttribute('data-forecast-drop-day')
  }
  return null
}

/**
 * Arm a drag of a planned SMS row from its grip; the drag starts past the travel threshold.
 * @param event - The native pointerdown event on the grip.
 * @param item - The planned-SMS row the grip belongs to.
 */
function onSmsGripPointerDown(event: PointerEvent, item: ForecastRow): void {
  if (event.button !== 0 || smsDrag) return
  const grip: HTMLElement | null = event.currentTarget instanceof HTMLElement ? event.currentTarget : null
  const rowElement: HTMLElement | null = grip?.closest('[data-forecast-row]') ?? null
  if (!rowElement) return
  event.preventDefault()
  const bounds: DOMRect = rowElement.getBoundingClientRect()
  smsDrag = {
    item,
    rowElement,
    pointerId: event.pointerId,
    startClientX: event.clientX,
    startClientY: event.clientY,
    grabOffsetX: event.clientX - bounds.left,
    grabOffsetY: event.clientY - bounds.top,
    ghost: null,
    isActive: false,
  }
  window.addEventListener('pointermove', onSmsDragMove)
  window.addEventListener('pointerup', onSmsDragUp)
  window.addEventListener('pointercancel', cancelSmsDrag)
  window.addEventListener('keydown', onSmsDragKeydown)
}

/**
 * Lift a ghost copy of the row (same look as the shared drag engine) and lock the page cursor.
 * @param session - The armed drag session.
 */
function beginSmsDrag(session: ForecastSmsDragSession): void {
  session.isActive = true
  isSmsDragActive.value = true
  const bounds: DOMRect = session.rowElement.getBoundingClientRect()
  const clone: HTMLElement = session.rowElement.cloneNode(true) as HTMLElement
  clone.removeAttribute('data-forecast-row')
  const card: HTMLDivElement = document.createElement('div')
  card.className = 'drag-reorder-ghost__card drag-reorder-ghost__card--card'
  // Same rounding as the shared engine's card frame (`CARD_FRAME_BORDER_RADIUS`) — the row is square.
  card.style.borderRadius = '0.75rem'
  card.appendChild(clone)
  const ghost: HTMLDivElement = document.createElement('div')
  ghost.className = 'drag-reorder-ghost'
  ghost.style.width = `${bounds.width}px`
  ghost.appendChild(card)
  document.body.appendChild(ghost)
  document.body.classList.add('is-drag-reordering')
  session.ghost = ghost
}

/**
 * Follow the pointer: start the drag past the threshold, move the ghost, highlight the target.
 * @param event - The native pointermove event.
 */
function onSmsDragMove(event: PointerEvent): void {
  const session: ForecastSmsDragSession | null = smsDrag
  if (!session || event.pointerId !== session.pointerId) return
  if (!session.isActive) {
    const travel: number = Math.hypot(event.clientX - session.startClientX, event.clientY - session.startClientY)
    if (travel < SMS_DRAG_START_THRESHOLD_PX) return
    beginSmsDrag(session)
  }
  if (session.ghost) {
    session.ghost.style.transform = `translate3d(${event.clientX - session.grabOffsetX}px, ${event.clientY - session.grabOffsetY}px, 0)`
  }
  const target: string | null = dropKeyAtPointer(event.clientX, event.clientY)
  // The row's own day is a no-op drop: don't advertise it as a target.
  dropTargetKey.value = target === dateKey(parseApiDate(session.item.scheduled_at)) ? null : target
}

/**
 * Release: reschedule onto the dropped day (same time of day) or +7 days on « Semaine suivante ».
 * @param event - The native pointerup event.
 * @returns A promise resolved once the reschedule (if any) is persisted.
 */
async function onSmsDragUp(event: PointerEvent): Promise<void> {
  const session: ForecastSmsDragSession | null = smsDrag
  if (!session || event.pointerId !== session.pointerId) return
  const target: string | null = session.isActive ? dropTargetKey.value : null
  const item: CampaignForecastItem = session.item
  teardownSmsDrag()
  const rowId: number | null | undefined = item.sms_queue_id
  if (!target || rowId === null || rowId === undefined) return
  const current: Date = parseApiDate(item.scheduled_at)
  const moved: Date = new Date(current)
  if (target === NEXT_WEEK_DROP_KEY) {
    moved.setDate(moved.getDate() + 7)
  } else {
    if (target === dateKey(current)) return
    const parts: number[] = target.split('-').map(Number)
    moved.setFullYear(
      parts[0] ?? current.getFullYear(),
      (parts[1] ?? current.getMonth() + 1) - 1,
      parts[2] ?? current.getDate(),
    )
  }
  try {
    const result: SmsAutoQueueAction = await SmsService.rescheduleAutoQueue(rowId, moved.toISOString())
    const retained: string = parseApiDate(result.scheduled_at).toLocaleString(LOCALE, {
      dateStyle: 'long',
      timeStyle: 'short',
    })
    toast.success(`Envoi déplacé au ${retained}`)
    await load()
  } catch {
    toast.error('Impossible de déplacer cet envoi (la date doit être dans le futur)')
  }
}

/**
 * Escape cancels the drag in progress.
 * @param event - The native keydown event.
 */
function onSmsDragKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') cancelSmsDrag()
}

/** Abort the drag (Escape, pointer cancel, unmount) without rescheduling anything. */
function cancelSmsDrag(): void {
  teardownSmsDrag()
}

/** Remove the ghost and the listeners, and clear the target highlight. */
function teardownSmsDrag(): void {
  const session: ForecastSmsDragSession | null = smsDrag
  smsDrag = null
  dropTargetKey.value = null
  isSmsDragActive.value = false
  document.body.classList.remove('is-drag-reordering')
  session?.ghost?.remove()
  window.removeEventListener('pointermove', onSmsDragMove)
  window.removeEventListener('pointerup', onSmsDragUp)
  window.removeEventListener('pointercancel', cancelSmsDrag)
  window.removeEventListener('keydown', onSmsDragKeydown)
}

onMounted((): void => {
  void load()
})

onUnmounted((): void => {
  cancelSmsDrag()
})
</script>
