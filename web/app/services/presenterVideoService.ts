import { ApiClient } from '~/services/api'

const BASE_URL: string = '/api/v1/settings/presenter-video'
const PHOTO_BASE_URL: string = '/api/v1/settings/presenter-photo'

/**
 * Above this weight, a network-level failure is almost always the reverse proxy
 * rejecting the body rather than a genuine connectivity problem.
 */
const LIKELY_PROXY_LIMIT_BYTES: number = 50 * 1024 * 1024

/** How the stored clip was produced. */
export type PresenterVideoSource = 'upload' | 'recorded'

/** Presenter clip state returned by the API (no file content). */
export type PresenterVideo = {
  has_video: boolean
  original_filename?: string | null
  duration_seconds?: number
  intro_seconds?: number
  outro_seconds?: number
  /** User-chosen length of the site-scroll part; null = automatic split. */
  site_seconds?: number | null
  auto_generate?: boolean
  source?: PresenterVideoSource
  updated_at?: string | null
}

/** Presenter photo state returned by the API (bubble on video thumbnails). */
export type PresenterPhoto = {
  has_photo: boolean
}

/**
 * Post a multipart request to the presenter media API and parse its answer.
 *
 * The shared ``api`` client only speaks JSON, so the multipart calls go
 * through ``fetch`` directly and share their error handling here.
 *
 * @param path - Full API path (clip or photo endpoint).
 * @param formData - The multipart body.
 * @param payloadBytes - Weight being sent, quoted back when the upload is refused.
 * @returns The parsed API response.
 * @throws With the API message when the request fails.
 */
async function putMultipart<TResponse>(path: string, formData: FormData, payloadBytes: number): Promise<TResponse> {
  const userStore: ReturnType<typeof useUserStore> = useUserStore()
  const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

  let response: Response
  try {
    response = await fetch(`${config.public.apiBase}${path}`, {
      method: 'PUT',
      headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
      body: formData,
    })
  } catch (error: unknown) {
    // A proxy rejecting an oversized body answers 413 without CORS headers, which
    // `fetch` surfaces as the same bare « Failed to fetch » as a dead network.
    throw new Error(describeUnreachableUpload(payloadBytes, error))
  }

  if (!response.ok) {
    const errorText: string = await response.text().catch((): string => '')
    let errorMessage: string = `Upload échoué : ${response.statusText}`
    let hasApiDetail: boolean = false
    if (errorText) {
      try {
        const detail: string = JSON.parse(errorText).detail as string
        if (detail) {
          errorMessage = detail
          hasApiDetail = true
        }
      } catch {
        errorMessage = errorText
      }
    }
    // Un 413 sans détail vient du reverse proxy (l'API explique toujours les siens).
    if (response.status === 413 && !hasApiDetail) {
      errorMessage = `Fichier trop lourd pour le serveur (${formatMegabytes(payloadBytes)}). Allégez-le puis réessayez.`
    }
    throw new Error(errorMessage)
  }

  return (await response.json()) as TResponse
}

/**
 * Turn an unreachable upload into a sentence the user can act on.
 * @param payloadBytes - Weight that was being sent.
 * @param error - Whatever ``fetch`` rejected with.
 * @returns A French message naming the likely cause.
 */
function describeUnreachableUpload(payloadBytes: number, error: unknown): string {
  if (payloadBytes > LIKELY_PROXY_LIMIT_BYTES) {
    return (
      `L'envoi a été refusé avant d'atteindre le serveur — la vidéo est probablement trop lourde ` +
      `(${formatMegabytes(payloadBytes)}). Ré-exportez-la en 720p, ou raccourcissez-la.`
    )
  }
  return error instanceof Error && error.message
    ? `Connexion au serveur impossible (${error.message}). Vérifiez votre connexion puis réessayez.`
    : 'Connexion au serveur impossible. Vérifiez votre connexion puis réessayez.'
}

/**
 * Format a byte count as a rounded French megabyte label.
 * @param bytes - Raw size.
 * @returns A label such as « 262 Mo ».
 */
function formatMegabytes(bytes: number): string {
  return `${Math.round(bytes / (1024 * 1024))} Mo`
}

export class PresenterVideoService {
  /**
   * Fetch the current user's presenter clip metadata.
   * @returns Clip state (``has_video: false`` when none was uploaded).
   */
  static async getPresenterVideo(): Promise<PresenterVideo> {
    return ApiClient.get<PresenterVideo>(BASE_URL)
  }

  /**
   * Upload (or replace) the presenter clip used by prospection videos.
   *
   * Sends multipart form-data directly (the shared ``api`` client only handles
   * JSON bodies).
   * @param file - Webcam clip (MP4 / WebM / MOV / MKV, 12-90 s).
   * @param introSeconds - Full-screen webcam seconds at the start.
   * @param outroSeconds - Full-screen webcam seconds at the end.
   * @param autoGenerate - Auto-generate the video for every new demo site.
   * @returns The stored clip metadata (duration detected server-side).
   * @throws When the upload fails (message from the API when available).
   */
  static async uploadPresenterVideo(
    file: File,
    introSeconds: number,
    outroSeconds: number,
    autoGenerate: boolean,
  ): Promise<PresenterVideo> {
    const formData: FormData = new FormData()
    formData.append('file', file)
    formData.append('intro_seconds', String(introSeconds))
    formData.append('outro_seconds', String(outroSeconds))
    formData.append('auto_generate', String(autoGenerate))
    return putMultipart<PresenterVideo>(BASE_URL, formData, file.size)
  }

  /**
   * Send the three takes recorded in-app; the API concatenates them.
   *
   * Nothing is sent about where the cuts fall: each take *is* a segment, so the
   * API measures them and stores the exact intro/outro seconds.
   *
   * @param intro - Full-screen greeting take.
   * @param middle - Take played over the prospect's scrolling site.
   * @param outro - Full-screen call-to-action take.
   * @param autoGenerate - Auto-generate the video for every new demo site.
   * @returns The stored clip metadata.
   * @throws When the assembly fails (message from the API when available).
   */
  static async uploadPresenterVideoSegments(
    intro: File,
    middle: File,
    outro: File,
    autoGenerate: boolean,
  ): Promise<PresenterVideo> {
    const formData: FormData = new FormData()
    formData.append('intro', intro)
    formData.append('middle', middle)
    formData.append('outro', outro)
    formData.append('auto_generate', String(autoGenerate))
    return putMultipart<PresenterVideo>(`${BASE_URL}/segments`, formData, intro.size + middle.size + outro.size)
  }

  /**
   * Adjust the segment cuts + auto-generation toggle of the existing clip.
   * @param introSeconds - Full-screen webcam seconds at the start.
   * @param outroSeconds - Full-screen webcam seconds at the end.
   * @param autoGenerate - Auto-generate the video for every new demo site.
   * @param siteSeconds - Length of the site-scroll part (Storyblok gets the rest); null = automatic split.
   */
  static async updatePresenterVideoSettings(
    introSeconds: number,
    outroSeconds: number,
    autoGenerate: boolean,
    siteSeconds: number | null = null,
  ): Promise<PresenterVideo> {
    return ApiClient.patch<PresenterVideo>(BASE_URL, {
      intro_seconds: introSeconds,
      outro_seconds: outroSeconds,
      site_seconds: siteSeconds,
      auto_generate: autoGenerate,
    })
  }

  /**
   * Delete the presenter clip (file + record).
   */
  static async deletePresenterVideo(): Promise<PresenterVideo> {
    return ApiClient.delete<PresenterVideo>(BASE_URL)
  }

  /**
   * Fetch the user's own clip as a blob URL for the in-app preview player.
   * @returns An object URL (caller must ``URL.revokeObjectURL`` it), or null.
   */
  static async getPresenterVideoObjectUrl(): Promise<string | null> {
    const userStore: ReturnType<typeof useUserStore> = useUserStore()
    const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
    const response: Response = await fetch(`${config.public.apiBase}${BASE_URL}/file`, {
      headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
    })
    if (!response.ok) return null
    const blob: Blob = await response.blob()
    return URL.createObjectURL(blob)
  }

  /**
   * Fetch the presenter photo state (bubble on video thumbnails).
   * @returns Photo state (``has_photo: false`` when none was uploaded).
   */
  static async getPresenterPhoto(): Promise<PresenterPhoto> {
    return ApiClient.get<PresenterPhoto>(PHOTO_BASE_URL)
  }

  /**
   * Upload (or replace) the presenter photo drawn on video thumbnails.
   * @param file - Portrait image (JPEG / PNG / WebP).
   * @returns The stored photo state.
   * @throws When the upload fails (message from the API when available).
   */
  static async uploadPresenterPhoto(file: File): Promise<PresenterPhoto> {
    const formData: FormData = new FormData()
    formData.append('file', file)
    return putMultipart<PresenterPhoto>(PHOTO_BASE_URL, formData, file.size)
  }

  /**
   * Delete the presenter photo (file + record).
   * @returns The cleared photo state.
   */
  static async deletePresenterPhoto(): Promise<PresenterPhoto> {
    return ApiClient.delete<PresenterPhoto>(PHOTO_BASE_URL)
  }

  /**
   * Fetch the user's own presenter photo as a blob (sidecar build + preview).
   * @returns The image blob, or null when no photo is stored.
   */
  static async fetchPresenterPhotoBlob(): Promise<Blob | null> {
    const userStore: ReturnType<typeof useUserStore> = useUserStore()
    const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
    const response: Response = await fetch(`${config.public.apiBase}${PHOTO_BASE_URL}/file`, {
      headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
    })
    if (!response.ok) return null
    return response.blob()
  }

  /**
   * Fetch the presenter photo as a blob URL for the settings preview.
   * @returns An object URL (caller must ``URL.revokeObjectURL`` it), or null.
   */
  static async getPresenterPhotoObjectUrl(): Promise<string | null> {
    const blob: Blob | null = await PresenterVideoService.fetchPresenterPhotoBlob()
    return blob ? URL.createObjectURL(blob) : null
  }
}
