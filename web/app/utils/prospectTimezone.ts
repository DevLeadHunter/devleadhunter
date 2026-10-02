import type { ProspectLocalTime } from '~/types/ProspectTimezone'
import { parseApiDate } from '~/utils/date'

const LOCALE: string = 'fr-FR'

/**
 * The prospect's clock for a scheduled send, shown next to the viewer's.
 *
 * The API evaluates every send window in the prospect's timezone (`prospect_timezone`, an IANA
 * name read from its country) and serialises the instant as naive UTC. The dashboard renders it
 * in the viewer's clock; this class adds « 08:00 à Montréal » when the prospect reads another one.
 */
export class ProspectTimezone {
  private constructor() {}

  /** The city a prospect reads its clock in, per IANA zone — the Québec prospects live on the Toronto zone. */
  private static readonly CITY_BY_TIMEZONE: Record<string, string> = {
    'Europe/Paris': 'Paris',
    'Europe/Zurich': 'Zurich',
    'Europe/Brussels': 'Bruxelles',
    'Europe/Luxembourg': 'Luxembourg',
    'America/Toronto': 'Montréal',
  }

  /**
   * The viewer's IANA timezone, as the browser resolves it.
   * @returns The zone name, e.g. `Europe/Paris`.
   */
  static viewerTimezone(): string {
    return Intl.DateTimeFormat().resolvedOptions().timeZone
  }

  /**
   * A readable city for an IANA zone: the known label, else the zone's last segment (`America/New_York` → `New York`).
   * @param timezoneName - IANA zone name.
   * @returns The city label.
   */
  static cityLabel(timezoneName: string): string {
    const known: string | undefined = ProspectTimezone.CITY_BY_TIMEZONE[timezoneName]
    if (known) return known
    const lastSegment: string = timezoneName.split('/').pop() ?? timezoneName
    return lastSegment.replace(/_/g, ' ')
  }

  /**
   * The prospect's wall-clock time of a send, only when it differs from the viewer's.
   * @param scheduledAt - The send instant as the API serialises it (naive UTC).
   * @param timezoneName - The prospect's IANA zone, absent on rows without one.
   * @returns The local time and its city, or `null` when both clocks read the same (same zone, or zones sharing the offset).
   */
  static localTime(scheduledAt: string, timezoneName: string | null | undefined): ProspectLocalTime | null {
    if (!timezoneName) return null
    const viewerTimezone: string = ProspectTimezone.viewerTimezone()
    if (timezoneName === viewerTimezone) return null
    const moment: Date = parseApiDate(scheduledAt)
    const prospectTime: string | null = ProspectTimezone.formatWallClockTime(moment, timezoneName)
    const viewerTime: string | null = ProspectTimezone.formatWallClockTime(moment, viewerTimezone)
    if (prospectTime === null || prospectTime === viewerTime) return null
    return { time: prospectTime, city: ProspectTimezone.cityLabel(timezoneName) }
  }

  /**
   * « 08:00 à Montréal », or `null` when the prospect reads the same clock as the viewer.
   * @param scheduledAt - The send instant as the API serialises it (naive UTC).
   * @param timezoneName - The prospect's IANA zone, absent on rows without one.
   * @returns The label, or `null`.
   */
  static localTimeLabel(scheduledAt: string, timezoneName: string | null | undefined): string | null {
    const localTime: ProspectLocalTime | null = ProspectTimezone.localTime(scheduledAt, timezoneName)
    return localTime ? `${localTime.time} à ${localTime.city}` : null
  }

  /**
   * `HH:mm` of an instant on a zone's clock.
   * @param moment - The instant.
   * @param timezoneName - IANA zone name.
   * @returns The time, or `null` when the browser does not know the zone.
   */
  private static formatWallClockTime(moment: Date, timezoneName: string): string | null {
    try {
      return moment.toLocaleTimeString(LOCALE, { hour: '2-digit', minute: '2-digit', timeZone: timezoneName })
    } catch {
      return null
    }
  }
}
