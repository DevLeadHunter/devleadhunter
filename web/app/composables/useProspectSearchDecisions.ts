import type { UseProspectSearchDecisionsReturn, UseToastReturn } from '~/types/Composables'
import type {
  ProspectSearchCandidate,
  ProspectSearchDecisionsResult,
  ProspectSearchRefusedDecision,
} from '~/types/ProspectSearch'
import { useToast } from '~/composables/useToast'
import { MY_PROSPECTS_PAGE_PATH } from '~/constants/prospectSearch'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useProspectSearchStore } from '~/stores/prospectSearch'

/**
 * Decisions on the leads a search proposes: each one is told by a toast, and a refusal can be taken back.
 * @returns The accept / refuse actions, and the two ways to look at a lead.
 */
export function useProspectSearchDecisions(): UseProspectSearchDecisionsReturn {
  const store: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()
  const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
  const router: ReturnType<typeof useRouter> = useRouter()
  const toast: UseToastReturn = useToast()

  /**
   * Write « n lead(s) » with its agreement.
   * @param count - How many leads.
   * @param singular - Words following a single lead.
   * @param plural - Words following several leads.
   * @returns E.g. « 3 leads refusés ».
   */
  function buildLeadCountLabel(count: number, singular: string, plural: string): string {
    return count > 1 ? `${count} leads ${plural}` : `1 lead ${singular}`
  }

  /**
   * Tell the decisions the server did not apply.
   * @param refusals - The refused decisions, with their reason.
   */
  function reportRefusals(refusals: ProspectSearchRefusedDecision[]): void {
    const firstRefusal: ProspectSearchRefusedDecision | undefined = refusals[0]
    if (!firstRefusal) return
    toast.error(`${buildLeadCountLabel(refusals.length, 'non traité', 'non traités')} : ${firstRefusal.detail}`)
  }

  /**
   * Take back a refusal: the leads wait for a decision again.
   * @param candidates - The leads refused a moment ago.
   * @returns A promise resolved once the refusal is taken back, or the failure is reported.
   */
  async function undoRefusal(candidates: ProspectSearchCandidate[]): Promise<void> {
    const restoredCount: number = await store.restoreRefusedCandidates(candidates)
    const onlyCandidate: ProspectSearchCandidate | undefined = candidates.length === 1 ? candidates[0] : undefined
    if (restoredCount === 0) {
      toast.error('Ce refus ne peut plus être annulé')
      return
    }
    toast.success(
      onlyCandidate
        ? `Refus annulé : « ${onlyCandidate.name} » est de nouveau à valider`
        : `Refus annulé : ${restoredCount > 1 ? `${restoredCount} leads` : '1 lead'} de nouveau à valider`,
    )
  }

  /**
   * Accept a lead: it becomes a prospect.
   * @param candidate - The lead to accept.
   * @returns True once the lead is a prospect.
   */
  async function acceptLead(candidate: ProspectSearchCandidate): Promise<boolean> {
    try {
      if (!(await store.acceptCandidate(candidate))) return false
      toast.success(`« ${candidate.name} » ajouté à vos prospects`)
      return true
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Impossible d'accepter ce lead")
      return false
    }
  }

  /**
   * Refuse a lead; the toast offers to take the refusal back for a few seconds.
   * @param candidate - The lead to refuse.
   * @returns True once the lead is refused.
   */
  async function rejectLead(candidate: ProspectSearchCandidate): Promise<boolean> {
    try {
      if (!(await store.rejectCandidate(candidate))) return false
      toast.info(`« ${candidate.name} » refusé`, {
        action: {
          label: 'Annuler',
          onSelect: (): void => {
            undoRefusal([candidate])
          },
        },
      })
      return true
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Impossible de refuser ce lead')
      return false
    }
  }

  /**
   * Accept several leads at once.
   * @param candidates - The leads to accept.
   * @returns A promise resolved once the decisions are sent and told.
   */
  async function acceptLeads(candidates: ProspectSearchCandidate[]): Promise<void> {
    const onlyCandidate: ProspectSearchCandidate | undefined = candidates.length === 1 ? candidates[0] : undefined
    if (onlyCandidate) {
      await acceptLead(onlyCandidate)
      return
    }
    try {
      const result: ProspectSearchDecisionsResult = await store.decideCandidates(
        candidates.map((candidate: ProspectSearchCandidate): number => candidate.id),
        [],
      )
      if (result.accepted > 0) {
        toast.success(`${buildLeadCountLabel(result.accepted, 'ajouté', 'ajoutés')} à vos prospects`)
      }
      reportRefusals(result.refused)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Impossible d'accepter ces leads")
    }
  }

  /**
   * Refuse several leads at once; the toast offers to take the refusals back for a few seconds.
   * @param candidates - The leads to refuse.
   * @returns A promise resolved once the decisions are sent and told.
   */
  async function rejectLeads(candidates: ProspectSearchCandidate[]): Promise<void> {
    const onlyCandidate: ProspectSearchCandidate | undefined = candidates.length === 1 ? candidates[0] : undefined
    if (onlyCandidate) {
      await rejectLead(onlyCandidate)
      return
    }
    try {
      const result: ProspectSearchDecisionsResult = await store.decideCandidates(
        [],
        candidates.map((candidate: ProspectSearchCandidate): number => candidate.id),
      )
      const untouchedIds: Set<number> = new Set(
        result.refused.map((refusal: ProspectSearchRefusedDecision): number => refusal.candidate_id),
      )
      const rejectedCandidates: ProspectSearchCandidate[] = candidates.filter(
        (candidate: ProspectSearchCandidate): boolean => !untouchedIds.has(candidate.id),
      )
      if (result.rejected > 0) {
        toast.info(buildLeadCountLabel(result.rejected, 'refusé', 'refusés'), {
          action: {
            label: 'Annuler',
            onSelect: (): void => {
              undoRefusal(rejectedCandidates)
            },
          },
        })
      }
      reportRefusals(result.refused)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Impossible de refuser ces leads')
    }
  }

  /**
   * Open the record of a lead, stacked as a drawer that walks the list it was opened from.
   * @param candidate - The lead to show.
   * @param browsedCandidates - The list the opener displays; every waiting lead when omitted.
   */
  function openLead(candidate: ProspectSearchCandidate, browsedCandidates?: ProspectSearchCandidate[]): void {
    store.setLeadBrowseList(
      (browsedCandidates ?? store.pendingCandidates).map((browsed: ProspectSearchCandidate): number => browsed.id),
    )
    drawerStack.push({ kind: 'prospect-search-lead', candidate })
  }

  /**
   * Show every lead waiting for a decision: the « À valider » tab of the prospects page.
   * @returns A promise resolved once the page is displayed.
   */
  async function showPendingLeads(): Promise<void> {
    store.requestPendingTab()
    if (router.currentRoute.value.path !== MY_PROSPECTS_PAGE_PATH) await navigateTo(MY_PROSPECTS_PAGE_PATH)
  }

  return { acceptLead, rejectLead, acceptLeads, rejectLeads, openLead, showPendingLeads }
}
