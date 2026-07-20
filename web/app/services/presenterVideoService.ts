import { api } from '~/services/api'

const BASE_URL = '/api/v1/settings/presenter-video'

/** How the stored clip was produced. */
export type PresenterVideoSource = 'upload' | 'recorded'

/** Presenter clip state returned by the API (no file content). */
export interface PresenterVideoInfo {
  has_video: boolean
  original_filename?: string | null
  duration_seconds?: number
  intro_seconds?: number
  outro_seconds?: number
  auto_generate?: boolean
  /** ``recorded`` when filmed in-app: the segments are measured, not guessed. */
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
 * @throws {Error} With the API message when the request fails.
 */
async function putMultipart(path: string, formData: FormData): Promise<PresenterVideoInfo> {
  const userStore = useUserStore()
  const config = useRuntimeConfig()

  const response = await fetch(`${config.public.apiBase}${BASE_URL}${path}`, {
    method: 'PUT',
    headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
    body: formData,
  })

  if (!response.ok) {
    const errorText = await response.text().catch((): string => '')
    let errorMessage = `Upload échoué : ${response.statusText}`
    if (errorText) {
      try {
        errorMessage = (JSON.parse(errorText).detail as string) || errorMessage
      } catch {
        errorMessage = errorText
      }
    }
    throw new Error(errorMessage)
  }

  return (await response.json()) as PresenterVideoInfo
}

/**
 * Fetch the current user's presenter clip metadata.
 * @returns Clip state (``has_video: false`` when none was uploaded).
 */
export async function getPresenterVideo(): Promise<PresenterVideoInfo> {
  return api.get<PresenterVideoInfo>(BASE_URL)
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
 * @throws {Error} When the upload fails (message from the API when available).
 */
export async function uploadPresenterVideo(
  file: File,
  introSeconds: number,
  outroSeconds: number,
  autoGenerate: boolean,
): Promise<PresenterVideoInfo> {
  const formData = new FormData()
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
 * @throws {Error} When the assembly fails (message from the API when available).
 */
export async function uploadPresenterVideoSegments(
  intro: File,
  middle: File,
  outro: File,
  autoGenerate: boolean,
): Promise<PresenterVideoInfo> {
  const formData = new FormData()
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
export async function updatePresenterVideoSettings(
  introSeconds: number,
  outroSeconds: number,
  autoGenerate: boolean,
): Promise<PresenterVideoInfo> {
  return api.patch<PresenterVideoInfo>(BASE_URL, {
    intro_seconds: introSeconds,
    outro_seconds: outroSeconds,
    auto_generate: autoGenerate,
  })
}

/**
 * Delete the presenter clip (file + record).
 */
export async function deletePresenterVideo(): Promise<PresenterVideoInfo> {
  return api.delete<PresenterVideoInfo>(BASE_URL)
}

/**
 * Fetch the user's own clip as a blob URL for the in-app preview player.
 * @returns An object URL (caller must ``URL.revokeObjectURL`` it), or null.
 */
export async function getPresenterVideoObjectUrl(): Promise<string | null> {
  const userStore = useUserStore()
  const config = useRuntimeConfig()
  const response = await fetch(`${config.public.apiBase}${BASE_URL}/file`, {
    headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
  })
  if (!response.ok) return null
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}
