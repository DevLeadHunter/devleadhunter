import type { UseProfilePhotoReturn } from '~/types/Composables'
import type { Ref } from 'vue'
import { ref } from 'vue'
import { ProfilePhotoService } from '~/services/profilePhotoService'
import type { ProfilePhoto } from '~/services/profilePhotoService'

// État de module : la sidebar et le drawer profil partagent la même photo,
// un upload dans l'un met l'autre à jour sans recharger la page.
const hasProfilePhoto: Ref<boolean> = ref(false)
const profilePhotoObjectUrl: Ref<string | null> = ref(null)
let hasLoadedOnce: boolean = false

/**
 * Shared profile photo state (round avatar in the sidebar + profile drawer).
 * @returns The photo state, a lazy first load and an explicit refresh.
 */
export function useProfilePhoto(): UseProfilePhotoReturn {
  /**
   * Reload the photo state + its object URL from the API.
   * @returns A promise that resolves once the state is refreshed.
   */
  async function refreshProfilePhoto(): Promise<void> {
    hasLoadedOnce = true
    try {
      const photo: ProfilePhoto = await ProfilePhotoService.getProfilePhoto()
      hasProfilePhoto.value = photo.has_photo
      if (profilePhotoObjectUrl.value) URL.revokeObjectURL(profilePhotoObjectUrl.value)
      profilePhotoObjectUrl.value = photo.has_photo ? await ProfilePhotoService.getProfilePhotoObjectUrl() : null
    } catch {
      // La photo est un bonus : son échec de chargement n'affiche que l'avatar à initiales.
      hasProfilePhoto.value = false
    }
  }

  /**
   * Load the photo once per app session (later callers reuse the shared state).
   * @returns A promise that resolves once the first load is done.
   */
  async function ensureProfilePhotoLoaded(): Promise<void> {
    if (hasLoadedOnce) return
    await refreshProfilePhoto()
  }

  return { hasProfilePhoto, profilePhotoObjectUrl, ensureProfilePhotoLoaded, refreshProfilePhoto }
}
