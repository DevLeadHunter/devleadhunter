import type { PresenterVideoTake, PresenterVideoTakeList } from '~/types/PresenterVideoTake'
import { ApiClient } from '~/services/api'

const BASE_URL: string = '/api/v1/settings/presenter-video'

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
  static async getPresenterVideo(module: string = 'websites'): Promise<PresenterVideo> {
    return ApiClient.get<PresenterVideo>(`${BASE_URL}?module=${module}`)
  }

  /**
   * Keep an imported clip as a new take of the module, next to the older ones.
   *
   * Sends multipart form-data directly (the shared ``api`` client only handles
   * JSON bodies).
   * @param file - Webcam clip (MP4 / WebM / MOV / MKV, 12-90 s).
   * @param introSeconds - Full-screen webcam seconds at the start.
   * @param outroSeconds - Full-screen webcam seconds at the end.
   * @param autoGenerate - Auto-generate the video for every new demo site, kept only for the module's first take.
   * @param module - The sellable module the take belongs to.
   * @returns The stored clip metadata (duration detected server-side).
   * @throws When the upload fails (message from the API when available).
   */
  static async uploadPresenterVideo(
    file: File,
    introSeconds: number,
    outroSeconds: number,
    autoGenerate: boolean,
    module: string = 'websites',
  ): Promise<PresenterVideoTake> {
    const formData: FormData = new FormData()
    formData.append('file', file)
    formData.append('intro_seconds', String(introSeconds))
    formData.append('outro_seconds', String(outroSeconds))
    formData.append('auto_generate', String(autoGenerate))
    return putMultipart<PresenterVideoTake>(`${BASE_URL}?module=${module}`, formData, file.size)
  }

  /**
   * Send the three parts filmed in-app; the API concatenates them into a new take.
   *
   * Nothing is sent about where the cuts fall: each part *is* a segment, so the
   * API measures them and stores the exact intro/outro seconds.
   *
   * @param intro - Full-screen greeting part.
   * @param middle - Part played over the prospect's scrolling site.
   * @param outro - Full-screen call-to-action part.
   * @param autoGenerate - Auto-generate the video for every new demo site, kept only for the module's first take.
   * @param module - The sellable module the take belongs to.
   * @returns The stored clip metadata.
   * @throws When the assembly fails (message from the API when available).
   */
  static async uploadPresenterVideoSegments(
    intro: File,
    middle: File,
    outro: File,
    autoGenerate: boolean,
    module: string = 'websites',
  ): Promise<PresenterVideoTake> {
    const formData: FormData = new FormData()
    formData.append('intro', intro)
    formData.append('middle', middle)
    formData.append('outro', outro)
    formData.append('auto_generate', String(autoGenerate))
    return putMultipart<PresenterVideoTake>(
      `${BASE_URL}/segments?module=${module}`,
      formData,
      intro.size + middle.size + outro.size,
    )
  }

  /**
   * List the module's takes, the oldest first, with the module's auto-generation setting.
   * @param module - The sellable module.
   * @returns The takes.
   */
  static async listTakes(module: string = 'websites'): Promise<PresenterVideoTakeList> {
    return ApiClient.get<PresenterVideoTakeList>(`${BASE_URL}/takes?module=${module}`)
  }

  /**
   * Turn on or off the video every new demo of the module gets on its own.
   * @param autoGenerate - Whether the videos are generated on their own.
   * @param module - The sellable module.
   * @returns The module's takes, up to date.
   */
  static async setAutoGenerate(autoGenerate: boolean, module: string = 'websites'): Promise<PresenterVideoTakeList> {
    return ApiClient.patch<PresenterVideoTakeList>(`${BASE_URL}/auto-generate?module=${module}`, {
      auto_generate: autoGenerate,
    })
  }

  /**
   * Make a take the one the module's next prospection videos are built with.
   * @param takeId - The take to use.
   * @returns The take, now in use.
   */
  static async activateTake(takeId: number): Promise<PresenterVideoTake> {
    return ApiClient.post<PresenterVideoTake>(`${BASE_URL}/takes/${takeId}/activate`, {})
  }

  /**
   * Adjust a take's cut points; the API drops its example video when they move.
   * @param takeId - The take to adjust.
   * @param introSeconds - Full-screen webcam seconds at the start.
   * @param outroSeconds - Full-screen webcam seconds at the end.
   * @param siteSeconds - Length of the site-scroll part (Storyblok gets the rest); null = automatic split.
   * @returns The take, up to date.
   */
  static async updateTakeTimings(
    takeId: number,
    introSeconds: number,
    outroSeconds: number,
    siteSeconds: number | null,
  ): Promise<PresenterVideoTake> {
    return ApiClient.patch<PresenterVideoTake>(`${BASE_URL}/takes/${takeId}`, {
      intro_seconds: introSeconds,
      outro_seconds: outroSeconds,
      site_seconds: siteSeconds,
    })
  }

  /**
   * Delete a take with its clip and example video; the take in use goes only once it is the last one.
   * @param takeId - The take to delete.
   * @throws With the API message when the take is still in use.
   */
  static async deleteTake(takeId: number): Promise<void> {
    await ApiClient.delete(`${BASE_URL}/takes/${takeId}`)
  }

  /**
   * Fetch a take's clip, for the desktop app to build its example video.
   * @param takeId - The take.
   * @returns The clip as an mp4 blob.
   * @throws When the clip cannot be fetched.
   */
  static async fetchTakeFile(takeId: number): Promise<Blob> {
    const userStore: ReturnType<typeof useUserStore> = useUserStore()
    const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
    const response: Response = await fetch(`${config.public.apiBase}${BASE_URL}/takes/${takeId}/file`, {
      headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
    })
    if (!response.ok) throw new Error('Le fichier de cette prise est introuvable.')
    return response.blob()
  }

  /**
   * Keep the example video the desktop app built with a take on one of the user's demos.
   * @param takeId - The take the example was built with.
   * @param video - The finished mp4.
   * @param demoId - The demo site or receptionist filmed.
   * @param demoName - Its business name, shown under the example.
   * @returns The take with its new example.
   * @throws When the upload fails (message from the API when available).
   */
  static async uploadTakeExample(
    takeId: number,
    video: Blob,
    demoId: number,
    demoName: string,
  ): Promise<PresenterVideoTake> {
    const formData: FormData = new FormData()
    formData.append('file', video, 'example.mp4')
    formData.append('subject_id', String(demoId))
    formData.append('subject_name', demoName)
    return putMultipart<PresenterVideoTake>(`${BASE_URL}/takes/${takeId}/example`, formData, video.size)
  }
}
