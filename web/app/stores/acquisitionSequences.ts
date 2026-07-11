/**
 * Pinia store for acquisition sequences (the auto-chaining tunnel).
 */
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import type { Sequence, SequenceDetail } from '~/types/AcquisitionSequence'
import {
  approveSequence,
  cancelSequence,
  deleteSequence,
  getSequence,
  listSequences,
  pauseSequence,
  rejectSequenceItem,
  resumeSequence,
} from '~/services/acquisitionSequencesService'

/** Statuses that mean the orchestrator is still working on the sequence. */
const ACTIVE_STATUSES: ReadonlyArray<string> = ['running', 'awaiting_review']

export const useAcquisitionSequencesStore = defineStore('acquisitionSequences', () => {
  /** All sequences of the current user (summary view). */
  const sequences: Ref<Sequence[]> = ref<Sequence[]>([])
  /** The currently opened sequence (pipeline board). */
  const current: Ref<SequenceDetail | null> = ref<SequenceDetail | null>(null)
  /** Whether the list is loading. */
  const isLoading: Ref<boolean> = ref<boolean>(false)
  /** Last error message, if any. */
  const error: Ref<string | null> = ref<string | null>(null)

  /** Total number of sequences. */
  const sequencesCount: ComputedRef<number> = computed((): number => sequences.value.length)

  /** Number of sequences the machine is still working on. */
  const activeCount: ComputedRef<number> = computed(
    (): number => sequences.value.filter((s: Sequence): boolean => ACTIVE_STATUSES.includes(s.status)).length,
  )

  /** Whether any sequence (or the open one) is still progressing — drives polling. */
  const hasActive: ComputedRef<boolean> = computed((): boolean => {
    const listActive: boolean = sequences.value.some((s: Sequence): boolean => ACTIVE_STATUSES.includes(s.status))
    const currentActive: boolean = current.value !== null && ACTIVE_STATUSES.includes(current.value.status)
    return listActive || currentActive
  })

  /**
   * Merge an updated summary into the list (upsert, newest kept in place).
   * @param seq - The sequence summary to upsert.
   */
  function upsert(seq: Sequence): void {
    const idx: number = sequences.value.findIndex((s: Sequence): boolean => s.id === seq.id)
    if (idx === -1) {
      sequences.value = [seq, ...sequences.value]
    } else {
      sequences.value[idx] = seq
    }
  }

  /**
   * Apply a detail returned by an action to both the list and the open board.
   * @param detail - The fresh sequence detail.
   */
  function applyDetail(detail: SequenceDetail): void {
    upsert(detail)
    if (current.value !== null && current.value.id === detail.id) {
      current.value = detail
    }
  }

  /**
   * Load the sequence list.
   * @returns A promise resolved once loaded.
   */
  async function fetchSequences(): Promise<void> {
    try {
      isLoading.value = true
      error.value = null
      const response = await listSequences()
      sequences.value = response.sequences
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Échec du chargement des séquences'
      sequences.value = []
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Load one sequence's detail into ``current``.
   * @param id - Sequence identifier.
   * @returns A promise resolved once loaded.
   */
  async function fetchSequence(id: number): Promise<void> {
    const detail = await getSequence(id)
    current.value = detail
    upsert(detail)
  }

  /**
   * Silently refresh the open sequence and the list (used by the poller).
   * @returns A promise resolved once refreshed.
   */
  async function refreshActive(): Promise<void> {
    if (current.value !== null) {
      const detail = await getSequence(current.value.id)
      applyDetail(detail)
    } else {
      await fetchSequences()
    }
  }

  /** Clear the currently opened sequence. */
  function clearCurrent(): void {
    current.value = null
  }

  /**
   * Pause a sequence.
   * @param id - Sequence identifier.
   * @returns A promise resolved once paused.
   */
  async function pause(id: number): Promise<void> {
    applyDetail(await pauseSequence(id))
  }

  /**
   * Resume a sequence.
   * @param id - Sequence identifier.
   * @returns A promise resolved once resumed.
   */
  async function resume(id: number): Promise<void> {
    applyDetail(await resumeSequence(id))
  }

  /**
   * Cancel a sequence.
   * @param id - Sequence identifier.
   * @returns A promise resolved once cancelled.
   */
  async function cancel(id: number): Promise<void> {
    applyDetail(await cancelSequence(id))
  }

  /**
   * Approve the review gate of a sequence.
   * @param id - Sequence identifier.
   * @returns A promise resolved once approved.
   */
  async function approve(id: number): Promise<void> {
    applyDetail(await approveSequence(id))
  }

  /**
   * Reject a single generated site during review.
   * @param id - Sequence identifier.
   * @param itemId - The item (prospect) to reject.
   * @returns A promise resolved once rejected.
   */
  async function reject(id: number, itemId: number): Promise<void> {
    applyDetail(await rejectSequenceItem(id, itemId))
  }

  /**
   * Delete a sequence and drop it from the store.
   * @param id - Sequence identifier.
   * @returns A promise resolved once deleted.
   */
  async function remove(id: number): Promise<void> {
    await deleteSequence(id)
    sequences.value = sequences.value.filter((s: Sequence): boolean => s.id !== id)
    if (current.value !== null && current.value.id === id) {
      current.value = null
    }
  }

  return {
    sequences,
    current,
    isLoading,
    error,
    sequencesCount,
    activeCount,
    hasActive,
    fetchSequences,
    fetchSequence,
    refreshActive,
    clearCurrent,
    upsert,
    pause,
    resume,
    cancel,
    approve,
    reject,
    remove,
  }
})
