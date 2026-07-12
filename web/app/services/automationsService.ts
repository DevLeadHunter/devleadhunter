/**
 * Automatisations service — the auto-chaining tunnel.
 * @module services/automationsService
 */

import type {
  AutomationCreatePayload,
  AutomationDetail,
  AutomationListResponse,
  EmailPreview,
} from '~/types/Automation'
import { api } from './api'

const BASE_URL: string = '/api/v1/automations'

/**
 * List the current user's automatisations (newest first).
 * @returns The automatisations and their total count.
 */
export async function listAutomations(): Promise<AutomationListResponse> {
  return api.get<AutomationListResponse>(BASE_URL)
}

/**
 * Fetch one automatisation with its per-prospect pipeline.
 * @param id - Automatisation identifier.
 * @returns The full detail.
 */
export async function getAutomation(id: number): Promise<AutomationDetail> {
  return api.get<AutomationDetail>(`${BASE_URL}/${id}`)
}

/**
 * Create and start an automatisation.
 * @param payload - Automatisation configuration.
 * @returns The created detail.
 */
export async function createAutomation(payload: AutomationCreatePayload): Promise<AutomationDetail> {
  return api.post<AutomationDetail>(BASE_URL, payload)
}

/**
 * Prospect ids already claimed by an automatisation (for the picker).
 * @returns The claimed prospect ids.
 */
export async function getUsedProspectIds(): Promise<number[]> {
  const response = await api.get<{ prospect_ids: number[] }>(`${BASE_URL}/used-prospects`)
  return response.prospect_ids
}

/**
 * Pause a running automatisation.
 * @param id - Automatisation identifier.
 * @returns The updated detail.
 */
export async function pauseAutomation(id: number): Promise<AutomationDetail> {
  return api.post<AutomationDetail>(`${BASE_URL}/${id}/pause`, {})
}

/**
 * Resume a paused automatisation.
 * @param id - Automatisation identifier.
 * @returns The updated detail.
 */
export async function resumeAutomation(id: number): Promise<AutomationDetail> {
  return api.post<AutomationDetail>(`${BASE_URL}/${id}/resume`, {})
}

/**
 * Cancel an automatisation (non-destructive).
 * @param id - Automatisation identifier.
 * @returns The updated detail.
 */
export async function cancelAutomation(id: number): Promise<AutomationDetail> {
  return api.post<AutomationDetail>(`${BASE_URL}/${id}/cancel`, {})
}

/**
 * Approve the review gate — the machine may now campaign the generated sites.
 * @param id - Automatisation identifier.
 * @returns The updated detail.
 */
export async function approveAutomation(id: number): Promise<AutomationDetail> {
  return api.post<AutomationDetail>(`${BASE_URL}/${id}/approve`, {})
}

/**
 * Assign a demo template to some (or all pre-generation) items.
 * @param id - Automatisation identifier.
 * @param templateId - Template id (null clears).
 * @param itemIds - Items to target (undefined = all eligible).
 * @returns The updated detail.
 */
export async function assignTemplates(
  id: number,
  templateId: string | null,
  itemIds?: number[],
): Promise<AutomationDetail> {
  return api.post<AutomationDetail>(`${BASE_URL}/${id}/assign-templates`, {
    template_id: templateId,
    item_ids: itemIds ?? null,
  })
}

/**
 * Regenerate items, optionally with a new template.
 * @param id - Automatisation identifier.
 * @param itemIds - Items to regenerate.
 * @param templateId - Optional new template.
 * @returns The updated detail.
 */
export async function regenerateItems(
  id: number,
  itemIds: number[],
  templateId?: string | null,
): Promise<AutomationDetail> {
  return api.post<AutomationDetail>(`${BASE_URL}/${id}/regenerate`, {
    item_ids: itemIds,
    template_id: templateId ?? null,
  })
}

/**
 * Re-enrich then re-generate the given items.
 * @param id - Automatisation identifier.
 * @param itemIds - Items to re-enrich.
 * @returns The updated detail.
 */
export async function reenrichItems(id: number, itemIds: number[]): Promise<AutomationDetail> {
  return api.post<AutomationDetail>(`${BASE_URL}/${id}/reenrich`, { item_ids: itemIds })
}

/**
 * Exclude items from the automatisation (frees their prospects).
 * @param id - Automatisation identifier.
 * @param itemIds - Items to exclude.
 * @returns The updated detail.
 */
export async function excludeItems(id: number, itemIds: number[]): Promise<AutomationDetail> {
  return api.post<AutomationDetail>(`${BASE_URL}/${id}/exclude`, { item_ids: itemIds })
}

/**
 * Render the real email for one item with a given template.
 * @param id - Automatisation identifier.
 * @param itemId - The item (prospect).
 * @param templateId - Email template to render.
 * @returns The rendered subject + HTML.
 */
export async function previewItemEmail(id: number, itemId: number, templateId: number): Promise<EmailPreview> {
  return api.post<EmailPreview>(`${BASE_URL}/${id}/preview-email`, {
    item_id: itemId,
    template_id: templateId,
  })
}

/**
 * Delete an automatisation and its items (prospects/sites untouched).
 * @param id - Automatisation identifier.
 * @returns Nothing.
 */
export async function deleteAutomation(id: number): Promise<void> {
  await api.delete(`${BASE_URL}/${id}`)
}
