import type { ScheduleSendPreset } from '~/types/UiScheduleSendControls'
import { formatScheduledMoment } from '~/utils/date'

const MORNING_HOUR: number = 9
const LATE_MORNING_HOUR: number = 11
const MONDAY: number = 1
/** Before this hour the « next morning » is today's: planning at 1 a.m. targets the coming morning. */
const NIGHT_END_HOUR: number = 6

/** One-click send times for the « Programmer l'envoi » panel. */
export class ScheduleSendPresets {
  /**
   * The presets offered at a given moment: next morning 9:00 and 11:00, then Monday 9:00 when it is another day.
   * @param now - The current time.
   * @returns The presets, earliest first, all in the future.
   */
  static build(now: Date): ScheduleSendPreset[] {
    const nextMorning: Date = new Date(now)
    nextMorning.setHours(0, 0, 0, 0)
    if (now.getHours() >= NIGHT_END_HOUR) nextMorning.setDate(nextMorning.getDate() + 1)

    const nextMonday: Date = new Date(nextMorning)
    while (nextMonday.getDay() !== MONDAY) nextMonday.setDate(nextMonday.getDate() + 1)

    const moments: Date[] = [
      ScheduleSendPresets.atHour(nextMorning, MORNING_HOUR),
      ScheduleSendPresets.atHour(nextMorning, LATE_MORNING_HOUR),
    ]
    if (nextMonday.getTime() !== nextMorning.getTime())
      moments.push(ScheduleSendPresets.atHour(nextMonday, MORNING_HOUR))

    return moments
      .filter((moment: Date): boolean => moment.getTime() > now.getTime())
      .map(
        (moment: Date): ScheduleSendPreset => ({
          key: moment.toISOString(),
          label: ScheduleSendPresets.capitalize(formatScheduledMoment(moment)),
          moment,
        }),
      )
  }

  /**
   * A copy of a day at a given hour.
   * @param day - The day (its time is ignored).
   * @param hour - The hour, local time.
   * @returns The new date.
   */
  private static atHour(day: Date, hour: number): Date {
    const moment: Date = new Date(day)
    moment.setHours(hour, 0, 0, 0)
    return moment
  }

  /**
   * Upper-case the first letter.
   * @param text - The text.
   * @returns The text with a capital first letter.
   */
  private static capitalize(text: string): string {
    return text.charAt(0).toUpperCase() + text.slice(1)
  }
}
