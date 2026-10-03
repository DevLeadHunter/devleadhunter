import type { CampaignStatus } from '~/services/campaignService'
import type { CampaignChannelWords } from '~/types/CampaignChannelWords'
import type {
  CampaignResultsComparison,
  CampaignResultsDay,
  CampaignResultsHeadline,
  CampaignResultsKpiComparison,
  CampaignResultsPlannedSend,
  CampaignResultsReply,
  CampaignResultsReplyVerdict,
  CampaignResultsResponse,
  CampaignResultsRow,
  CampaignResultsRowReply,
  CampaignResultsSend,
  CampaignResultsSendDayProgress,
  CampaignResultsStage,
  CampaignResultsStateFact,
  CampaignResultsStepSummary,
  CampaignResultsTodo,
  CampaignResultsTodoTone,
  CampaignResultsTotals,
  CampaignResultsTradeGroup,
} from '~/types/CampaignResults'
import type { UiKpiBandCell, UiKpiBandTrendBadge } from '~/types/UiKpiBand'
import { CAMPAIGN_CHANNEL_WORDS } from '~/constants/campaignResults'
import { CampaignResults } from '~/utils/campaignResults'
import { CampaignResultsFormat } from '~/utils/campaignResultsFormat'
import { formatRelativeTime, formatScheduledMoment, parseApiDate } from '~/utils/date'

const MILLISECONDS_PER_HOUR: number = 3_600_000
const MILLISECONDS_PER_DAY: number = 86_400_000
const RECENT_REPLY_HOURS: number = 48
const INTERESTED_FOLLOW_UP_DAYS: number = 30
const SENTENCE_NAMES_LIMIT: number = 3
const DETAIL_NAMES_LIMIT: number = 2

/** The sentences of a campaign's results: headline, key figures, to-do list and card notes. */
export class CampaignResultsSummary {
  private constructor() {}

  /**
   * Whether mails of the campaign are still waiting to leave.
   * @param totals - The campaign's totals.
   * @returns True while first mails or follow-ups are planned.
   */
  static isSending(totals: CampaignResultsTotals): boolean {
    return totals.planned_first_mails + totals.planned_follow_ups > 0
  }

  /**
   * Which sending day of the campaign today is, counting only the days a mail left or will leave.
   * @param rows - The campaign's rows.
   * @param now - The current moment.
   * @returns Today's rank and the number of sending days, or null when no mail is sent nor planned.
   */
  static sendDayProgress(rows: CampaignResultsRow[], now: Date): CampaignResultsSendDayProgress | null {
    const sendDayKeys: Set<string> = new Set()
    for (const row of rows) {
      for (const send of row.prospect.sends) {
        if (send.status === 'sent' || send.status === 'planned') {
          sendDayKeys.add(CampaignResults.dayKey(parseApiDate(send.at)))
        }
      }
    }
    if (sendDayKeys.size === 0) return null
    const todayKey: string = CampaignResults.dayKey(now)
    return {
      current: [...sendDayKeys].filter((key: string): boolean => key <= todayKey).length,
      total: sendDayKeys.size,
    }
  }

  /**
   * The headline of the tab: where the campaign stands, its main result, and a sentence of context.
   * @param results - The campaign's results.
   * @param rows - The campaign's rows.
   * @param status - The campaign's status.
   * @param now - The current moment.
   * @returns The label, title and summary.
   */
  static headline(
    results: CampaignResultsResponse,
    rows: CampaignResultsRow[],
    status: CampaignStatus,
    now: Date,
  ): CampaignResultsHeadline {
    const isSending: boolean = CampaignResultsSummary.isSending(results.totals)
    return {
      label: CampaignResultsSummary.headlineLabel(results, rows, status, now),
      title: CampaignResultsSummary.headlineTitle(results, isSending),
      summary: isSending
        ? CampaignResultsSummary.sendingSummary(results, rows, now)
        : CampaignResultsSummary.reviewSummary(results, rows),
    }
  }

  /**
   * The five key figures, each against the chosen comparison when there is one.
   * @param results - The campaign's results.
   * @param rows - The campaign's rows.
   * @param comparison - What the rates are compared against, null for nothing.
   * @param now - The current moment.
   * @returns The cells of the figures band.
   */
  static kpiCells(
    results: CampaignResultsResponse,
    rows: CampaignResultsRow[],
    comparison: CampaignResultsComparison | null,
    now: Date,
  ): UiKpiBandCell[] {
    const totals: CampaignResultsTotals = results.totals
    const contacted: number = totals.contacted
    return [
      {
        key: 'contacted',
        label: 'Contactés',
        value: String(contacted),
        total: `/ ${totals.prospects}`,
        detail: CampaignResultsSummary.contactedDetail(totals, CAMPAIGN_CHANNEL_WORDS[results.channel]),
        trendBadge: { trend: 'flat', text: CampaignResultsSummary.contactedBadgeText(results, rows, now) },
        comparisonNote: '',
        meterRatio: totals.prospects > 0 ? contacted / totals.prospects : 0,
        meterTone: 'soft',
      },
      CampaignResultsSummary.visitedCell(results, comparison),
      {
        key: 'replied',
        label: 'Ont répondu',
        value: String(totals.replied),
        total: null,
        detail: CampaignResultsSummary.repliedDetail(totals),
        ...CampaignResultsSummary.comparisonOf(totals.replied, contacted, comparison, 'replied'),
        meterRatio: CampaignResultsSummary.ratioOf(totals.replied, contacted),
        meterTone: 'ink',
      },
      {
        key: 'interested',
        label: 'Intéressés',
        value: String(totals.interested),
        total: null,
        detail: CampaignResultsSummary.interestedDetail(totals, rows),
        ...CampaignResultsSummary.comparisonOf(totals.interested, contacted, comparison, 'interested'),
        meterRatio: CampaignResultsSummary.ratioOf(totals.interested, contacted),
        meterTone: 'green',
      },
      {
        key: 'sales',
        label: 'Ventes',
        value: String(totals.sales),
        total: null,
        detail: CampaignResultsSummary.salesDetail(totals, rows),
        trendBadge: { trend: 'flat', text: CampaignResultsSummary.revenueBadgeText(totals) },
        comparisonNote: '',
        meterRatio: CampaignResultsSummary.ratioOf(totals.sales, contacted),
        meterTone: 'green',
      },
    ]
  }

  /**
   * What is worth doing now, the most likely sale first: replies to answer, interested prospects to follow,
   * visitors who did not write, addresses or numbers to check, refusals to acknowledge.
   * @param rows - The campaign's rows.
   * @param now - The current moment.
   * @param words - The words of the campaign's channel.
   * @returns The to-do entries, in order.
   */
  static todos(rows: CampaignResultsRow[], now: Date, words: CampaignChannelWords): CampaignResultsTodo[] {
    const todos: CampaignResultsTodo[] = []
    const interestedReplies: CampaignResultsRowReply[] = CampaignResultsSummary.latestInterestedReplies(rows)
    for (const { row, reply } of interestedReplies) {
      if (!reply.is_handled) todos.push(CampaignResultsSummary.replyTodo(row, reply, 'green'))
    }
    for (const { row, reply } of interestedReplies) {
      if (CampaignResultsSummary.isAwaitingFollowUp(reply, now)) {
        todos.push(CampaignResultsSummary.awaitingFollowUpTodo(row, reply))
      }
    }
    for (const row of rows) {
      const reply: CampaignResultsReply | null = CampaignResultsSummary.latestReply(row, 'other')
      if (row.prospect.state === 'replied' && reply && !reply.is_handled) {
        todos.push(CampaignResultsSummary.replyTodo(row, reply, 'blue'))
      }
    }
    const visitorsTodo: CampaignResultsTodo | null = CampaignResultsSummary.visitorsTodo(rows, words)
    if (visitorsTodo) todos.push(visitorsTodo)
    for (const row of rows) {
      const bouncedTodo: CampaignResultsTodo | null = CampaignResultsSummary.bouncedTodo(row, words)
      if (bouncedTodo) todos.push(bouncedTodo)
    }
    for (const row of rows) {
      const reply: CampaignResultsReply | null = CampaignResultsSummary.latestReply(row, 'refused')
      if (row.prospect.state === 'refused' && reply && !reply.is_handled) {
        todos.push(CampaignResultsSummary.replyTodo(row, reply, 'red'))
      }
    }
    return todos
  }

  /**
   * The facts under the state squares: the sends to come or made, and what the SMS of an SMS campaign cost.
   * @param results - The campaign's results.
   * @param rows - The campaign's rows.
   * @returns The facts, in reading order.
   */
  static stateFacts(results: CampaignResultsResponse, rows: CampaignResultsRow[]): CampaignResultsStateFact[] {
    const totals: CampaignResultsTotals = results.totals
    const words: CampaignChannelWords = CAMPAIGN_CHANNEL_WORDS[results.channel]
    const planned: CampaignResultsPlannedSend[] = CampaignResults.plannedSends(rows)
    const facts: CampaignResultsStateFact[] = CampaignResultsSummary.sendFacts(totals, planned, words)
    const sentCount: number = totals.first_mails_sent + totals.follow_ups_sent
    if (totals.sms_cost_cents !== null && sentCount > 0) {
      facts.push({
        label: 'Coût des SMS',
        value: CampaignResultsFormat.money(totals.sms_cost_cents, 'EUR'),
        detail: CampaignResultsFormat.count(sentCount, 'SMS envoyé', 'SMS envoyés'),
      })
    }
    if (totals.bounced > 0) {
      facts.push({
        label: CampaignResultsFormat.capitalize(words.failedDeliveriesNoun),
        value: String(totals.bounced),
        detail: CampaignResultsSummary.bouncedNames(rows),
      })
    }
    if (totals.failed > 0) {
      facts.push({
        label: "Échecs d'envoi",
        value: String(totals.failed),
        detail: "à reprendre dans la file d'attente",
      })
    }
    if (planned.length === 0 && results.demo_sites.online > 0) {
      facts.push({
        label: 'Démos en ligne',
        value: String(results.demo_sites.online),
        detail: CampaignResultsSummary.demoExpiryDetail(results),
      })
    }
    return facts
  }

  /**
   * The best and the worst trade, once at least two trades had a few prospects contacted.
   * @param groups - The trade groups, best rate first.
   * @returns The sentence, empty when there is nothing to tell apart.
   */
  static tradesNote(groups: CampaignResultsTradeGroup[]): string {
    const comparableGroups: CampaignResultsTradeGroup[] = CampaignResults.comparableTradeGroups(groups)
    const best: CampaignResultsTradeGroup | undefined = comparableGroups[0]
    const worst: CampaignResultsTradeGroup | undefined = comparableGroups[comparableGroups.length - 1]
    if (!best || !worst || best === worst) return ''
    if (best.visited / best.contacted === worst.visited / worst.contacted) return ''
    const bestLabel: string = best.label.toLocaleLowerCase('fr-FR')
    const worstLabel: string = worst.label.toLocaleLowerCase('fr-FR')
    return `Le mieux : ${bestLabel} (${best.visited} sur ${best.contacted}). Le moins bien : ${worstLabel} (${worst.visited} sur ${worst.contacted}).`
  }

  /**
   * What the to-do list says when nothing waits.
   * @param totals - The campaign's totals.
   * @param words - The words of the campaign's channel.
   * @returns Why there is nothing to do yet.
   */
  static todosEmptyNote(totals: CampaignResultsTotals, words: CampaignChannelWords): string {
    if (totals.contacted === 0) return `Rien à traiter : aucun ${words.messageNoun} n'est encore parti.`
    return "Rien à traiter pour l'instant : aucune réponse ni visite n'attend de suite."
  }

  /**
   * What the follow-ups brought, under the table of the sequence.
   * @param steps - The step summaries, from the first message.
   * @param replies - Every reply of the campaign.
   * @param words - The words of the campaign's channel.
   * @returns The sentence.
   */
  static sendsNote(
    steps: CampaignResultsStepSummary[],
    replies: CampaignResultsReply[],
    words: CampaignChannelWords,
  ): string {
    const followUps: CampaignResultsStepSummary[] = steps.filter(
      (step: CampaignResultsStepSummary): boolean => step.step > 0,
    )
    if (followUps.length === 0) return 'Pas de relance dans cette campagne.'
    const sentFollowUps: number = followUps.reduce(
      (total: number, step: CampaignResultsStepSummary): number => total + step.sent,
      0,
    )
    if (sentFollowUps === 0) return "Une relance s'annule d'elle-même si le prospect répond avant son départ."
    if (replies.length === 0) return `Aucune réponse, ni au premier ${words.messageNoun} ni aux relances.`
    const repliesAfterFollowUps: number = replies.filter(
      (reply: CampaignResultsReply): boolean => reply.answered_step > 0,
    ).length
    if (replies.length > 1) {
      return `${repliesAfterFollowUps} des ${replies.length} réponses sont arrivées après une relance.`
    }
    if (repliesAfterFollowUps > 0) return 'La seule réponse est arrivée après une relance.'
    return `La seule réponse est arrivée après le premier ${words.messageNoun}.`
  }

  /**
   * The span the day-by-day chart covers.
   * @param days - The campaign's days.
   * @returns « du 22 septembre au 1er octobre », « le 22 septembre », or empty without days.
   */
  static periodLabel(days: CampaignResultsDay[]): string {
    const first: CampaignResultsDay | undefined = days[0]
    const last: CampaignResultsDay | undefined = days[days.length - 1]
    if (!first || !last) return ''
    if (first === last) return `le ${CampaignResultsFormat.dayAndMonth(first.date)}`
    return `du ${CampaignResultsFormat.dayAndMonth(first.date)} au ${CampaignResultsFormat.dayAndMonth(last.date)}`
  }

  /**
   * Where the campaign stands: the day of sending while it runs, else its end and today's date.
   * @param results - The campaign's results.
   * @param rows - The campaign's rows.
   * @param status - The campaign's status.
   * @param now - The current moment.
   * @returns The headline label.
   */
  private static headlineLabel(
    results: CampaignResultsResponse,
    rows: CampaignResultsRow[],
    status: CampaignStatus,
    now: Date,
  ): string {
    if (CampaignResultsSummary.isSending(results.totals)) {
      return CampaignResultsSummary.sendingLabel(results, rows, now)
    }
    const review: string = `bilan au ${CampaignResultsFormat.longDay(now)}`
    if (status === 'paused') return `En pause · ${review}`
    if (status === 'cancelled') return `Annulée · ${review}`
    const lastSentAt: Date | null = CampaignResultsSummary.lastSentAt(rows)
    if (!lastSentAt) return CampaignResultsFormat.capitalize(review)
    const ending: string = status === 'completed' ? 'Terminée' : 'Dernier envoi'
    return `${ending} le ${CampaignResultsFormat.dayAndMonth(lastSentAt)} · ${review}`
  }

  /**
   * The label of a running campaign: today, then the sending day, or when the first mail leaves.
   * @param results - The campaign's results.
   * @param rows - The campaign's rows.
   * @param now - The current moment.
   * @returns « Jeudi 24 septembre, 11 h 05 · jour 3 sur 8 jours d'envoi ».
   */
  private static sendingLabel(results: CampaignResultsResponse, rows: CampaignResultsRow[], now: Date): string {
    const moment: string = `${CampaignResultsFormat.capitalize(CampaignResultsFormat.longDay(now))}, ${CampaignResultsFormat.spokenClock(now)}`
    const progress: CampaignResultsSendDayProgress | null = CampaignResultsSummary.sendDayProgress(rows, now)
    if (progress && progress.current > 0)
      return `${moment} · jour ${progress.current} sur ${progress.total} jours d'envoi`
    if (!results.next_send) return moment
    return `${moment} · premier envoi ${formatScheduledMoment(parseApiDate(results.next_send.at))}`
  }

  /**
   * The main result in one line: sales, else interested prospects, else visits.
   * @param results - The campaign's results.
   * @param isSending - Whether messages are still planned.
   * @returns The headline title.
   */
  private static headlineTitle(results: CampaignResultsResponse, isSending: boolean): string {
    const totals: CampaignResultsTotals = results.totals
    const words: CampaignChannelWords = CAMPAIGN_CHANNEL_WORDS[results.channel]
    if (totals.sales > 0) {
      return `${CampaignResultsFormat.count(totals.sales, 'vente')}, ${CampaignResultsFormat.money(totals.revenue_cents, totals.currency)}`
    }
    if (totals.interested > 0) {
      const outcome: string = isSending ? " pour l'instant" : ', aucune vente'
      return `${CampaignResultsFormat.count(totals.interested, 'intéressé')}${outcome}`
    }
    if (totals.contacted === 0) {
      if (!results.next_send) return `Aucun ${words.messageNoun} envoyé`
      return `Premier ${words.messageNoun} ${formatScheduledMoment(parseApiDate(results.next_send.at))}`
    }
    const contactedLabel: string = CampaignResultsFormat.count(
      totals.contacted,
      'prospect contacté',
      'prospects contactés',
    )
    if (!results.is_visit_tracking_available) {
      return `${CampaignResultsFormat.capitalize(contactedLabel)}, ${CampaignResultsFormat.count(totals.replied, 'réponse')}`
    }
    if (totals.visited === 1) return `1 prospect sur ${totals.contacted} a ouvert son site`
    if (totals.visited > 1) return `${totals.visited} prospects sur ${totals.contacted} ont ouvert leur site`
    if (isSending) return `${CampaignResultsFormat.capitalize(contactedLabel)}, aucun site ouvert pour l'instant`
    return `Aucun site ouvert sur ${contactedLabel}`
  }

  /**
   * Context of a running campaign: the latest reply when it is fresh, and the messages still to leave.
   * @param results - The campaign's results.
   * @param rows - The campaign's rows.
   * @param now - The current moment.
   * @returns The summary sentences.
   */
  private static sendingSummary(results: CampaignResultsResponse, rows: CampaignResultsRow[], now: Date): string {
    const sentences: string[] = []
    const freshReply: string = CampaignResultsSummary.freshReplySentence(results, rows, now)
    if (freshReply) sentences.push(freshReply)
    const plannedSends: string = CampaignResultsSummary.plannedSendsSentence(results, now)
    if (plannedSends) sentences.push(plannedSends)
    return sentences.join(' ')
  }

  /**
   * The latest reply of the campaign when it arrived less than two days ago.
   * @param results - The campaign's results.
   * @param rows - The campaign's rows.
   * @param now - The current moment.
   * @returns « Les projets d'Hugo a répondu il y a 29 min. », or empty.
   */
  private static freshReplySentence(results: CampaignResultsResponse, rows: CampaignResultsRow[], now: Date): string {
    const latestReply: CampaignResultsReply | undefined = results.replies[results.replies.length - 1]
    if (!latestReply) return ''
    const replyAge: number = now.getTime() - parseApiDate(latestReply.received_at).getTime()
    if (replyAge > RECENT_REPLY_HOURS * MILLISECONDS_PER_HOUR) return ''
    const author: CampaignResultsRow | undefined = rows.find(
      (row: CampaignResultsRow): boolean => row.prospect.id === latestReply.prospect_id,
    )
    if (!author) return ''
    return `${author.prospect.name} a répondu ${formatRelativeTime(latestReply.received_at).toLocaleLowerCase('fr-FR')}.`
  }

  /**
   * The messages still to leave and the day the last one leaves.
   * @param results - The campaign's results.
   * @param now - The current moment.
   * @returns « 11 premiers mails et 25 relances partiront d'ici le jeudi 1er octobre. », or empty.
   */
  private static plannedSendsSentence(results: CampaignResultsResponse, now: Date): string {
    const totals: CampaignResultsTotals = results.totals
    const words: CampaignChannelWords = CAMPAIGN_CHANNEL_WORDS[results.channel]
    if (!results.last_planned_send_at) return ''
    const plannedParts: string[] = []
    if (totals.planned_first_mails > 0) {
      plannedParts.push(
        CampaignResultsFormat.count(
          totals.planned_first_mails,
          `premier ${words.messageNoun}`,
          `premiers ${words.messagesNoun}`,
        ),
      )
    }
    if (totals.planned_follow_ups > 0) {
      plannedParts.push(CampaignResultsFormat.count(totals.planned_follow_ups, 'relance'))
    }
    if (plannedParts.length === 0) return ''
    const lastPlannedAt: Date = parseApiDate(results.last_planned_send_at)
    const isLeavingToday: boolean = CampaignResults.dayKey(lastPlannedAt) === CampaignResults.dayKey(now)
    const when: string = isLeavingToday ? "aujourd'hui" : `d'ici le ${CampaignResultsFormat.longDay(lastPlannedAt)}`
    const plannedCount: number = totals.planned_first_mails + totals.planned_follow_ups
    const verb: string = CampaignResultsFormat.agreeWithCount(plannedCount, 'partira', 'partiront')
    return `${plannedParts.join(' et ')} ${verb} ${when}.`
  }

  /**
   * Context of a campaign whose mails all left: visits and replies, and who still waits for a follow-up.
   * @param results - The campaign's results.
   * @param rows - The campaign's rows.
   * @returns The summary sentences.
   */
  private static reviewSummary(results: CampaignResultsResponse, rows: CampaignResultsRow[]): string {
    const totals: CampaignResultsTotals = results.totals
    if (totals.contacted === 0) return ''
    const sentences: string[] = []
    const isTitleAboutVisits: boolean = totals.sales === 0 && totals.interested === 0
    if (isTitleAboutVisits || !results.is_visit_tracking_available) {
      sentences.push(CampaignResultsSummary.repliesSentence(totals))
    } else {
      sentences.push(`${CampaignResultsSummary.visitedClause(totals)}${CampaignResultsSummary.repliedClause(totals)}.`)
    }
    const awaitingNames: string[] = rows
      .filter((row: CampaignResultsRow): boolean => row.prospect.state === 'interested')
      .map((row: CampaignResultsRow): string => row.prospect.name)
    if (awaitingNames.length > 0) {
      const verb: string = CampaignResultsFormat.agreeWithCount(awaitingNames.length, 'attend', 'attendent')
      sentences.push(`${CampaignResultsSummary.shortNameList(awaitingNames)} ${verb} une suite.`)
    }
    return sentences.join(' ')
  }

  /**
   * How many prospects replied, and how many of them refused.
   * @param totals - The campaign's totals.
   * @returns « Personne n'a répondu. », « 2 prospects ont répondu, dont 1 refus. »
   */
  private static repliesSentence(totals: CampaignResultsTotals): string {
    if (totals.replied === 0) return "Personne n'a répondu."
    const replied: string = CampaignResultsFormat.count(totals.replied, 'prospect a répondu', 'prospects ont répondu')
    return `${replied}${CampaignResultsSummary.refusedClause(totals)}.`
  }

  /**
   * The share of contacted prospects who opened their site, opening the review sentence.
   * @param totals - The campaign's totals.
   * @returns « 10 prospects sur 25 ont ouvert leur site ».
   */
  private static visitedClause(totals: CampaignResultsTotals): string {
    if (totals.visited === 1) return `1 prospect sur ${totals.contacted} a ouvert son site`
    if (totals.visited > 1) return `${totals.visited} prospects sur ${totals.contacted} ont ouvert leur site`
    if (totals.contacted === 1) return "Le seul prospect contacté n'a pas ouvert son site"
    return `Aucun des ${totals.contacted} prospects contactés n'a ouvert son site`
  }

  /**
   * The replies, following the visits in the review sentence.
   * @param totals - The campaign's totals.
   * @returns « et 3 ont répondu, dont 1 refus », or a note that nobody replied.
   */
  private static repliedClause(totals: CampaignResultsTotals): string {
    if (totals.replied === 0) return ', sans aucune réponse'
    const link: string = totals.visited === 0 ? ', mais' : ' et'
    const verb: string = CampaignResultsFormat.agreeWithCount(totals.replied, 'a', 'ont')
    return `${link} ${totals.replied} ${verb} répondu${CampaignResultsSummary.refusedClause(totals)}`
  }

  /**
   * The refusals among the replies.
   * @param totals - The campaign's totals.
   * @returns « , dont 2 refus », or empty without refusal.
   */
  private static refusedClause(totals: CampaignResultsTotals): string {
    if (totals.refused === 0) return ''
    return `, dont ${CampaignResultsFormat.count(totals.refused, 'refus', 'refus')}`
  }

  /**
   * Names in a sentence, the extra ones counted rather than listed.
   * @param names - The names, in order.
   * @returns « A, B et C », or « A, B, C et 2 autres ».
   */
  private static shortNameList(names: string[]): string {
    if (names.length <= SENTENCE_NAMES_LIMIT) return CampaignResultsFormat.nameList(names)
    const extraCount: number = names.length - SENTENCE_NAMES_LIMIT
    return `${names.slice(0, SENTENCE_NAMES_LIMIT).join(', ')} et ${extraCount} autres`
  }

  /**
   * The figure of the prospects who opened their site, or a note when visits are not measured.
   * @param results - The campaign's results.
   * @param comparison - What the rate is compared against, null for nothing.
   * @returns The key figure cell.
   */
  private static visitedCell(
    results: CampaignResultsResponse,
    comparison: CampaignResultsComparison | null,
  ): UiKpiBandCell {
    const totals: CampaignResultsTotals = results.totals
    if (!results.is_visit_tracking_available) {
      return {
        key: 'visited',
        label: 'Ont ouvert leur site',
        value: '—',
        total: null,
        detail: 'Visites non mesurées',
        trendBadge: null,
        comparisonNote: '',
        meterRatio: 0,
        meterTone: 'blue',
      }
    }
    return {
      key: 'visited',
      label: 'Ont ouvert leur site',
      value: String(totals.visited),
      total: null,
      detail: CampaignResultsSummary.shareOfContacted(totals.visited, totals.contacted),
      ...CampaignResultsSummary.comparisonOf(totals.visited, totals.contacted, comparison, 'visited'),
      meterRatio: CampaignResultsSummary.ratioOf(totals.visited, totals.contacted),
      meterTone: 'blue',
    }
  }

  /**
   * Under the contacted count: the messages sent, or the prospects still to contact, and their incidents.
   * @param totals - The campaign's totals.
   * @param words - The words of the campaign's channel.
   * @returns « 49 mails · 2 rebonds », « 40 SMS · 1 non reçu », « 11 à venir · aucun échec ».
   */
  private static contactedDetail(totals: CampaignResultsTotals, words: CampaignChannelWords): string {
    const isSending: boolean = CampaignResultsSummary.isSending(totals)
    const sentCount: number = totals.first_mails_sent + totals.follow_ups_sent
    if (!isSending && sentCount === 0) return `Aucun ${words.messageNoun} parti`
    const sendCount: string = isSending
      ? `${totals.prospects - totals.contacted} à venir`
      : CampaignResultsFormat.count(sentCount, words.messageNoun, words.messagesNoun)
    const incidents: string[] = []
    if (totals.bounced > 0) {
      incidents.push(CampaignResultsFormat.count(totals.bounced, words.failedDeliveryNoun, words.failedDeliveriesNoun))
    }
    if (totals.failed > 0) incidents.push(CampaignResultsFormat.count(totals.failed, 'échec'))
    if (incidents.length === 0) incidents.push('aucun échec')
    return `${sendCount} · ${incidents.join(', ')}`
  }

  /**
   * The badge of the contacted count: the sending day, or whether every prospect got the first mail.
   * @param results - The campaign's results.
   * @param rows - The campaign's rows.
   * @param now - The current moment.
   * @returns The badge text.
   */
  private static contactedBadgeText(results: CampaignResultsResponse, rows: CampaignResultsRow[], now: Date): string {
    const totals: CampaignResultsTotals = results.totals
    if (CampaignResultsSummary.isSending(totals)) {
      const progress: CampaignResultsSendDayProgress | null = CampaignResultsSummary.sendDayProgress(rows, now)
      if (progress && progress.current > 0) return `Jour ${progress.current} sur ${progress.total}`
      return 'Pas encore parti'
    }
    if (totals.contacted === totals.prospects) return 'Tout est parti'
    return CampaignResultsFormat.count(totals.prospects - totals.contacted, 'non envoyé', 'non envoyés')
  }

  /**
   * Under the replies count: the share of contacted prospects and the verdicts.
   * @param totals - The campaign's totals.
   * @returns « 12 % · 2 intéressés, 1 refus ».
   */
  private static repliedDetail(totals: CampaignResultsTotals): string {
    if (totals.replied === 0) return CampaignResultsSummary.shareOfContacted(0, totals.contacted)
    const share: string = `${CampaignResultsFormat.percent(totals.replied, totals.contacted)} %`
    const verdicts: string[] = [CampaignResultsFormat.count(totals.interested, 'intéressé')]
    if (totals.refused > 0) verdicts.push(CampaignResultsFormat.count(totals.refused, 'refus', 'refus'))
    return `${share} · ${verdicts.join(', ')}`
  }

  /**
   * Under the interested count: the share of contacted prospects and who they are.
   * @param totals - The campaign's totals.
   * @param rows - The campaign's rows.
   * @returns « 8 % · TP Motorsport, Les projets d'Hugo ».
   */
  private static interestedDetail(totals: CampaignResultsTotals, rows: CampaignResultsRow[]): string {
    if (totals.contacted === 0) return ''
    const share: string = `${CampaignResultsFormat.percent(totals.interested, totals.contacted)} %`
    const names: string[] = rows
      .filter(
        (row: CampaignResultsRow): boolean => row.prospect.state === 'interested' || row.prospect.state === 'sold',
      )
      .map((row: CampaignResultsRow): string => row.prospect.name)
    if (names.length === 0) return CampaignResultsSummary.shareOfContacted(totals.interested, totals.contacted)
    const listedNames: string = names.slice(0, DETAIL_NAMES_LIMIT).join(', ')
    const ellipsis: string = names.length > DETAIL_NAMES_LIMIT ? '…' : ''
    return `${share} · ${listedNames}${ellipsis}`
  }

  /**
   * Under the sales count: their share of contacted prospects, or the leads still open.
   * @param totals - The campaign's totals.
   * @param rows - The campaign's rows.
   * @returns « 4 % des contactés », « 2 pistes ouvertes », « Aucune piste ».
   */
  private static salesDetail(totals: CampaignResultsTotals, rows: CampaignResultsRow[]): string {
    if (totals.sales > 0) return `${CampaignResultsFormat.percent(totals.sales, totals.contacted)} % des contactés`
    const openLeads: number = rows.filter(
      (row: CampaignResultsRow): boolean => row.prospect.state === 'interested',
    ).length
    if (openLeads === 0) return 'Aucune piste'
    return CampaignResultsFormat.count(openLeads, 'piste ouverte', 'pistes ouvertes')
  }

  /**
   * The money the campaign's sales brought.
   * @param totals - The campaign's totals.
   * @returns « 0 € encaissé », « 500 € encaissés ».
   */
  private static revenueBadgeText(totals: CampaignResultsTotals): string {
    const amount: string = CampaignResultsFormat.money(totals.revenue_cents, totals.currency)
    const participle: string = CampaignResultsFormat.agreeWithCount(
      CampaignResultsFormat.unitsFromCents(totals.revenue_cents),
      'encaissé',
    )
    return `${amount} ${participle}`
  }

  /**
   * The share of the contacted prospects a figure stands for, empty before the first mail.
   * @param count - Prospects at the stage.
   * @param contacted - Prospects contacted.
   * @returns « 40 % des contactés », or empty when nobody was contacted.
   */
  private static shareOfContacted(count: number, contacted: number): string {
    if (contacted === 0) return ''
    return `${CampaignResultsFormat.percent(count, contacted)} % des contactés`
  }

  /**
   * Part of the contacted prospects, for the meter under a figure.
   * @param count - Prospects at the stage.
   * @param contacted - Prospects contacted.
   * @returns The ratio, 0 when nobody was contacted.
   */
  private static ratioOf(count: number, contacted: number): number {
    return contacted > 0 ? count / contacted : 0
  }

  /**
   * A rate against the same rate of the comparison, in points.
   * @param count - Prospects at the stage in this campaign.
   * @param contacted - Prospects contacted in this campaign.
   * @param comparison - What the rate is compared against, null for nothing.
   * @param stage - The compared stage.
   * @returns The badge and the reference note, empty without a comparison.
   */
  private static comparisonOf(
    count: number,
    contacted: number,
    comparison: CampaignResultsComparison | null,
    stage: Exclude<CampaignResultsStage, 'contacted'>,
  ): CampaignResultsKpiComparison {
    if (!comparison || contacted === 0 || comparison.contacted === 0) return { trendBadge: null, comparisonNote: '' }
    const referenceRate: number = comparison[stage] / comparison.contacted
    const referenceLabel: string = comparison.referenceLabel ? ` ${comparison.referenceLabel}` : ''
    return {
      trendBadge: CampaignResultsSummary.trendBadgeOf(count / contacted - referenceRate),
      comparisonNote: `vs ${CampaignResultsFormat.wholePercent(referenceRate)} %${referenceLabel}`,
    }
  }

  /**
   * The badge of a difference of rates, in points.
   * @param rateDifference - This campaign's rate minus the reference rate.
   * @returns « +8 pts » going up, « −3 pts » going down, « Pareil » when it rounds to nothing.
   */
  private static trendBadgeOf(rateDifference: number): UiKpiBandTrendBadge {
    const points: number = CampaignResultsFormat.wholePercent(rateDifference)
    if (points === 0) return { trend: 'flat', text: 'Pareil' }
    if (points > 0) return { trend: 'up', text: `+${points} pts` }
    return { trend: 'down', text: `−${Math.abs(points)} pts` }
  }

  /**
   * The facts about the messages: those to come while the campaign runs, else those sent, none before the first one.
   * @param totals - The campaign's totals.
   * @param planned - The planned sends, the soonest first.
   * @param words - The words of the campaign's channel.
   * @returns The facts.
   */
  private static sendFacts(
    totals: CampaignResultsTotals,
    planned: CampaignResultsPlannedSend[],
    words: CampaignChannelWords,
  ): CampaignResultsStateFact[] {
    if (planned.length > 0) return CampaignResultsSummary.plannedSendFacts(planned)
    if (totals.first_mails_sent + totals.follow_ups_sent === 0) return []
    return [CampaignResultsSummary.messagesSentFact(totals, words)]
  }

  /**
   * The facts of a running campaign: next send, follow-ups to come and last planned send.
   * @param planned - The planned sends, the soonest first.
   * @returns The facts.
   */
  private static plannedSendFacts(planned: CampaignResultsPlannedSend[]): CampaignResultsStateFact[] {
    const facts: CampaignResultsStateFact[] = []
    const nextSend: CampaignResultsPlannedSend | undefined = planned[0]
    const lastSend: CampaignResultsPlannedSend | undefined = planned[planned.length - 1]
    if (!nextSend || !lastSend) return facts
    facts.push({ label: 'Prochain envoi', value: formatScheduledMoment(nextSend.at), detail: nextSend.prospectName })
    const followUps: CampaignResultsPlannedSend[] = planned.filter(
      (send: CampaignResultsPlannedSend): boolean => send.step > 0,
    )
    const firstFollowUp: CampaignResultsPlannedSend | undefined = followUps[0]
    if (firstFollowUp) {
      facts.push({
        label: 'Relances prévues',
        value: String(followUps.length),
        detail: `la première ${formatScheduledMoment(firstFollowUp.at)}`,
      })
    }
    if (planned.length > 1) {
      facts.push({
        label: 'Dernier envoi prévu',
        value: CampaignResultsFormat.shortWeekday(lastSend.at),
        detail: lastSend.prospectName,
      })
    }
    return facts
  }

  /**
   * The messages a finished campaign sent.
   * @param totals - The campaign's totals.
   * @param words - The words of the campaign's channel.
   * @returns The fact.
   */
  private static messagesSentFact(
    totals: CampaignResultsTotals,
    words: CampaignChannelWords,
  ): CampaignResultsStateFact {
    const firstMessages: string = CampaignResultsFormat.count(
      totals.first_mails_sent,
      `premier ${words.messageNoun}`,
      `premiers ${words.messagesNoun}`,
    )
    const parts: string[] = [firstMessages]
    if (totals.follow_ups_sent > 0) parts.push(CampaignResultsFormat.count(totals.follow_ups_sent, 'relance'))
    return {
      label: `${CampaignResultsFormat.capitalize(words.messagesNoun)} envoyés`,
      value: String(totals.first_mails_sent + totals.follow_ups_sent),
      detail: parts.join(', '),
    }
  }

  /**
   * The prospects one of whose mails bounced.
   * @param rows - The campaign's rows.
   * @returns Their names, the first two then an ellipsis.
   */
  private static bouncedNames(rows: CampaignResultsRow[]): string {
    const names: string[] = rows
      .filter((row: CampaignResultsRow): boolean =>
        row.prospect.sends.some((send: CampaignResultsSend): boolean => send.is_bounced),
      )
      .map((row: CampaignResultsRow): string => row.prospect.name)
    if (names.length > DETAIL_NAMES_LIMIT) return `${names.slice(0, DETAIL_NAMES_LIMIT).join(', ')}…`
    return CampaignResultsFormat.nameList(names)
  }

  /**
   * The last time a mail of the campaign left.
   * @param rows - The campaign's rows.
   * @returns The moment, or null when no mail left.
   */
  private static lastSentAt(rows: CampaignResultsRow[]): Date | null {
    let latestTime: number | null = null
    for (const row of rows) {
      for (const send of row.prospect.sends) {
        if (send.status !== 'sent') continue
        const sentTime: number = parseApiDate(send.at).getTime()
        if (latestTime === null || sentTime > latestTime) latestTime = sentTime
      }
    }
    return latestTime === null ? null : new Date(latestTime)
  }

  /**
   * Each interested prospect with their latest interested reply, the most recent reply first.
   * @param rows - The campaign's rows.
   * @returns The prospects and their replies.
   */
  private static latestInterestedReplies(rows: CampaignResultsRow[]): CampaignResultsRowReply[] {
    const interestedReplies: CampaignResultsRowReply[] = []
    for (const row of rows) {
      if (row.prospect.state !== 'interested') continue
      const reply: CampaignResultsReply | null = CampaignResultsSummary.latestReply(row, 'interested')
      if (reply) interestedReplies.push({ row, reply })
    }
    return interestedReplies.sort(
      (first: CampaignResultsRowReply, second: CampaignResultsRowReply): number =>
        parseApiDate(second.reply.received_at).getTime() - parseApiDate(first.reply.received_at).getTime(),
    )
  }

  /**
   * Whether an interested prospect already answered still waits for a next step, a month at most.
   * @param reply - The prospect's interested reply.
   * @param now - The current moment.
   * @returns True for a handled reply of less than a month.
   */
  private static isAwaitingFollowUp(reply: CampaignResultsReply, now: Date): boolean {
    if (!reply.is_handled) return false
    const replyAge: number = now.getTime() - parseApiDate(reply.received_at).getTime()
    return replyAge <= INTERESTED_FOLLOW_UP_DAYS * MILLISECONDS_PER_DAY
  }

  /**
   * A prospect's latest reply of a verdict.
   * @param row - The prospect row.
   * @param verdict - The verdict to look for.
   * @returns The reply, or null when the prospect never replied so.
   */
  private static latestReply(
    row: CampaignResultsRow,
    verdict: CampaignResultsReplyVerdict,
  ): CampaignResultsReply | null {
    let latestReply: CampaignResultsReply | null = null
    for (const reply of row.replies) {
      if (reply.verdict !== verdict) continue
      const isLater: boolean =
        !latestReply || parseApiDate(reply.received_at).getTime() > parseApiDate(latestReply.received_at).getTime()
      if (isLater) latestReply = reply
    }
    return latestReply
  }

  /**
   * The words of a reply between quotes, or what it was when it had none.
   * @param reply - The reply.
   * @returns The quote.
   */
  private static replyQuote(reply: CampaignResultsReply): string {
    if (reply.excerpt) return `« ${reply.excerpt} »`
    if (reply.channel === 'banner') return 'Message laissé sur son site, sans texte.'
    return 'Réponse sans texte.'
  }

  /**
   * A to-do entry for a reply still to deal with.
   * @param row - The prospect row.
   * @param reply - The reply.
   * @param tone - The entry's tone, after the reply's verdict.
   * @returns The entry.
   */
  private static replyTodo(
    row: CampaignResultsRow,
    reply: CampaignResultsReply,
    tone: CampaignResultsTodoTone,
  ): CampaignResultsTodo {
    const isRefusal: boolean = reply.verdict === 'refused'
    const receivedAgo: string = formatRelativeTime(reply.received_at).toLocaleLowerCase('fr-FR')
    return {
      key: `reply-${reply.id}`,
      tone,
      icon: isRefusal ? 'i-lucide-circle-x' : 'i-lucide-message-circle',
      title: `${row.prospect.name} ${isRefusal ? 'a refusé' : 'a répondu'}`,
      verdict: isRefusal ? null : reply.verdict,
      text: `${CampaignResultsSummary.replyQuote(reply)} · ${receivedAgo}`,
      actionLabel: 'Ouvrir la fiche',
      action: { kind: 'prospect', prospectId: row.prospect.id },
    }
  }

  /**
   * A to-do entry for an interested prospect already answered, who has not bought yet.
   * @param row - The prospect row.
   * @param reply - The prospect's interested reply.
   * @returns The entry.
   */
  private static awaitingFollowUpTodo(row: CampaignResultsRow, reply: CampaignResultsReply): CampaignResultsTodo {
    const receivedAt: Date = parseApiDate(reply.received_at)
    return {
      key: `awaiting-${row.prospect.id}`,
      tone: 'green',
      icon: 'i-lucide-calendar-clock',
      title: `${row.prospect.name} attend une suite`,
      verdict: null,
      text: `Intéressé le ${CampaignResultsFormat.numericDay(receivedAt)} : ${CampaignResultsSummary.replyQuote(reply)}`,
      actionLabel: 'Ouvrir la fiche',
      action: { kind: 'prospect', prospectId: row.prospect.id },
    }
  }

  /**
   * The to-do entry of the prospects who visited their site without writing, grouped when there are several.
   * @param rows - The campaign's rows.
   * @param words - The words of the campaign's channel.
   * @returns The entry, or null when no prospect is in that case.
   */
  private static visitorsTodo(rows: CampaignResultsRow[], words: CampaignChannelWords): CampaignResultsTodo | null {
    const visitors: CampaignResultsRow[] = rows
      .filter((row: CampaignResultsRow): boolean => row.prospect.state === 'visited')
      .sort(
        (first: CampaignResultsRow, second: CampaignResultsRow): number =>
          second.visitCount - first.visitCount || second.activeSeconds - first.activeSeconds,
      )
    const leader: CampaignResultsRow | undefined = visitors[0]
    if (!leader) return null
    const areFollowUpsPlanned: boolean = visitors.every((row: CampaignResultsRow): boolean =>
      row.prospect.sends.some((send: CampaignResultsSend): boolean => send.step > 0 && send.status === 'planned'),
    )
    if (visitors.length === 1) {
      const advice: string = areFollowUpsPlanned ? 'Sa relance est déjà prévue.' : words.visitorWithoutReplyAdvice
      return {
        key: 'visitors',
        tone: 'blue',
        icon: 'i-lucide-eye',
        title: `${leader.prospect.name} a visité son site sans écrire`,
        verdict: null,
        text: `${CampaignResultsSummary.visitsOnPage(leader)}. ${advice}`,
        actionLabel: 'Ouvrir la fiche',
        action: { kind: 'prospect', prospectId: leader.prospect.id },
      }
    }
    const leaders: string[] = visitors
      .slice(0, SENTENCE_NAMES_LIMIT)
      .map((row: CampaignResultsRow): string => CampaignResultsSummary.nameWithVisits(row))
    const advice: string = areFollowUpsPlanned ? 'Leurs relances sont déjà prévues.' : words.visitorWithoutReplyAdvice
    return {
      key: 'visitors',
      tone: 'blue',
      icon: 'i-lucide-eye',
      title: `${visitors.length} prospects ont visité leur site sans écrire`,
      verdict: null,
      text: `${CampaignResultsFormat.nameList(leaders)} en tête. ${advice}`,
      actionLabel: `Voir les ${visitors.length}`,
      action: { kind: 'filter', filter: 'toRelaunch' },
    }
  }

  /**
   * A prospect's visits and the time their site stayed in front of them.
   * @param row - The prospect row.
   * @returns « 3 visites, 2 min 43 sur la page ».
   */
  private static visitsOnPage(row: CampaignResultsRow): string {
    const visits: string = CampaignResultsFormat.count(row.visitCount, 'visite')
    if (row.activeSeconds === 0) return visits
    return `${visits}, ${CampaignResultsFormat.activeTime(row.activeSeconds)} sur la page`
  }

  /**
   * A prospect's name, with their visits when they came back.
   * @param row - The prospect row.
   * @returns « Urgence SOS (3 visites) », or the name alone after one visit.
   */
  private static nameWithVisits(row: CampaignResultsRow): string {
    if (row.visitCount <= 1) return row.prospect.name
    return `${row.prospect.name} (${CampaignResultsFormat.count(row.visitCount, 'visite')})`
  }

  /**
   * The to-do entry of a prospect whose mail bounced, or whose SMS never arrived, while nothing came back from them.
   * @param row - The prospect row.
   * @param words - The words of the campaign's channel.
   * @returns The entry, or null when every message arrived or the prospect answered anyway.
   */
  private static bouncedTodo(row: CampaignResultsRow, words: CampaignChannelWords): CampaignResultsTodo | null {
    const hasBounced: boolean = row.prospect.sends.some((send: CampaignResultsSend): boolean => send.is_bounced)
    const isWithoutAnswer: boolean = row.prospect.state === 'visited' || row.prospect.state === 'silent'
    if (!hasBounced || !isWithoutAnswer) return null
    const sentences: string[] = []
    if (row.visitCount > 0) {
      const visits: string = CampaignResultsFormat.count(row.visitCount, 'fois', 'fois')
      sentences.push(`${words.failedDeliverySentence}, mais le site a été ouvert ${visits} depuis.`)
    } else {
      sentences.push(`${words.failedDeliverySentence}.`)
    }
    const nextFollowUp: CampaignResultsSend | undefined = row.prospect.sends.find(
      (send: CampaignResultsSend): boolean => send.step > 0 && send.status === 'planned',
    )
    if (nextFollowUp) {
      sentences.push(`Prochaine relance ${formatScheduledMoment(parseApiDate(nextFollowUp.at))}.`)
    }
    return {
      key: `bounce-${row.prospect.id}`,
      tone: 'amber',
      icon: words.failedDeliveryIcon,
      title: `${row.prospect.name} : ${words.contactToCheckLabel}`,
      verdict: null,
      text: sentences.join(' '),
      actionLabel: 'Ouvrir la fiche',
      action: { kind: 'prospect', prospectId: row.prospect.id },
    }
  }

  /**
   * When the campaign's demo sites still online expire.
   * @param results - The campaign's results.
   * @returns « expirent du 13 au 19 oct. », « expire le 13 oct. », or a note when no countdown started.
   */
  private static demoExpiryDetail(results: CampaignResultsResponse): string {
    const {
      online,
      first_expiry_at: firstExpiryAt,
      last_expiry_at: lastExpiryAt,
    }: CampaignResultsResponse['demo_sites'] = results.demo_sites
    if (!firstExpiryAt || !lastExpiryAt) return "sans date d'expiration"
    const firstExpiry: Date = parseApiDate(firstExpiryAt)
    const lastExpiry: Date = parseApiDate(lastExpiryAt)
    if (CampaignResults.dayKey(firstExpiry) === CampaignResults.dayKey(lastExpiry)) {
      const verb: string = CampaignResultsFormat.agreeWithCount(online, 'expire', 'expirent')
      return `${verb} le ${CampaignResultsFormat.shortDay(firstExpiry)}`
    }
    const isSameMonth: boolean =
      firstExpiry.getMonth() === lastExpiry.getMonth() && firstExpiry.getFullYear() === lastExpiry.getFullYear()
    const from: string = isSameMonth
      ? CampaignResultsFormat.dayOfMonth(firstExpiry)
      : CampaignResultsFormat.shortDay(firstExpiry)
    return `expirent du ${from} au ${CampaignResultsFormat.shortDay(lastExpiry)}`
  }
}
