/**
 * Acquisition sequences service — the auto-chaining tunnel.
 * @module services/acquisitionSequencesService
 */

import type { Sequence, SequenceCreatePayload, SequenceDetail, SequenceListResponse } from '~/types/AcquisitionSequence'
import { api } from './api'

const BASE_URL: string = '/api/v1/acquisition-sequences'

/**
 * List the current user's sequences (newest first).
 * @returns The sequences and their total count.
 */
export async function listSequences(): Promise<SequenceListResponse> {
  return api.get<SequenceListResponse>(BASE_URL)
}

/**
 * Fetch one sequence with its per-prospect pipeline.
 * @param id - Sequence identifier.
 * @returns The full sequence detail.
 */
export async function getSequence(id: number): Promise<SequenceDetail> {
  return api.get<SequenceDetail>(`${BASE_URL}/${id}`)
}

/**
 * Create and start a sequence over the selected prospects.
 * @param payload - Sequence configuration.
 * @returns The created sequence detail.
 */
export async function createSequence(payload: SequenceCreatePayload): Promise<SequenceDetail> {
  return api.post<SequenceDetail>(BASE_URL, payload)
}

/**
 * Pause a running sequence.
 * @param id - Sequence identifier.
 * @returns The updated sequence detail.
 */
export async function pauseSequence(id: number): Promise<SequenceDetail> {
  return api.post<SequenceDetail>(`${BASE_URL}/${id}/pause`, {})
}

/**
 * Resume a paused sequence.
 * @param id - Sequence identifier.
 * @returns The updated sequence detail.
 */
export async function resumeSequence(id: number): Promise<SequenceDetail> {
  return api.post<SequenceDetail>(`${BASE_URL}/${id}/resume`, {})
}

/**
 * Cancel a sequence (non-destructive — stops the automation only).
 * @param id - Sequence identifier.
 * @returns The updated sequence detail.
 */
export async function cancelSequence(id: number): Promise<SequenceDetail> {
  return api.post<SequenceDetail>(`${BASE_URL}/${id}/cancel`, {})
}

/**
 * Approve the review gate — the machine may now campaign the generated sites.
 * @param id - Sequence identifier.
 * @returns The updated sequence detail.
 */
export async function approveSequence(id: number): Promise<SequenceDetail> {
  return api.post<SequenceDetail>(`${BASE_URL}/${id}/approve`, {})
}

/**
 * Reject a single generated site during review (it won't be campaigned).
 * @param id - Sequence identifier.
 * @param itemId - The item (prospect) to reject.
 * @returns The updated sequence detail.
 */
export async function rejectSequenceItem(id: number, itemId: number): Promise<SequenceDetail> {
  return api.post<SequenceDetail>(`${BASE_URL}/${id}/items/${itemId}/reject`, {})
}

/**
 * Delete a sequence and its items (prospects/sites are untouched).
 * @param id - Sequence identifier.
 * @returns Nothing.
 */
export async function deleteSequence(id: number): Promise<void> {
  await api.delete(`${BASE_URL}/${id}`)
}
