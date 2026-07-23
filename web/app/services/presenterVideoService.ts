import { ApiClient } from '~/services/api'

const BASE_URL: string = '/api/v1/settings/presenter-video'

/** How the stored clip was produced. */
export type PresenterVideoSource = 'upload' | 'recorded'

/** Presenter clip state returned by the API (no file content). */
export type PresenterVideo = {
  has_video: boolean
  original_filename?: string | null
  duration_seconds?: number
  intro_seconds?: number
  outro_seconds?: number
  auto_generate?: boolean
  source?: PresenterVideoSource
  updated_at?: string | null
}

/**
 * Post a multipart request to the presenter-video API and parse its answer.
 *
 * The shared ``api`` client only speaks JSON, so the multipart calls go
 * through ``fetch`` directly and share their error handling here.
 *
 * @param path - Path appended to the presenter-video base URL.
 * @param formData - The multipart body.
 * @returns The stored clip metadata.
 * @throws With the API message when the request fails.
 */
async function putMultipart(path: string, formData: FormData): Promise<PresenterVideo> {
  const userStore: ReturnType<typeof useUserStore> = useUserStore()
  const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

  const response: Response = await fetch(`${config.public.apiBase}${BASE_URL}${path}`, {
    method: 'PUT',
    headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
    body: formData,
  })

  if (!response.ok) {
    const errorText: string = await response.text().catch((): string => '')
    let errorMessage: string = `Upload échoué : ${response.statusText}`
    if (errorText) {
      try {
        errorMessage = (JSON.parse(errorText).detail as string) || errorMessage
      } catch {
        errorMessage = errorText
      }
    }
    throw new Error(errorMessage)
  }

  return (await response.json()) as PresenterVideo
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
    return putMultipart('', formData)
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
    return putMultipart('/segments', formData)
  }

  /**
   * Adjust the intro/outro segments + auto-generation toggle of the existing clip.
   * @param introSeconds - Full-screen webcam seconds at the start.
   * @param outroSeconds - Full-screen webcam seconds at the end.
   * @param autoGenerate - Auto-generate the video for every new demo site.
   */
  static async updatePresenterVideoSettings(
    introSeconds: number,
    outroSeconds: number,
    autoGenerate: boolean,
  ): Promise<PresenterVideo> {
    return ApiClient.patch<PresenterVideo>(BASE_URL, {
      intro_seconds: introSeconds,
      outro_seconds: outroSeconds,
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
}
