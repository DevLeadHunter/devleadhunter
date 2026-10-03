import type {
  CampaignBenchmark,
  CampaignResultsComparison,
  CampaignResultsDay,
  CampaignResultsFilterKey,
  CampaignResultsPlannedSend,
  CampaignResultsProspect,
  CampaignResultsProspectState,
  CampaignResultsReply,
  CampaignResultsResponse,
  CampaignResultsRow,
  CampaignResultsSend,
  CampaignResultsSortDirection,
  CampaignResultsSortKey,
  CampaignResultsStage,
  CampaignResultsStateGroup,
  CampaignResultsStepSummary,
  CampaignResultsTradeGroup,
  CampaignResultsVisit,
  CampaignResultsVisitMarks,
} from '~/types/CampaignResults'
import type { UiUnitChartUnit } from '~/types/UiUnitChart'
import {
  CAMPAIGN_RESULTS_STATE_LABELS,
  CAMPAIGN_RESULTS_STATE_ORDER,
  CAMPAIGN_RESULTS_STATE_TONES,
} from '~/constants/campaignResults'
import { CampaignResultsFormat } from '~/utils/campaignResultsFormat'
import { parseApiDate } from '~/utils/date'

const EVENING_HOUR: number = 18
const MAX_TIMELINE_DAYS: number = 366
const SUNDAY_INDEX: number = 0
const SATURDAY_INDEX: number = 6
const MILLISECONDS_PER_MINUTE: number = 60_000
const MINUTES_PER_HOUR: number = 60
const ACCENT_MARKS_PATTERN: RegExp = /[\u0300-\u036f]/g
const QUIET_STATES: CampaignResultsProspectState[] = ['silent', 'pending', 'not_sent']

/** Derives the day series, prospect rows and breakdowns of a campaign's « Résultats » tab from its API payload. */
export class CampaignResults {
  private constructor() {}

  /**
   * Calendar day of a moment in the viewer's timezone, sortable as text.
   * @param moment - The moment.
   * @returns The `YYYY-MM-DD` key.
   */
  static dayKey(moment: Date): string {
    const month: string = String(moment.getMonth() + 1).padStart(2, '0')
    const day: string = String(moment.getDate()).padStart(2, '0')
    return `${moment.getFullYear()}-${month}-${day}`
  }

  /**
   * Every day from the campaign's first event to its last (sends, planned ones included, visits and replies), with its counts.
   * @param results - The campaign's results.
   * @param now - The current moment, which splits past days from the days to come.
   * @returns The days in order, empty when nothing happened or is planned.
   */
  static buildDays(results: CampaignResultsResponse, now: Date): CampaignResultsDay[] {
    const moments: Date[] = [
      ...results.prospects.flatMap((prospect: CampaignResultsProspect): Date[] => [
        ...prospect.sends.map((send: CampaignResultsSend): Date => parseApiDate(send.at)),
        ...prospect.visits.map((visit: CampaignResultsVisit): Date => parseApiDate(visit.started_at)),
      ]),
      ...results.replies.map((reply: CampaignResultsReply): Date => parseApiDate(reply.received_at)),
    ]
    if (moments.length === 0) return []
    const times: number[] = moments.map((moment: Date): number => moment.getTime())
    const cursor: Date = new Date(Math.min(...times))
    cursor.setHours(0, 0, 0, 0)
    const lastKey: string = CampaignResults.dayKey(new Date(Math.max(...times)))
    const todayKey: string = CampaignResults.dayKey(now)
    const days: CampaignResultsDay[] = []
    while (days.length < MAX_TIMELINE_DAYS) {
      const key: string = CampaignResults.dayKey(cursor)
      days.push({
        key,
        date: new Date(cursor),
        isWeekend: cursor.getDay() === SUNDAY_INDEX || cursor.getDay() === SATURDAY_INDEX,
        isToday: key === todayKey,
        isFuture: key > todayKey,
        visits: 0,
        newVisitors: 0,
        firstMails: 0,
        followUps: 0,
        plannedFirstMails: 0,
        plannedFollowUps: 0,
        replies: [],
      })
      if (key >= lastKey) break
      cursor.setDate(cursor.getDate() + 1)
    }
    const dayByKey: Map<string, CampaignResultsDay> = new Map(
      days.map((day: CampaignResultsDay): [string, CampaignResultsDay] => [day.key, day]),
    )
    const dayOf: (iso: string) => CampaignResultsDay | undefined = (iso: string): CampaignResultsDay | undefined =>
      dayByKey.get(CampaignResults.dayKey(parseApiDate(iso)))
    for (const prospect of results.prospects) {
      for (const send of prospect.sends) {
        const day: CampaignResultsDay | undefined = dayOf(send.at)
        if (!day) continue
        if (send.status === 'sent' && send.step === 0) day.firstMails += 1
        else if (send.status === 'sent') day.followUps += 1
        else if (send.status === 'planned' && send.step === 0) day.plannedFirstMails += 1
        else if (send.status === 'planned') day.plannedFollowUps += 1
      }
      prospect.visits.forEach((visit: CampaignResultsVisit, index: number): void => {
        const day: CampaignResultsDay | undefined = dayOf(visit.started_at)
        if (!day) return
        day.visits += 1
        if (index === 0) day.newVisitors += 1
      })
    }
    for (const reply of results.replies) dayOf(reply.received_at)?.replies.push(reply)
    return days
  }

  /**
   * One row per prospect of the campaign, with its replies and visit totals.
   * @param results - The campaign's results.
   * @returns The rows, in the API's order.
   */
  static buildRows(results: CampaignResultsResponse): CampaignResultsRow[] {
    return results.prospects.map((prospect: CampaignResultsProspect): CampaignResultsRow => {
      const firstMail: CampaignResultsSend | undefined = prospect.sends.find(
        (send: CampaignResultsSend): boolean => send.step === 0 && send.status === 'sent',
      )
      const lastVisit: CampaignResultsVisit | undefined = prospect.visits[prospect.visits.length - 1]
      return {
        prospect,
        replies: results.replies.filter((reply: CampaignResultsReply): boolean => reply.prospect_id === prospect.id),
        visitCount: prospect.visits.length,
        activeSeconds: prospect.visits.reduce(
          (total: number, visit: CampaignResultsVisit): number => total + visit.active_seconds,
          0,
        ),
        firstMailAt: firstMail ? parseApiDate(firstMail.at) : null,
        lastVisitAt: lastVisit ? parseApiDate(lastVisit.started_at) : null,
      }
    })
  }

  /**
   * Rank of a state, the furthest stage first.
   * @param state - The prospect state.
   * @returns Its position in the state order.
   */
  static stateRank(state: CampaignResultsProspectState): number {
    return CAMPAIGN_RESULTS_STATE_ORDER.indexOf(state)
  }

  /**
   * Prospects grouped by state, furthest stage first, the most engaged first inside a group.
   * @param rows - The campaign's rows.
   * @returns The non-empty groups.
   */
  static stateGroups(rows: CampaignResultsRow[]): CampaignResultsStateGroup[] {
    return CAMPAIGN_RESULTS_STATE_ORDER.map(
      (state: CampaignResultsProspectState): CampaignResultsStateGroup => ({
        state,
        rows: rows
          .filter((row: CampaignResultsRow): boolean => row.prospect.state === state)
          .sort(
            (first: CampaignResultsRow, second: CampaignResultsRow): number =>
              second.activeSeconds - first.activeSeconds || first.prospect.name.localeCompare(second.prospect.name),
          ),
      }),
    ).filter((group: CampaignResultsStateGroup): boolean => group.rows.length > 0)
  }

  /**
   * A prospect as one square of a unit chart, with what its tooltip tells.
   * @param row - The prospect row.
   * @returns The unit, grouped and coloured by the prospect's state.
   */
  static unitOf(row: CampaignResultsRow): UiUnitChartUnit {
    const { name, category, city, state }: CampaignResultsProspect = row.prospect
    const latestReply: CampaignResultsReply | undefined = row.replies[row.replies.length - 1]
    const details: string[] = [`${CAMPAIGN_RESULTS_STATE_LABELS[state]} · ${category}${city ? `, ${city}` : ''}`]
    if (row.visitCount > 0) {
      const time: string =
        row.activeSeconds > 0 ? `, ${CampaignResultsFormat.activeTime(row.activeSeconds)} sur la page` : ''
      details.push(`${CampaignResultsFormat.count(row.visitCount, 'visite')}${time}`)
    }
    if (latestReply) {
      const receivedAt: Date = parseApiDate(latestReply.received_at)
      details.push(
        `Réponse le ${CampaignResultsFormat.numericDay(receivedAt)} à ${CampaignResultsFormat.clock(receivedAt)}`,
      )
    }
    return { key: row.prospect.id, group: state, tone: CAMPAIGN_RESULTS_STATE_TONES[state], title: name, details }
  }

  /**
   * Whether a row belongs under a filter of the prospects table.
   * @param row - The prospect row.
   * @param filter - The selected filter.
   * @returns True when the row is shown under it.
   */
  static matchesFilter(row: CampaignResultsRow, filter: CampaignResultsFilterKey): boolean {
    const state: CampaignResultsProspectState = row.prospect.state
    if (filter === 'opened') return row.visitCount > 0
    if (filter === 'toRelaunch') return state === 'visited'
    if (filter === 'replied') return row.replies.length > 0
    if (filter === 'silent') return state === 'silent'
    if (filter === 'pending') return state === 'pending' || state === 'not_sent'
    return true
  }

  /**
   * Text a search query is matched against, accents and case left out.
   * @param text - The raw text.
   * @returns The folded text.
   */
  static foldForSearch(text: string): string {
    return text.normalize('NFD').replace(ACCENT_MARKS_PATTERN, '').toLocaleLowerCase('fr-FR')
  }

  /**
   * Whether a row matches a search on its name, trade or city.
   * @param row - The prospect row.
   * @param foldedQuery - The query, already folded.
   * @returns True when the row contains the query.
   */
  static matchesSearch(row: CampaignResultsRow, foldedQuery: string): boolean {
    if (!foldedQuery) return true
    const { name, category, city }: CampaignResultsProspect = row.prospect
    return CampaignResults.foldForSearch(`${name} ${category} ${city ?? ''}`).includes(foldedQuery)
  }

  /**
   * Rows sorted for the table: by a column, or by default furthest stage first then the most engaged.
   * @param rows - The rows to sort.
   * @param sortKey - The sorting column, `default` for the stage order.
   * @param direction - The direction of a column sort.
   * @returns A sorted copy.
   */
  static sortRows(
    rows: CampaignResultsRow[],
    sortKey: CampaignResultsSortKey,
    direction: CampaignResultsSortDirection,
  ): CampaignResultsRow[] {
    const sign: number = direction === 'ascending' ? 1 : -1
    const timeOf: (moment: Date | null, missing: number) => number = (moment: Date | null, missing: number): number =>
      moment ? moment.getTime() : missing
    return [...rows].sort((first: CampaignResultsRow, second: CampaignResultsRow): number => {
      if (sortKey === 'visits') {
        return (first.visitCount - second.visitCount) * sign || second.activeSeconds - first.activeSeconds
      }
      if (sortKey === 'activeTime') return (first.activeSeconds - second.activeSeconds) * sign
      if (sortKey === 'lastVisit') return (timeOf(first.lastVisitAt, -1) - timeOf(second.lastVisitAt, -1)) * sign
      return (
        CampaignResults.stateRank(first.prospect.state) - CampaignResults.stateRank(second.prospect.state) ||
        second.activeSeconds - first.activeSeconds ||
        timeOf(first.firstMailAt, Infinity) - timeOf(second.firstMailAt, Infinity) ||
        first.prospect.name.localeCompare(second.prospect.name)
      )
    })
  }

  /**
   * Whether nothing happened to a prospect yet: no visit, no reply, or no mail at all.
   * @param row - The prospect row.
   * @returns True for a silent or not yet contacted prospect.
   */
  static isQuietRow(row: CampaignResultsRow): boolean {
    return QUIET_STATES.includes(row.prospect.state)
  }

  /**
   * The planned sends of the campaign, the soonest first.
   * @param rows - The campaign's rows.
   * @returns Each planned send with its prospect's name.
   */
  static plannedSends(rows: CampaignResultsRow[]): CampaignResultsPlannedSend[] {
    return rows
      .flatMap((row: CampaignResultsRow): CampaignResultsPlannedSend[] =>
        row.prospect.sends
          .filter((send: CampaignResultsSend): boolean => send.status === 'planned')
          .map(
            (send: CampaignResultsSend): CampaignResultsPlannedSend => ({
              step: send.step,
              prospectName: row.prospect.name,
              at: parseApiDate(send.at),
            }),
          ),
      )
      .sort(
        (first: CampaignResultsPlannedSend, second: CampaignResultsPlannedSend): number =>
          first.at.getTime() - second.at.getTime(),
      )
  }

  /**
   * Prospects grouped by trade, the trades whose prospects opened their site the most first.
   * @param rows - The campaign's rows.
   * @returns One group per trade.
   */
  static tradeGroups(rows: CampaignResultsRow[]): CampaignResultsTradeGroup[] {
    const groups: Map<string, CampaignResultsTradeGroup> = new Map()
    for (const row of rows) {
      const category: string = row.prospect.category.trim()
      const key: string = category.toLocaleLowerCase('fr-FR')
      const group: CampaignResultsTradeGroup = groups.get(key) ?? {
        key,
        label: category ? CampaignResultsFormat.capitalize(category) : 'Sans métier',
        rows: [],
        contacted: 0,
        visited: 0,
      }
      group.rows.push(row)
      if (row.firstMailAt) group.contacted += 1
      if (row.visitCount > 0) group.visited += 1
      groups.set(key, group)
    }
    const rateOf: (group: CampaignResultsTradeGroup) => number = (group: CampaignResultsTradeGroup): number =>
      group.contacted > 0 ? group.visited / group.contacted : -1
    return [...groups.values()]
      .map(
        (group: CampaignResultsTradeGroup): CampaignResultsTradeGroup => ({
          ...group,
          rows: [...group.rows].sort(
            (first: CampaignResultsRow, second: CampaignResultsRow): number =>
              CampaignResults.stateRank(first.prospect.state) - CampaignResults.stateRank(second.prospect.state),
          ),
        }),
      )
      .sort(
        (first: CampaignResultsTradeGroup, second: CampaignResultsTradeGroup): number =>
          rateOf(second) - rateOf(first) ||
          second.contacted - first.contacted ||
          first.label.localeCompare(second.label),
      )
  }

  /**
   * What each mail of the sequence (first mail, then each follow-up) sent and brought: visitors before the next mail, replies.
   * @param results - The campaign's results.
   * @param rows - The campaign's rows.
   * @param followUpDelays - Days between each follow-up and the mail before it, as configured.
   * @returns One summary per step, from the first mail.
   */
  static stepSummaries(
    results: CampaignResultsResponse,
    rows: CampaignResultsRow[],
    followUpDelays: number[],
  ): CampaignResultsStepSummary[] {
    const sends: CampaignResultsSend[] = rows.flatMap(
      (row: CampaignResultsRow): CampaignResultsSend[] => row.prospect.sends,
    )
    const lastStep: number = Math.max(
      followUpDelays.length,
      ...sends.map((send: CampaignResultsSend): number => send.step),
      0,
    )
    const steps: number[] = Array.from({ length: lastStep + 1 }, (_: unknown, step: number): number => step)
    return steps.map((step: number): CampaignResultsStepSummary => {
      const stepSends: CampaignResultsSend[] = sends.filter((send: CampaignResultsSend): boolean => send.step === step)
      const plannedTimes: number[] = stepSends
        .filter((send: CampaignResultsSend): boolean => send.status === 'planned')
        .map((send: CampaignResultsSend): number => parseApiDate(send.at).getTime())
      const delayToStep: number = followUpDelays
        .slice(0, step)
        .reduce((total: number, days: number): number => total + days, 0)
      return {
        step,
        label: CampaignResults.stepLabel(step, lastStep),
        timingLabel: CampaignResults.stepTimingLabel(step, delayToStep),
        sent: stepSends.filter((send: CampaignResultsSend): boolean => send.status === 'sent').length,
        planned: plannedTimes.length,
        cancelled: stepSends.filter((send: CampaignResultsSend): boolean => send.status === 'skipped').length,
        firstPlannedAt: plannedTimes.length > 0 ? new Date(Math.min(...plannedTimes)) : null,
        visitors: rows.filter((row: CampaignResultsRow): boolean => CampaignResults.visitedAfterStep(row, step)).length,
        replies: results.replies.filter((reply: CampaignResultsReply): boolean => reply.answered_step === step),
      }
    })
  }

  /**
   * Name of a step of the sequence.
   * @param step - 0 for the first mail, then the follow-up number.
   * @param lastStep - The campaign's last step, which tells whether follow-ups need a number.
   * @returns « Premier mail », « Relance », « 1re relance », « 2e relance »…
   */
  static stepLabel(step: number, lastStep: number): string {
    if (step === 0) return 'Premier mail'
    if (lastStep === 1) return 'Relance'
    return step === 1 ? '1re relance' : `${step}e relance`
  }

  /**
   * When a mail of the sequence leaves: « jour J » for the first mail, « J+3 » for a follow-up three days later.
   * @param step - 0 for the first mail, then the follow-up number.
   * @param daysAfterFirstMail - Configured days between the first mail and this one.
   * @returns The timing label, empty for a follow-up without a configured delay.
   */
  static stepTimingLabel(step: number, daysAfterFirstMail: number): string {
    if (step === 0) return 'jour J'
    if (daysAfterFirstMail > 0) return `J+${daysAfterFirstMail}`
    return ''
  }

  /**
   * Whether a prospect visited their site after a mail of the sequence and before the next one left.
   * @param row - The prospect row.
   * @param step - The mail's step.
   * @returns True when a visit falls in that mail's window.
   */
  static visitedAfterStep(row: CampaignResultsRow, step: number): boolean {
    const sentAt: (stepToFind: number) => number | null = (stepToFind: number): number | null => {
      const send: CampaignResultsSend | undefined = row.prospect.sends.find(
        (candidate: CampaignResultsSend): boolean => candidate.step === stepToFind && candidate.status === 'sent',
      )
      return send ? parseApiDate(send.at).getTime() : null
    }
    const from: number | null = sentAt(step)
    if (from === null) return false
    const until: number = sentAt(step + 1) ?? Infinity
    return row.prospect.visits.some((visit: CampaignResultsVisit): boolean => {
      const visitedAt: number = parseApiDate(visit.started_at).getTime()
      return visitedAt >= from && visitedAt < until
    })
  }

  /**
   * How and when prospects came to their site: delay after the first mail, phone, evening.
   * @param rows - The campaign's rows.
   * @returns The visit marks.
   */
  static visitMarks(rows: CampaignResultsRow[]): CampaignResultsVisitMarks {
    const delays: number[] = rows
      .flatMap((row: CampaignResultsRow): number[] => {
        const firstVisit: CampaignResultsVisit | undefined = row.prospect.visits[0]
        if (!firstVisit || !row.firstMailAt) return []
        const elapsed: number = parseApiDate(firstVisit.started_at).getTime() - row.firstMailAt.getTime()
        return [Math.max(0, Math.round(elapsed / MILLISECONDS_PER_MINUTE))]
      })
      .sort((first: number, second: number): number => first - second)
    const visits: CampaignResultsVisit[] = rows.flatMap(
      (row: CampaignResultsRow): CampaignResultsVisit[] => row.prospect.visits,
    )
    return {
      medianDelayMinutes: CampaignResults.median(delays),
      visitorsWithinHour: delays.filter((delay: number): boolean => delay <= MINUTES_PER_HOUR).length,
      visitors: delays.length,
      phoneVisits: visits.filter((visit: CampaignResultsVisit): boolean => visit.device_type === 'Mobile').length,
      eveningVisits: visits.filter(
        (visit: CampaignResultsVisit): boolean => parseApiDate(visit.started_at).getHours() >= EVENING_HOUR,
      ).length,
      visits: visits.length,
    }
  }

  /**
   * Middle value of sorted numbers, the mean of the two middle ones for an even count.
   * @param sortedValues - The values, smallest first.
   * @returns The rounded median, or null without values.
   */
  static median(sortedValues: number[]): number | null {
    if (sortedValues.length === 0) return null
    const middleIndex: number = Math.floor(sortedValues.length / 2)
    const middleValue: number = sortedValues[middleIndex] ?? 0
    if (sortedValues.length % 2 === 1) return middleValue
    const valueBeforeMiddle: number = sortedValues[middleIndex - 1] ?? 0
    return Math.round((valueBeforeMiddle + middleValue) / 2)
  }

  /**
   * What a campaign can be compared against: the pooled other campaigns, then each of them, most recent first.
   * @param benchmarks - Stage counts of the user's email campaigns.
   * @param campaignId - The campaign being looked at, left out.
   * @returns The comparisons, empty when the campaign is the only one.
   */
  static comparisons(benchmarks: CampaignBenchmark[], campaignId: number): CampaignResultsComparison[] {
    const others: CampaignBenchmark[] = benchmarks.filter(
      (benchmark: CampaignBenchmark): boolean => benchmark.campaign_id !== campaignId,
    )
    const each: CampaignResultsComparison[] = others.map(
      (benchmark: CampaignBenchmark): CampaignResultsComparison => ({
        key: `campaign-${benchmark.campaign_id}`,
        label: benchmark.name,
        referenceLabel: '',
        contacted: benchmark.contacted,
        visited: benchmark.visited,
        replied: benchmark.replied,
        interested: benchmark.interested,
      }),
    )
    if (others.length < 2) return each
    const sumOf: (stage: CampaignResultsStage) => number = (stage: CampaignResultsStage): number =>
      others.reduce((total: number, benchmark: CampaignBenchmark): number => total + benchmark[stage], 0)
    return [
      {
        key: 'others',
        label: 'vos autres campagnes',
        referenceLabel: 'ailleurs',
        contacted: sumOf('contacted'),
        visited: sumOf('visited'),
        replied: sumOf('replied'),
        interested: sumOf('interested'),
      },
      ...each,
    ]
  }
}
