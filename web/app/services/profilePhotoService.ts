import { ApiClient } from '~/services/api'

const BASE_URL: string = '/api/v1/auth/me/photo'

/** Profile photo state returned by the API (today: the video-thumbnail bubble). */
export type ProfilePhoto = {
  has_photo: boolean
}

export class ProfilePhotoService {
  /**
   * Fetch the profile photo state.
   * @returns Photo state (``has_photo: false`` when none was uploaded).
   */
  static async getProfilePhoto(): Promise<ProfilePhoto> {
    return ApiClient.get<ProfilePhoto>(BASE_URL)
  }

  /**
   * Upload (or replace) the profile photo.
   *
   * Sends multipart form-data directly (the shared ``api`` client only handles
   * JSON bodies).
   * @param file - Portrait image (JPEG / PNG / WebP).
   * @returns The stored photo state.
   * @throws When the upload fails (message from the API when available).
   */
  static async uploadProfilePhoto(file: File): Promise<ProfilePhoto> {
    const userStore: ReturnType<typeof useUserStore> = useUserStore()
    const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
    const formData: FormData = new FormData()
    formData.append('file', file)

    const response: Response = await fetch(`${config.public.apiBase}${BASE_URL}`, {
      method: 'PUT',
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
    return (await response.json()) as ProfilePhoto
  }

  /**
   * Delete the profile photo (file + record).
   * @returns The cleared photo state.
   */
  static async deleteProfilePhoto(): Promise<ProfilePhoto> {
    return ApiClient.delete<ProfilePhoto>(BASE_URL)
  }

  /**
   * Fetch the user's own photo as a blob (thumbnail montage + previews).
   * @returns The image blob, or null when no photo is stored.
   */
  static async fetchProfilePhotoBlob(): Promise<Blob | null> {
    const userStore: ReturnType<typeof useUserStore> = useUserStore()
    const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
    const response: Response = await fetch(`${config.public.apiBase}${BASE_URL}/file`, {
      headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
    })
    if (!response.ok) return null
    return response.blob()
  }

  /**
   * Fetch the profile photo as a blob URL for round previews.
   * @returns An object URL (caller must ``URL.revokeObjectURL`` it), or null.
   */
  static async getProfilePhotoObjectUrl(): Promise<string | null> {
    const blob: Blob | null = await ProfilePhotoService.fetchProfilePhotoBlob()
    return blob ? URL.createObjectURL(blob) : null
  }
}
