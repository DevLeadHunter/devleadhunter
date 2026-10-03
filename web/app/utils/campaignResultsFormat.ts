const LOCALE: string = 'fr-FR'
const FRENCH_PLURAL_FROM: number = 2
const SECONDS_PER_MINUTE: number = 60
const MINUTES_PER_HOUR: number = 60
const MINUTES_PER_DAY: number = 1440
const CENTS_PER_UNIT: number = 100
const FULL_PERCENT: number = 100

/** French wording of the numbers, durations and dates of a campaign's results. */
export class CampaignResultsFormat {
  private constructor() {}

  /**
   * A count with its noun, singular up to one as French wants it: « 0 réponse », « 1 réponse », « 3 réponses ».
   * @param value - The count.
   * @param singular - The noun for zero or one.
   * @param plural - The noun from two, the singular plus « s » when omitted.
   * @returns The count followed by its noun.
   */
  static count(value: number, singular: string, plural: string = `${singular}s`): string {
    return `${value} ${CampaignResultsFormat.agreeWithCount(value, singular, plural)}`
  }

  /**
   * The word that agrees with a count, singular up to one: « encaissé » for 0 €, « encaissés » for 500 €.
   * @param value - The count.
   * @param singular - The word for zero or one.
   * @param plural - The word from two, the singular plus « s » when omitted.
   * @returns The agreeing word.
   */
  static agreeWithCount(value: number, singular: string, plural: string = `${singular}s`): string {
    return value >= FRENCH_PLURAL_FROM ? plural : singular
  }

  /**
   * Rounded share of a part, in percent.
   * @param part - The counted part.
   * @param total - The whole, zero giving 0.
   * @returns The whole percentage.
   */
  static percent(part: number, total: number): number {
    return total > 0 ? CampaignResultsFormat.wholePercent(part / total) : 0
  }

  /**
   * A rate in whole percent: 0.237 gives 24.
   * @param rate - The rate, 1 for the whole.
   * @returns The rounded percentage.
   */
  static wholePercent(rate: number): number {
    return Math.round(rate * FULL_PERCENT)
  }

  /**
   * Time a page stayed in front of a visitor: « 40 s », « 2 min 05 ».
   * @param seconds - Active seconds.
   * @returns The duration label.
   */
  static activeTime(seconds: number): string {
    if (seconds < SECONDS_PER_MINUTE) return `${seconds} s`
    const minutes: number = Math.floor(seconds / SECONDS_PER_MINUTE)
    const remainingSeconds: number = seconds % SECONDS_PER_MINUTE
    return `${minutes} min ${String(remainingSeconds).padStart(2, '0')}`
  }

  /**
   * Time between two events: « 25 min », « 2 h 05 », « 3 j 4 h ».
   * @param minutes - Elapsed minutes.
   * @returns The delay label.
   */
  static delay(minutes: number): string {
    if (minutes < MINUTES_PER_HOUR) return `${minutes} min`
    if (minutes < MINUTES_PER_DAY) {
      const hours: number = Math.floor(minutes / MINUTES_PER_HOUR)
      const remainingMinutes: number = minutes % MINUTES_PER_HOUR
      if (remainingMinutes === 0) return `${hours} h`
      return `${hours} h ${String(remainingMinutes).padStart(2, '0')}`
    }
    const days: number = Math.floor(minutes / MINUTES_PER_DAY)
    const remainingHours: number = Math.round((minutes % MINUTES_PER_DAY) / MINUTES_PER_HOUR)
    if (remainingHours === 0) return `${days} j`
    return `${days} j ${remainingHours} h`
  }

  /**
   * Day of the month, with the French ordinal for the first: « 22 », « 1er ».
   * @param date - The day.
   * @returns The day label.
   */
  static dayOfMonth(date: Date): string {
    return date.getDate() === 1 ? '1er' : String(date.getDate())
  }

  /**
   * Day and abbreviated month: « 22 sept. », « 1er oct. ».
   * @param date - The day.
   * @returns The day label.
   */
  static shortDay(date: Date): string {
    return `${CampaignResultsFormat.dayOfMonth(date)} ${date.toLocaleDateString(LOCALE, { month: 'short' })}`
  }

  /**
   * Abbreviated weekday, day and month: « mar. 22 sept. ».
   * @param date - The day.
   * @returns The day label.
   */
  static shortWeekday(date: Date): string {
    return `${date.toLocaleDateString(LOCALE, { weekday: 'short' })} ${CampaignResultsFormat.shortDay(date)}`
  }

  /**
   * Day and month in full: « 1er octobre ».
   * @param date - The day.
   * @returns The day label.
   */
  static dayAndMonth(date: Date): string {
    return `${CampaignResultsFormat.dayOfMonth(date)} ${date.toLocaleDateString(LOCALE, { month: 'long' })}`
  }

  /**
   * Weekday, day and month in full: « jeudi 1er octobre ».
   * @param date - The day.
   * @returns The day label.
   */
  static longDay(date: Date): string {
    return `${date.toLocaleDateString(LOCALE, { weekday: 'long' })} ${CampaignResultsFormat.dayAndMonth(date)}`
  }

  /**
   * Day and month in digits: « 24/09 ».
   * @param date - The day.
   * @returns The day label.
   */
  static numericDay(date: Date): string {
    return date.toLocaleDateString(LOCALE, { day: '2-digit', month: '2-digit' })
  }

  /**
   * Clock time: « 11:30 ».
   * @param date - The moment.
   * @returns The time label.
   */
  static clock(date: Date): string {
    return date.toLocaleTimeString(LOCALE, { hour: '2-digit', minute: '2-digit' })
  }

  /**
   * Clock time written out, as in a sentence: « 11 h 05 ».
   * @param date - The moment.
   * @returns The time label.
   */
  static spokenClock(date: Date): string {
    return `${date.getHours()} h ${String(date.getMinutes()).padStart(2, '0')}`
  }

  /**
   * Amount of money in its currency, without cents when there are none: « 500 € », « 450 CHF ».
   * @param cents - Amount in cents.
   * @param currency - ISO currency code, euros when unknown.
   * @returns The amount label.
   */
  static money(cents: number, currency: string | null): string {
    const hasCents: boolean = cents % CENTS_PER_UNIT !== 0
    return new Intl.NumberFormat(LOCALE, {
      style: 'currency',
      currency: currency ?? 'EUR',
      maximumFractionDigits: hasCents ? 2 : 0,
    }).format(CampaignResultsFormat.unitsFromCents(cents))
  }

  /**
   * An amount in cents expressed in its currency's units: 45000 gives 450.
   * @param cents - Amount in cents.
   * @returns The amount in units.
   */
  static unitsFromCents(cents: number): number {
    return cents / CENTS_PER_UNIT
  }

  /**
   * Names joined the French way: « A », « A et B », « A, B et C ».
   * @param names - The names, in reading order.
   * @returns The joined names.
   */
  static nameList(names: string[]): string {
    if (names.length <= 1) return names[0] ?? ''
    return `${names.slice(0, -1).join(', ')} et ${names[names.length - 1]}`
  }

  /**
   * Text with an upper-case first letter.
   * @param text - The text.
   * @returns The capitalised text.
   */
  static capitalize(text: string): string {
    return text.charAt(0).toLocaleUpperCase(LOCALE) + text.slice(1)
  }

  /**
   * A label put inside a sentence: only its first letter lowered, so « Premier SMS » reads « premier SMS ».
   * @param text - The label.
   * @returns The label with a lowercase first letter.
   */
  static lowercaseFirst(text: string): string {
    return text.charAt(0).toLocaleLowerCase(LOCALE) + text.slice(1)
  }
}
