import { ApiClient } from './api'

/**
 * Admin storage service — inspects and manages the Cloudflare R2 bucket
 * (generated videos, email thumbnails, presenter clips, support attachments).
 * @module services/adminStorageService
 */

/** Category of a stored object, derived from its key prefix. */
export type StorageObjectKind =
  | 'website_video'
  | 'website_thumbnail'
  | 'website_background'
  | 'presenter'
  | 'support'
  | 'prospect_photo'
  | 'manual'
  | 'other'

/** One object of the bucket, enriched with business context. */
export type StorageObject = {
  key: string
  kind: StorageObjectKind
  size: number
  last_modified: string | null
  url: string
  slug: string | null
  prospect_name: string | null
  expires_in_days: number | null
  is_expired: boolean
  ttl_pending: boolean
}

/** Bucket listing + totals. */
export type StorageListResponse = {
  bucket: string
  public_base_url: string
  items: StorageObject[]
  total: number
  total_size: number
  ttl_days: number
}

/** Result of a manual upload / URL import — the caller pastes ``url`` where it is needed. */
export type StorageUploadResponse = {
  key: string
  url: string
  kind: StorageObjectKind
  size: number
  message: string
}

/** R2 ↔ database consistency report. */
export type StorageHealthResponse = {
  orphan_objects: string[]
  missing_objects: string[]
  expired_objects: string[]
}

/** Result of a mutating action (delete / purge / sync). */
export type StorageActionResponse = {
  deleted: number
  copied: number
  unchanged: number
  message: string
}

export class AdminStorageService {
  /**
   * List the bucket objects.
   * @param prefix - Optional key prefix filter (e.g. ``videos/websites/``).
   * @returns The bucket listing with totals.
   */
  static async getStorageObjects(prefix: string = ''): Promise<StorageListResponse> {
    return ApiClient.get<StorageListResponse>('/api/v1/admin/storage', { params: { prefix } })
  }

  /**
   * Read the R2 ↔ DB consistency report.
   * @returns Orphan, missing and expired objects.
   */
  static async getStorageHealth(): Promise<StorageHealthResponse> {
    return ApiClient.get<StorageHealthResponse>('/api/v1/admin/storage/health')
  }

  /**
   * Delete a single object from the bucket.
   * @param key - Full object key.
   * @returns The action result.
   */
  static async deleteStorageObject(key: string): Promise<StorageActionResponse> {
    return ApiClient.delete<StorageActionResponse>(`/api/v1/admin/storage/object?key=${encodeURIComponent(key)}`)
  }

  /**
   * Delete several objects at once (multi-selection on the storage page).
   * @param keys - Full object keys to remove.
   * @returns The action result.
   */
  static async deleteStorageObjects(keys: string[]): Promise<StorageActionResponse> {
    return ApiClient.post<StorageActionResponse>('/api/v1/admin/storage/delete-objects', { keys })
  }

  /**
   * Delete every demo deliverable whose demo has expired or vanished.
   * @returns The action result.
   */
  static async purgeExpiredStorage(): Promise<StorageActionResponse> {
    return ApiClient.post<StorageActionResponse>('/api/v1/admin/storage/purge-expired', {})
  }

  /**
   * Import a remote file (e.g. an expiring Facebook ``fbcdn`` image) onto R2.
   * @param url - Source URL to download and rehost.
   * @returns The stored object, whose ``url`` is the permanent R2 link.
   */
  static async importFromUrl(url: string): Promise<StorageUploadResponse> {
    return ApiClient.post<StorageUploadResponse>('/api/v1/admin/storage/import-url', { url })
  }

  /**
   * Upload a hand-picked file to R2.
   *
   * Sends multipart form-data directly (the shared ``api`` client only handles JSON bodies).
   * @param file - Image or PDF to store.
   * @returns The stored object, whose ``url`` is the permanent R2 link.
   * @throws When the upload fails (message from the API when available).
   */
  static async uploadFile(file: File): Promise<StorageUploadResponse> {
    const userStore: ReturnType<typeof useUserStore> = useUserStore()
    const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
    const formData: FormData = new FormData()
    formData.append('file', file)

    const response: Response = await fetch(`${config.public.apiBase}/api/v1/admin/storage/upload`, {
      method: 'POST',
      headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
      body: formData,
    })
    if (!response.ok) {
      const errorText: string = await response.text().catch((): string => '')
      let errorMessage: string = `Upload échoué : ${response.statusText}`
      try {
        errorMessage = (JSON.parse(errorText).detail as string) || errorMessage
      } catch {
        if (errorText) errorMessage = errorText
      }
      throw new Error(errorMessage)
    }
    return (await response.json()) as StorageUploadResponse
  }

  /**
   * Delete rehosted prospect photos no enrichment references any more.
   * @returns The action result.
   */
  static async purgeOrphanProspectPhotos(): Promise<StorageActionResponse> {
    return ApiClient.post<StorageActionResponse>('/api/v1/admin/storage/purge-orphan-prospect-photos', {})
  }

  /**
   * Mirror the production bucket into the dev one (development only).
   * @returns Copied / deleted / unchanged counts.
   */
  static async syncStorageFromProd(): Promise<StorageActionResponse> {
    return ApiClient.post<StorageActionResponse>('/api/v1/admin/storage/sync-from-prod', {})
  }
}
