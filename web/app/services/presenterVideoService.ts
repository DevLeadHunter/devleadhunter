import { api } from '~/services/api'

const BASE_URL = '/api/v1/settings/presenter-video'

/** Presenter clip state returned by the API (no file content). */
export interface PresenterVideoInfo {
  has_video: boolean
  original_filename?: string | null
  duration_seconds?: number
  intro_seconds?: number
  outro_seconds?: number
  updated_at?: string | null
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
 * @returns The stored clip metadata (duration detected server-side).
 * @throws {Error} When the upload fails (message from the API when available).
 */
export async function uploadPresenterVideo(
  file: File,
  introSeconds: number,
  outroSeconds: number,
): Promise<PresenterVideoInfo> {
  const userStore = useUserStore()
  const config = useRuntimeConfig()
  const formData = new FormData()
  formData.append('file', file)
  formData.append('intro_seconds', String(introSeconds))
  formData.append('outro_seconds', String(outroSeconds))

  const response = await fetch(`${config.public.apiBase}${BASE_URL}`, {
    method: 'PUT',
    headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
    body: formData,
  })

  if (!response.ok) {
    const errorText = await response.text().catch(() => '')
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
 * Adjust the intro/outro full-screen segments of the existing clip.
 * @param introSeconds - Full-screen webcam seconds at the start.
 * @param outroSeconds - Full-screen webcam seconds at the end.
 */
export async function updatePresenterVideoTimings(
  introSeconds: number,
  outroSeconds: number,
): Promise<PresenterVideoInfo> {
  return api.patch<PresenterVideoInfo>(BASE_URL, {
    intro_seconds: introSeconds,
    outro_seconds: outroSeconds,
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
