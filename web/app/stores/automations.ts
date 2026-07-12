/**
 * Pinia store for automatisations (the auto-chaining tunnel).
 */
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import type { Automation, AutomationDetail } from '~/types/Automation'
import {
  approveAutomation,
  cancelAutomation,
  deleteAutomation,
  getAutomation,
  listAutomations,
  pauseAutomation,
  resumeAutomation,
} from '~/services/automationsService'

/** Statuses that mean the orchestrator is still working. */
const ACTIVE_STATUSES: ReadonlyArray<string> = ['running', 'awaiting_review']

export const useAutomationsStore = defineStore('automations', () => {
  /** All automatisations of the current user (summary view). */
  const automations: Ref<Automation[]> = ref<Automation[]>([])
  /** The currently opened automatisation (detail / validation). */
  const current: Ref<AutomationDetail | null> = ref<AutomationDetail | null>(null)
  /** Whether the list is loading. */
  const isLoading: Ref<boolean> = ref<boolean>(false)
  /** Last error message, if any. */
  const error: Ref<string | null> = ref<string | null>(null)

  /** Total number of automatisations. */
  const automationsCount: ComputedRef<number> = computed((): number => automations.value.length)

  /** Number of automatisations awaiting the user's validation. */
  const awaitingReviewCount: ComputedRef<number> = computed(
    (): number => automations.value.filter((a: Automation): boolean => a.status === 'awaiting_review').length,
  )

  /** Whether any automatisation (or the open one) is still progressing — drives polling. */
  const hasActive: ComputedRef<boolean> = computed((): boolean => {
    const listActive: boolean = automations.value.some((a: Automation): boolean => ACTIVE_STATUSES.includes(a.status))
    const currentActive: boolean = current.value !== null && ACTIVE_STATUSES.includes(current.value.status)
    return listActive || currentActive
  })

  /**
   * Upsert a summary into the list.
   * @param automation - The automatisation summary.
   */
  function upsert(automation: Automation): void {
    const idx: number = automations.value.findIndex((a: Automation): boolean => a.id === automation.id)
    if (idx === -1) {
      automations.value = [automation, ...automations.value]
    } else {
      automations.value[idx] = automation
    }
  }

  /**
   * Apply a detail returned by an action to the list and the open view.
   * @param detail - The fresh automatisation detail.
   */
  function applyDetail(detail: AutomationDetail): void {
    upsert(detail)
    if (current.value !== null && current.value.id === detail.id) {
      current.value = detail
    }
  }

  /**
   * Load the automatisation list.
   * @returns A promise resolved once loaded.
   */
  async function fetchAll(): Promise<void> {
    try {
      isLoading.value = true
      error.value = null
      const response = await listAutomations()
      automations.value = response.sequences
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Échec du chargement des automatisations'
      automations.value = []
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Load one automatisation's detail into ``current``.
   * @param id - Automatisation identifier.
   * @returns A promise resolved once loaded.
   */
  async function fetchOne(id: number): Promise<void> {
    const detail = await getAutomation(id)
    current.value = detail
    upsert(detail)
  }

  /**
   * Silently refresh the open automatisation and the list (poller).
   * @returns A promise resolved once refreshed.
   */
  async function refreshActive(): Promise<void> {
    if (current.value !== null) {
      applyDetail(await getAutomation(current.value.id))
    } else {
      await fetchAll()
    }
  }

  /** Clear the currently opened automatisation. */
  function clearCurrent(): void {
    current.value = null
  }

  /**
   * Pause an automatisation.
   * @param id - Automatisation identifier.
   * @returns A promise resolved once paused.
   */
  async function pause(id: number): Promise<void> {
    applyDetail(await pauseAutomation(id))
  }

  /**
   * Resume an automatisation.
   * @param id - Automatisation identifier.
   * @returns A promise resolved once resumed.
   */
  async function resume(id: number): Promise<void> {
    applyDetail(await resumeAutomation(id))
  }

  /**
   * Cancel an automatisation.
   * @param id - Automatisation identifier.
   * @returns A promise resolved once cancelled.
   */
  async function cancel(id: number): Promise<void> {
    applyDetail(await cancelAutomation(id))
  }

  /**
   * Approve the review gate.
   * @param id - Automatisation identifier.
   * @returns A promise resolved once approved.
   */
  async function approve(id: number): Promise<void> {
    applyDetail(await approveAutomation(id))
  }

  /**
   * Delete an automatisation and drop it from the store.
   * @param id - Automatisation identifier.
   * @returns A promise resolved once deleted.
   */
  async function remove(id: number): Promise<void> {
    await deleteAutomation(id)
    automations.value = automations.value.filter((a: Automation): boolean => a.id !== id)
    if (current.value !== null && current.value.id === id) {
      current.value = null
    }
  }

  return {
    automations,
    current,
    isLoading,
    error,
    automationsCount,
    awaitingReviewCount,
    hasActive,
    upsert,
    applyDetail,
    fetchAll,
    fetchOne,
    refreshActive,
    clearCurrent,
    pause,
    resume,
    cancel,
    approve,
    remove,
  }
})
