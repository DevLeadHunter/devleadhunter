import { defineStore, skipHydrate } from 'pinia'
import type { ComputedRef, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type { DrawerStackEntry, ProspectMutationNotice } from '~/types/DrawerStack'
import type { Prospect } from '~/types'

/** sessionStorage key persisting the drawer stack across page reloads. */
const DRAWER_STACK_STORAGE_KEY = 'dlh-drawer-stack'

/** Pinia store driving the persistent right-side drawer stack (survives route changes via `UiDrawerStackHost`). */
export const useDrawerStackStore = defineStore('drawerStack', () => {
  // State — restored from sessionStorage so an open drawer survives a reload.
  const stack: Ref<DrawerStackEntry[]> = ref([])
  if (import.meta.client) {
    try {
      const raw: string | null = sessionStorage.getItem(DRAWER_STACK_STORAGE_KEY)
      if (raw) stack.value = JSON.parse(raw) as DrawerStackEntry[]
    } catch {
      // État illisible → on repart d'une pile vide.
    }
  }
  const lastProspectMutation: Ref<ProspectMutationNotice | null> = ref(null)
  const prospectMutationCounter: Ref<number> = ref(0)
  const emailLogsRefreshCounter: Ref<number> = ref(0)
  const emailTemplatesRefreshCounter: Ref<number> = ref(0)

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

  /** Close every drawer. */
  function closeAll(): void {
    stack.value = []
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
      if (entry.kind === 'send-email' && entry.prospect?.id === prospect.id) {
        return { ...entry, prospect }
      }
      return entry
    })
    lastProspectMutation.value = { type: 'updated', prospect }
    prospectMutationCounter.value++
  }

  /**
   * Broadcast a prospect deletion: drop matching stacked entries and notify
   * pages watching `prospectMutationCounter`.
   * @param prospectId - Identifier of the deleted prospect.
   */
  function notifyProspectDeleted(prospectId: number): void {
    stack.value = stack.value.filter(
      (entry: DrawerStackEntry): boolean => !(entry.kind === 'prospect' && entry.prospect.id === prospectId),
    )
    lastProspectMutation.value = { type: 'deleted', prospectId }
    prospectMutationCounter.value++
  }

  /** Signal that email logs changed (an email was sent from a drawer). */
  function bumpEmailLogsRefresh(): void {
    emailLogsRefreshCounter.value++
  }

  /** Signal that email templates changed (created/edited/deleted from a drawer). */
  function bumpEmailTemplatesRefresh(): void {
    emailTemplatesRefreshCounter.value++
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
    emailLogsRefreshCounter,
    emailTemplatesRefreshCounter,
    topEntry,
    hasPrevious,
    push,
    back,
    closeAll,
    notifyProspectUpdated,
    notifyProspectDeleted,
    bumpEmailLogsRefresh,
    bumpEmailTemplatesRefresh,
  }
})
