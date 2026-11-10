import { defineStore, skipHydrate } from 'pinia'
import type { ComputedRef, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type {
  DrawerStackChangeChannel,
  DrawerStackChangeNotices,
  DrawerStackEntry,
  DrawerStackEntryKind,
  OrderMutationNotice,
  ProspectMutationNotice,
} from '~/types/DrawerStack'
import type { Order } from '~/services/ordersService'
import type { EmailTemplate, Prospect } from '~/types'
import { DrawerKindRegistry } from '~/utils/drawerKindRegistry'

/** sessionStorage key persisting the drawer stack across page reloads. */
const DRAWER_STACK_STORAGE_KEY: string = 'dlh-drawer-stack'

const PAGE_INDEPENDENT_DRAWER_KINDS: DrawerStackEntryKind[] = ['prospect-search', 'prospect-search-lead']

/**
 * Whether a stored entry can be shown again: a retired kind, or the drawer of a module no longer installed, is not.
 * @param entry - An entry read back from the session.
 * @returns True when its kind is the core's or a registered module's.
 */
function isRestorableEntry(entry: unknown): entry is DrawerStackEntry {
  if (typeof entry !== 'object' || entry === null || !('kind' in entry)) {
    return false
  }
  return typeof entry.kind === 'string' && DrawerKindRegistry.isKnownKind(entry.kind)
}

/** Pinia store driving the persistent right-side drawer stack (survives route changes via `UiDrawerStackHost`). */
// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useDrawerStackStore = defineStore('drawerStack', () => {
  // State — restored from sessionStorage so an open drawer survives a reload.
  const stack: Ref<DrawerStackEntry[]> = ref([])
  if (import.meta.client) {
    try {
      const raw: string | null = sessionStorage.getItem(DRAWER_STACK_STORAGE_KEY)
      const stored: unknown = raw ? JSON.parse(raw) : null
      if (Array.isArray(stored)) {
        stack.value = stored.filter(isRestorableEntry)
      }
    } catch {
      // État illisible → on repart d'une pile vide.
    }
  }
  const lastProspectMutation: Ref<ProspectMutationNotice | null> = ref(null)
  const prospectMutationCounter: Ref<number> = ref(0)
  // Volontairement hors sessionStorage : sert seulement à naviguer entre voisins pendant la session.
  const prospectBrowseList: Ref<Prospect[]> = ref([])
  const emailTemplateBrowseList: Ref<EmailTemplate[]> = ref([])
  const lastOrderMutation: Ref<OrderMutationNotice | null> = ref(null)
  const orderMutationCounter: Ref<number> = ref(0)
  const changeCounts: Ref<Record<string, number>> = ref({})
  const latestChangeNotices: Ref<Partial<DrawerStackChangeNotices>> = ref({})
  const emailLogsRefreshCounter: Ref<number> = ref(0)
  const smsMessagesRefreshCounter: Ref<number> = ref(0)
  const emailTemplatesRefreshCounter: Ref<number> = ref(0)
  const usersRefreshCounter: Ref<number> = ref(0)
  const campaignsRefreshCounter: Ref<number> = ref(0)
  const campaignResultsRefreshCounter: Ref<number> = ref(0)

  // Getters
  const topEntry: ComputedRef<DrawerStackEntry | null> = computed(
    (): DrawerStackEntry | null => stack.value[stack.value.length - 1] ?? null,
  )

  const hasPrevious: ComputedRef<boolean> = computed((): boolean => stack.value.length > 1)

  /**
   * Open a drawer. Pushing the same kind as the current top replaces it
   * (e.g. clicking prospect B while prospect A is open); a different kind
   * stacks on top (e.g. « envoyer un email » over a prospect).
   * @param entry - Drawer entry to display.
   */
  function push(entry: DrawerStackEntry): void {
    const top: DrawerStackEntry | undefined = stack.value[stack.value.length - 1]
    if (top && top.kind === entry.kind) {
      stack.value.splice(stack.value.length - 1, 1, entry)
      return
    }
    stack.value.push(entry)
  }

  /** Go back to the previous drawer (pops the top entry). */
  function back(): void {
    stack.value.pop()
  }

  /** Close every drawer, and forget the lists the drawers were browsing. */
  function closeAll(): void {
    stack.value = []
    prospectBrowseList.value = []
    emailTemplateBrowseList.value = []
  }

  /**
   * Leave a page: the drawers that follow the user stay open, the ones of the page left close.
   */
  function keepPageIndependentEntries(): void {
    const followingEntries: DrawerStackEntry[] = stack.value.filter((entry: DrawerStackEntry): boolean =>
      PAGE_INDEPENDENT_DRAWER_KINDS.includes(entry.kind),
    )
    if (followingEntries.length === 0) {
      closeAll()
      return
    }
    stack.value = followingEntries
  }

  /**
   * Remember the list the prospect drawer browses, so it can step to its neighbours.
   * @param list - Prospects in the order they are displayed by the calling page.
   */
  function setProspectBrowseList(list: Prospect[]): void {
    prospectBrowseList.value = list
  }

  /**
   * Remember the list the email template preview browses, so it can step to its neighbours.
   * @param list - Templates in the order they are displayed by the calling page.
   */
  function setEmailTemplateBrowseList(list: EmailTemplate[]): void {
    emailTemplateBrowseList.value = list
  }

  /**
   * Broadcast a prospect update: refresh matching stacked entries and notify
   * pages watching `prospectMutationCounter`.
   * @param prospect - The freshly updated prospect.
   */
  function notifyProspectUpdated(prospect: Prospect): void {
    stack.value = stack.value.map((entry: DrawerStackEntry): DrawerStackEntry => {
      if (entry.kind === 'prospect' && entry.prospect.id === prospect.id) {
        return { ...entry, prospect }
      }
      if (entry.kind === 'prospect-settings' && entry.prospect.id === prospect.id) {
        return { ...entry, prospect }
      }
      if (entry.kind === 'send-email' && entry.prospect?.id === prospect.id) {
        return { ...entry, prospect }
      }
      if (entry.kind === 'send-sms' && entry.prospect?.id === prospect.id) {
        return { ...entry, prospect }
      }
      return entry
    })
    lastProspectMutation.value = { type: 'updated', prospect }
    prospectMutationCounter.value++
  }

  /**
   * Broadcast an order update: refresh matching stacked entries and notify
   * pages watching `orderMutationCounter`.
   * @param order - The freshly updated order.
   */
  function notifyOrderUpdated(order: Order): void {
    stack.value = stack.value.map((entry: DrawerStackEntry): DrawerStackEntry => {
      if (entry.kind === 'order' && entry.order?.id === order.id) {
        return { ...entry, order, mode: 'view' }
      }
      if (entry.kind === 'finalize-sale' && entry.order.id === order.id) {
        return { ...entry, order }
      }
      return entry
    })
    lastOrderMutation.value = { type: 'updated', order }
    orderMutationCounter.value++
  }

  /**
   * Broadcast an order deletion: drop matching stacked entries and notify
   * pages watching `orderMutationCounter`.
   * @param orderId - Identifier of the deleted order.
   */
  function notifyOrderDeleted(orderId: number): void {
    stack.value = stack.value.filter((entry: DrawerStackEntry): boolean => {
      const isSameOrder: boolean =
        (entry.kind === 'order' && entry.order?.id === orderId) ||
        (entry.kind === 'finalize-sale' && entry.order.id === orderId)
      return !isSameOrder
    })
    lastOrderMutation.value = { type: 'deleted', orderId }
    orderMutationCounter.value++
  }

  /**
   * Replace, or drop, the stacked entries a change touches (a module refreshes its own drawers' entries this way).
   * @param transform - Returns the entry as it should now read, the same entry when untouched, or null to drop it.
   */
  function replaceEntries(transform: (entry: DrawerStackEntry) => DrawerStackEntry | null): void {
    stack.value = stack.value.flatMap((entry: DrawerStackEntry): DrawerStackEntry[] => {
      const replacement: DrawerStackEntry | null = transform(entry)
      return replacement === null ? [] : [replacement]
    })
  }

  /**
   * Broadcast a module's change to the pages watching its channel.
   * @param channel - The channel the module declared in `DrawerStackChangeNotices`.
   * @param notice - What changed.
   */
  function broadcastChange<TChannel extends DrawerStackChangeChannel>(
    channel: TChannel,
    notice: DrawerStackChangeNotices[TChannel],
  ): void {
    latestChangeNotices.value[channel] = notice
    changeCounts.value[channel] = changeCountOf(channel) + 1
  }

  /**
   * How many changes a channel broadcast so far: pages watch it to apply the latest one.
   * @param channel - The module's channel.
   * @returns The count, 0 before the first change.
   */
  function changeCountOf(channel: DrawerStackChangeChannel): number {
    return changeCounts.value[channel] ?? 0
  }

  /**
   * The latest change broadcast on a channel.
   * @param channel - The module's channel.
   * @returns The notice, or null before the first change.
   */
  function latestChangeOf<TChannel extends DrawerStackChangeChannel>(
    channel: TChannel,
  ): DrawerStackChangeNotices[TChannel] | null {
    return latestChangeNotices.value[channel] ?? null
  }

  /** Signal that email logs changed (an email was sent from a drawer). */
  function bumpEmailLogsRefresh(): void {
    emailLogsRefreshCounter.value++
  }

  /** Signal that SMS messages changed (an SMS was sent from a drawer). */
  function bumpSmsMessagesRefresh(): void {
    smsMessagesRefreshCounter.value++
  }

  /** Signal that email templates changed (created/edited/deleted from a drawer). */
  function bumpEmailTemplatesRefresh(): void {
    emailTemplatesRefreshCounter.value++
  }

  /**
   * Broadcast a prospect deletion: drop matching stacked entries and notify
   * pages watching `prospectMutationCounter`.
   * @param prospectId - Identifier of the deleted prospect.
   */
  function notifyProspectDeleted(prospectId: number): void {
    stack.value = stack.value.filter((entry: DrawerStackEntry): boolean => {
      const isSameProspect: boolean =
        (entry.kind === 'prospect' && entry.prospect.id === prospectId) ||
        (entry.kind === 'send-email' && entry.prospect?.id === prospectId) ||
        (entry.kind === 'send-sms' && entry.prospect?.id === prospectId)
      return !isSameProspect
    })
    lastProspectMutation.value = { type: 'deleted', prospectId }
    prospectMutationCounter.value++
  }

  /** Signal that users changed (created or edited from a drawer). */
  function bumpUsersRefresh(): void {
    usersRefreshCounter.value++
  }

  /** Signal that campaigns changed (created or edited from a drawer). */
  function bumpCampaignsRefresh(): void {
    campaignsRefreshCounter.value++
  }

  /** Signal that a campaign's results changed (a reply added by hand from a drawer). */
  function bumpCampaignResultsRefresh(): void {
    campaignResultsRefreshCounter.value++
  }

  // Persister chaque mutation de la pile (F5 ne ferme plus les drawers).
  watch(
    stack,
    (value: DrawerStackEntry[]): void => {
      if (!import.meta.client) return
      try {
        sessionStorage.setItem(DRAWER_STACK_STORAGE_KEY, JSON.stringify(value))
      } catch {
        // Quota plein ou storage indisponible : la persistance est best-effort.
      }
    },
    { deep: true },
  )

  return {
    // skipHydrate : l'état SSR, toujours vide, écraserait la pile restaurée du sessionStorage.
    stack: skipHydrate(stack),
    lastProspectMutation,
    prospectMutationCounter,
    prospectBrowseList,
    emailTemplateBrowseList,
    lastOrderMutation,
    orderMutationCounter,
    changeCounts,
    latestChangeNotices,
    emailLogsRefreshCounter,
    smsMessagesRefreshCounter,
    emailTemplatesRefreshCounter,
    usersRefreshCounter,
    campaignsRefreshCounter,
    campaignResultsRefreshCounter,
    topEntry,
    hasPrevious,
    push,
    back,
    closeAll,
    keepPageIndependentEntries,
    setProspectBrowseList,
    setEmailTemplateBrowseList,
    notifyProspectUpdated,
    notifyProspectDeleted,
    notifyOrderUpdated,
    notifyOrderDeleted,
    replaceEntries,
    broadcastChange,
    changeCountOf,
    latestChangeOf,
    bumpEmailLogsRefresh,
    bumpSmsMessagesRefresh,
    bumpEmailTemplatesRefresh,
    bumpUsersRefresh,
    bumpCampaignsRefresh,
    bumpCampaignResultsRefresh,
  }
})
