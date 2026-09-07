<template>
  <div ref="rootEl" class="relative">
    <button
      type="button"
      class="app-btn-secondary h-9 px-4 text-xs whitespace-nowrap"
      :aria-expanded="isOpen"
      aria-haspopup="dialog"
      @click="toggle"
    >
      <UIcon name="i-lucide-calendar" class="h-3.5 w-3.5" />
      <span>{{ triggerLabel }}</span>
      <UIcon
        name="i-lucide-chevron-down"
        :class="['h-3 w-3 opacity-60 transition-transform', isOpen && 'rotate-180']"
      />
    </button>

    <div
      v-if="isOpen"
      class="absolute right-0 z-50 mt-1.5 w-72 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-1.5 shadow-[var(--app-shadow-soft)]"
      role="dialog"
      aria-label="Choisir une période"
    >
      <!-- presets -->
      <button
        v-for="preset in PRESETS"
        :key="preset.key"
        type="button"
        class="flex w-full cursor-pointer items-center justify-between rounded-lg px-2.5 py-2 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
        @click="selectPreset(preset.key)"
      >
        {{ preset.label }}
        <UIcon
          v-if="modelValue.preset === preset.key"
          name="i-lucide-check"
          class="h-3.5 w-3.5 text-[var(--app-accent-ink)]"
        />
      </button>

      <button
        type="button"
        class="flex w-full cursor-pointer items-center justify-between rounded-lg px-2.5 py-2 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
        :class="showCalendar && 'bg-[var(--app-surface-2)]'"
        @click="showCalendar = !showCalendar"
      >
        Plage personnalisée…
        <UIcon
          name="i-lucide-chevron-down"
          :class="['h-3.5 w-3.5 opacity-60 transition-transform', showCalendar && 'rotate-180']"
        />
      </button>

      <!-- calendrier -->
      <div v-if="showCalendar" class="mt-1 border-t border-[var(--app-line-soft)] px-1 pt-2">
        <div class="mb-2 flex items-center justify-between">
          <button
            type="button"
            class="cursor-pointer rounded-md p-1 text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            aria-label="Mois précédent"
            @click="shiftMonth(-1)"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>
          <span class="text-sm font-semibold text-[var(--app-ink)]">{{ monthTitle }}</span>
          <button
            type="button"
            class="cursor-pointer rounded-md p-1 text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            aria-label="Mois suivant"
            @click="shiftMonth(1)"
          >
            <UIcon name="i-lucide-chevron-right" class="h-4 w-4" />
          </button>
        </div>

        <div class="grid grid-cols-7 gap-0.5">
          <span
            v-for="dow in WEEKDAYS"
            :key="dow"
            class="font-label py-1 text-center text-[0.5rem] text-[var(--app-faint)]"
          >
            {{ dow }}
          </span>
          <span v-for="blank in leadingBlanks" :key="`b-${blank}`" aria-hidden="true"></span>
          <button v-for="day in daysInMonth" :key="day" type="button" :class="dayClass(day)" @click="pickDay(day)">
            {{ day }}
          </button>
        </div>

        <div class="mt-2 flex items-center justify-between gap-2">
          <button
            type="button"
            class="cursor-pointer text-xs text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
            @click="clearRange"
          >
            Effacer
          </button>
          <span class="truncate text-[0.7rem] text-[var(--app-ink-soft)]">{{ rangeHint }}</span>
          <button
            type="button"
            class="app-btn-primary h-7 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!draftStart || !draftEnd"
            @click="applyRange"
          >
            Appliquer
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, ModelRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import type { PeriodPreset, PeriodValue } from '~/types/UiPeriodFilter'

const modelValue: ModelRef<PeriodValue> = defineModel<PeriodValue>({ required: true })

/** Presets offered above the custom-range calendar. */
const PRESETS: { key: PeriodPreset; label: string }[] = [
  { key: 'all', label: 'Toute période' },
  { key: 'week', label: 'Cette semaine' },
  { key: 'month', label: 'Ce mois-ci' },
  { key: '30d', label: '30 derniers jours' },
]

const MONTHS_FULL: string[] = [
  'Janvier',
  'Février',
  'Mars',
  'Avril',
  'Mai',
  'Juin',
  'Juillet',
  'Août',
  'Septembre',
  'Octobre',
  'Novembre',
  'Décembre',
]
const MONTHS_SHORT: string[] = [
  'janv.',
  'févr.',
  'mars',
  'avr.',
  'mai',
  'juin',
  'juil.',
  'août',
  'sept.',
  'oct.',
  'nov.',
  'déc.',
]
const WEEKDAYS: string[] = ['lun', 'mar', 'mer', 'jeu', 'ven', 'sam', 'dim']

/** Root element — closes the popover when a click lands outside it. */
const rootEl: Ref<HTMLElement | null> = ref(null)

/** Whether the popover is open. */
const isOpen: Ref<boolean> = ref(false)

/** Whether the custom-range calendar section is expanded. */
const showCalendar: Ref<boolean> = ref(false)

/** First day of the month the calendar currently shows. */
const cursor: Ref<Date> = ref(startOfMonth(new Date()))

/** In-progress range selection (committed only on « Appliquer »). */
const draftStart: Ref<Date | null> = ref(null)
const draftEnd: Ref<Date | null> = ref(null)

/** Label shown on the trigger button for the active selection. */
const triggerLabel: ComputedRef<string> = computed((): string => {
  if (modelValue.value.preset === 'custom' && modelValue.value.start && modelValue.value.end) {
    return formatRange(parseIso(modelValue.value.start), parseIso(modelValue.value.end))
  }
  const preset: { key: PeriodPreset; label: string } | undefined = PRESETS.find(
    (p: { key: PeriodPreset; label: string }): boolean => p.key === modelValue.value.preset,
  )
  return preset?.label ?? 'Toute période'
})

/** Full month + year heading of the calendar (e.g. « Août 2026 »). */
const monthTitle: ComputedRef<string> = computed(
  (): string => `${MONTHS_FULL[cursor.value.getMonth()]} ${cursor.value.getFullYear()}`,
)

/** Number of empty leading cells before day 1 (Monday-first grid). */
const leadingBlanks: ComputedRef<number> = computed((): number => {
  const first: Date = startOfMonth(cursor.value)
  return (first.getDay() + 6) % 7
})

/** Number of days in the displayed month. */
const daysInMonth: ComputedRef<number> = computed((): number =>
  new Date(cursor.value.getFullYear(), cursor.value.getMonth() + 1, 0).getDate(),
)

/** Hint under the calendar: prompts the next click, then shows the picked range. */
const rangeHint: ComputedRef<string> = computed((): string => {
  if (!draftStart.value) return 'Date de début'
  if (!draftEnd.value) return 'Date de fin'
  return formatRange(draftStart.value, draftEnd.value)
})

onClickOutside(rootEl, (): void => {
  isOpen.value = false
})

/**
 * Return the first day of the month containing `date` (time zeroed).
 * @param date - Any date.
 * @returns Midnight on the first of that month.
 */
function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

/**
 * Parse a `YYYY-MM-DD` string into a local `Date` at midnight.
 * @param iso - Local date string.
 * @returns The matching `Date`.
 */
function parseIso(iso: string): Date {
  const parts: string[] = iso.split('-')
  return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]))
}

/**
 * Serialize a `Date` as a `YYYY-MM-DD` local string.
 * @param date - The date to serialize.
 * @returns The `YYYY-MM-DD` string.
 */
function toIso(date: Date): string {
  const month: string = String(date.getMonth() + 1).padStart(2, '0')
  const day: string = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

/**
 * Whether two dates fall on the same calendar day.
 * @param a - First date (nullable).
 * @param b - Second date (nullable).
 * @returns True when both are set and share the same day.
 */
function isSameDay(a: Date | null, b: Date | null): boolean {
  return (
    !!a && !!b && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
  )
}

/**
 * Human-readable range label (e.g. « 3 – 12 août » or « 28 juil. – 5 août »).
 * @param start - Range start.
 * @param end - Range end.
 * @returns The formatted range.
 */
function formatRange(start: Date, end: Date): string {
  if (start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear()) {
    return `${start.getDate()} – ${end.getDate()} ${MONTHS_SHORT[end.getMonth()]}`
  }
  return `${start.getDate()} ${MONTHS_SHORT[start.getMonth()]} – ${end.getDate()} ${MONTHS_SHORT[end.getMonth()]}`
}

/**
 * Open or close the popover, seeding the calendar from the current selection.
 */
function toggle(): void {
  isOpen.value = !isOpen.value
  if (!isOpen.value) return
  if (modelValue.value.preset === 'custom' && modelValue.value.start && modelValue.value.end) {
    draftStart.value = parseIso(modelValue.value.start)
    draftEnd.value = parseIso(modelValue.value.end)
    cursor.value = startOfMonth(draftStart.value)
    showCalendar.value = true
  } else {
    draftStart.value = null
    draftEnd.value = null
    cursor.value = startOfMonth(new Date())
    showCalendar.value = false
  }
}

/**
 * Apply a preset period and close the popover.
 * @param preset - The chosen preset.
 */
function selectPreset(preset: PeriodPreset): void {
  modelValue.value = { preset, start: null, end: null }
  isOpen.value = false
}

/**
 * Move the calendar by a number of months.
 * @param delta - Months to add (negative to go back).
 */
function shiftMonth(delta: number): void {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1)
}

/**
 * Resolve the classes of a calendar day cell.
 * @param day - Day number in the displayed month.
 * @returns The Tailwind class string.
 */
function dayClass(day: number): string {
  const date: Date = new Date(cursor.value.getFullYear(), cursor.value.getMonth(), day)
  const base: string = 'aspect-square cursor-pointer text-xs tabular-nums transition-colors'
  const isStart: boolean = isSameDay(date, draftStart.value)
  const isEnd: boolean = isSameDay(date, draftEnd.value)
  const isEdge: boolean = isStart || isEnd
  const inRange: boolean = !!draftStart.value && !!draftEnd.value && date > draftStart.value && date < draftEnd.value
  const isToday: boolean = isSameDay(date, new Date())

  if (isEdge) return `${base} rounded-md bg-[var(--app-btn-bg)] font-semibold text-[var(--app-btn-text)]`
  if (inRange) return `${base} bg-[var(--app-accent-soft)] text-[var(--app-ink)]`
  const ring: string = isToday ? ' ring-1 ring-inset ring-[var(--app-line)]' : ''
  return `${base} rounded-md text-[var(--app-ink)] hover:bg-[var(--app-surface-2)]${ring}`
}

/**
 * Handle a day click: start a new range, or close the open one.
 * @param day - Day number in the displayed month.
 */
function pickDay(day: number): void {
  const date: Date = new Date(cursor.value.getFullYear(), cursor.value.getMonth(), day)
  if (!draftStart.value || (draftStart.value && draftEnd.value)) {
    draftStart.value = date
    draftEnd.value = null
  } else if (date < draftStart.value) {
    draftEnd.value = draftStart.value
    draftStart.value = date
  } else {
    draftEnd.value = date
  }
}

/**
 * Clear the in-progress range.
 */
function clearRange(): void {
  draftStart.value = null
  draftEnd.value = null
}

/**
 * Commit the drafted custom range and close the popover.
 */
function applyRange(): void {
  if (!draftStart.value || !draftEnd.value) return
  modelValue.value = { preset: 'custom', start: toIso(draftStart.value), end: toIso(draftEnd.value) }
  isOpen.value = false
}
</script>
