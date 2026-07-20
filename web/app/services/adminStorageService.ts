import { api } from './api'

/**
 * Admin storage service — inspects and manages the Cloudflare R2 bucket
 * (generated videos, email thumbnails, presenter clips, support attachments).
 * @module services/adminStorageService
 */

/** Category of a stored object, derived from its key prefix. */
export type StorageObjectKind = 'website_video' | 'website_thumbnail' | 'presenter' | 'support' | 'other'

/** One object of the bucket, enriched with business context. */
export interface StorageObject {
  key: string
  kind: StorageObjectKind
  size: number
  last_modified: string | null
  url: string
  slug: string | null
  prospect_name: string | null
  expires_in_days: number | null
  is_expired: boolean
}

/** Bucket listing + totals. */
export interface StorageListResponse {
  bucket: string
  public_base_url: string
  items: StorageObject[]
  total: number
  total_size: number
}

/** R2 ↔ database consistency report. */
export interface StorageHealthResponse {
  orphan_objects: string[]
  missing_objects: string[]
  expired_objects: string[]
}

/** Result of a mutating action (delete / purge / sync). */
export interface StorageActionResponse {
  deleted: number
  copied: number
  unchanged: number
  message: string
}

/**
 * List the bucket objects.
 * @param prefix - Optional key prefix filter (e.g. ``videos/websites/``).
 * @returns The bucket listing with totals.
 */
export async function getStorageObjects(prefix = ''): Promise<StorageListResponse> {
  return api.get<StorageListResponse>('/api/v1/admin/storage', { params: { prefix } })
}

/**
 * Read the R2 ↔ DB consistency report.
 * @returns Orphan, missing and expired objects.
 */
export async function getStorageHealth(): Promise<StorageHealthResponse> {
  return api.get<StorageHealthResponse>('/api/v1/admin/storage/health')
}

/**
 * Delete a single object from the bucket.
 * @param key - Full object key.
 * @returns The action result.
 */
export async function deleteStorageObject(key: string): Promise<StorageActionResponse> {
  return api.delete<StorageActionResponse>(`/api/v1/admin/storage/object?key=${encodeURIComponent(key)}`)
}

/**
 * Delete every demo deliverable past its 14-day TTL.
 * @returns The action result.
 */
export async function purgeExpiredStorage(): Promise<StorageActionResponse> {
  return api.post<StorageActionResponse>('/api/v1/admin/storage/purge-expired', {})
}

/**
 * Mirror the production bucket into the dev one (development only).
 * @returns Copied / deleted / unchanged counts.
 */
export async function syncStorageFromProd(): Promise<StorageActionResponse> {
  return api.post<StorageActionResponse>('/api/v1/admin/storage/sync-from-prod', {})
}
