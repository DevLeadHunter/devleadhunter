import type { SiteContentOpeningHours } from '@devleadhunter/website-content'
import type {
  OpeningRangeDays,
  OpeningTimeRange,
  SchemaOrgDayOfWeek,
  SchemaOrgOpeningHoursSpecification,
} from '~/types/SiteStructuredData'
import { TextFoldUtils } from '~/utils/TextFoldUtils'

const WEEK: SchemaOrgDayOfWeek[] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const DAY_BY_PREFIX: Record<string, SchemaOrgDayOfWeek> = {
  lun: 'Monday',
  mon: 'Monday',
  mar: 'Tuesday',
  tue: 'Tuesday',
  mer: 'Wednesday',
  wed: 'Wednesday',
  jeu: 'Thursday',
  thu: 'Thursday',
  ven: 'Friday',
  fri: 'Friday',
  sam: 'Saturday',
  sat: 'Saturday',
  dim: 'Sunday',
  sun: 'Sunday',
}
const DAY_PREFIX_LENGTH: number = 3
const CLOSED: RegExp = /^(ferme|closed)\b/
const OPEN_ALL_DAY: RegExp = /24\s*h?\s*\/\s*24|24\s*heures|24 hours/
const RANGE_SEPARATOR: RegExp = /\s*[,;]\s*|\s+et\s+|\s+and\s+/
const FOLDED_TIME_RANGE: RegExp =
  /^(\d{1,2})(?:\s*[:h.]\s*(\d{2})?)?\s*(?:–|—|-|a|to)\s*(\d{1,2})(?:\s*[:h.]\s*(\d{2})?)?$/
const MIDNIGHT: string = '00:00'
const END_OF_DAY: string = '23:59'
const LAST_HOUR: number = 23
const HOURS_IN_DAY: number = 24
const LAST_MINUTE: number = 59
const TIME_PART_LENGTH: number = 2

/**
 * The opening hours a site lists (« lundi : 08:00–12:00, 14:00–18:00 ») as schema.org specifications.
 */
export class SchemaOrgOpeningHoursUtils {
  /**
   * One specification per opening range, the days sharing it grouped, a closed or unreadable day left out.
   * @param rows - The site's opening hours, one row per day.
   * @returns The specifications in week order, empty when no day reads.
   */
  static buildSpecifications(rows: SiteContentOpeningHours[]): SchemaOrgOpeningHoursSpecification[] {
    const openingsByRange: Map<string, OpeningRangeDays> = new Map()
    for (const row of rows) {
      const day: SchemaOrgDayOfWeek | null = SchemaOrgOpeningHoursUtils.readDayOfWeek(row.day ?? '')
      if (!day) continue

      for (const range of SchemaOrgOpeningHoursUtils.readTimeRanges(row.hours ?? '')) {
        const rangeKey: string = `${range.opens}-${range.closes}`
        const opening: OpeningRangeDays = openingsByRange.get(rangeKey) ?? { range, days: new Set() }
        opening.days.add(day)
        openingsByRange.set(rangeKey, opening)
      }
    }

    return [...openingsByRange.values()]
      .map(({ range, days }: OpeningRangeDays): SchemaOrgOpeningHoursSpecification => ({
        '@type': 'OpeningHoursSpecification',
        dayOfWeek: WEEK.filter((weekDay: SchemaOrgDayOfWeek): boolean => days.has(weekDay)),
        opens: range.opens,
        closes: range.closes,
      }))
      .sort(
        (first: SchemaOrgOpeningHoursSpecification, second: SchemaOrgOpeningHoursSpecification): number =>
          SchemaOrgOpeningHoursUtils.firstDayIndex(first) - SchemaOrgOpeningHoursUtils.firstDayIndex(second) ||
          first.opens.localeCompare(second.opens),
      )
  }

  /**
   * The day a row names, in French or English (« lundi », « Mon. »).
   * @param label - The row's day.
   * @returns The schema.org day, null when the label names none.
   */
  private static readDayOfWeek(label: string): SchemaOrgDayOfWeek | null {
    return DAY_BY_PREFIX[TextFoldUtils.fold(label).trim().slice(0, DAY_PREFIX_LENGTH)] ?? null
  }

  /**
   * The opening ranges of one day (« 08:00–12:00, 14:00–18:00 », « Ouvert 24h/24 »).
   * @param hours - The day's hours, as the listing words them.
   * @returns The ranges; none for a closed day or a day any part of which does not read.
   */
  private static readTimeRanges(hours: string): OpeningTimeRange[] {
    const folded: string = TextFoldUtils.fold(hours).trim()
    if (!folded || CLOSED.test(folded)) return []
    if (OPEN_ALL_DAY.test(folded)) return [{ opens: MIDNIGHT, closes: END_OF_DAY }]

    const segments: string[] = folded.split(RANGE_SEPARATOR)
    const ranges: OpeningTimeRange[] = segments
      .map((segment: string): OpeningTimeRange | null => SchemaOrgOpeningHoursUtils.readTimeRange(segment))
      .filter((range: OpeningTimeRange | null): range is OpeningTimeRange => range !== null)
    return ranges.length === segments.length ? ranges : []
  }

  /**
   * One folded range (« 08:00–19:00 », « 8h-12h », « 7h30 a 18h »), a closing at midnight read as the day's last minute.
   * @param segment - The folded range.
   * @returns The range in `HH:MM`, null when it does not read as two valid times.
   */
  private static readTimeRange(segment: string): OpeningTimeRange | null {
    const match: RegExpMatchArray | null = segment.trim().match(FOLDED_TIME_RANGE)
    if (!match) return null

    const opens: string | null = SchemaOrgOpeningHoursUtils.formatTime(match[1], match[2], LAST_HOUR)
    const closes: string | null = SchemaOrgOpeningHoursUtils.formatTime(match[3], match[4], HOURS_IN_DAY)
    if (!opens || !closes) return null

    const isMidnightClose: boolean = closes === MIDNIGHT || closes === `${HOURS_IN_DAY}:00`
    return { opens, closes: isMidnightClose ? END_OF_DAY : closes }
  }

  /**
   * A time in `HH:MM`.
   * @param hour - The hour digits.
   * @param minute - The minute digits, absent for a round hour.
   * @param maximumHour - The latest hour allowed.
   * @returns The time, null when out of range.
   */
  private static formatTime(hour: string | undefined, minute: string | undefined, maximumHour: number): string | null {
    const hourValue: number = Number(hour)
    const minuteValue: number = Number(minute ?? '0')
    if (!Number.isInteger(hourValue) || hourValue > maximumHour || minuteValue > LAST_MINUTE) return null
    if (hourValue === HOURS_IN_DAY && minuteValue > 0) return null

    const hourPart: string = String(hourValue).padStart(TIME_PART_LENGTH, '0')
    const minutePart: string = String(minuteValue).padStart(TIME_PART_LENGTH, '0')
    return `${hourPart}:${minutePart}`
  }

  /**
   * Where a specification's first day falls in the week.
   * @param specification - The specification.
   * @returns The index of its first day.
   */
  private static firstDayIndex(specification: SchemaOrgOpeningHoursSpecification): number {
    return WEEK.indexOf(specification.dayOfWeek[0] ?? 'Monday')
  }
}
