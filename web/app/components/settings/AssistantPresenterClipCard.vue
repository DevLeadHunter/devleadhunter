<template>
  <section class="app-card space-y-4 p-5">
    <div>
      <h2 class="text-sm font-semibold text-[var(--app-ink)]">Clip webcam — Réceptionniste IA</h2>
      <p class="text-muted mt-1 text-sm leading-relaxed">
        Un discours webcam <strong>différent</strong> de celui des sites : ici vous présentez l'assistant. Enregistré
        une fois, il sert d'intro et d'outro à toutes les vidéos d'assistant (la démo du widget passe au milieu).
      </p>
    </div>

    <div v-if="isLoading" class="flex h-16 items-center justify-center">
      <UIcon name="i-lucide-loader-circle" class="h-5 w-5 animate-spin text-[var(--app-ink-soft)]" />
    </div>

    <template v-else>
      <div
        v-if="clip.has_video"
        class="flex items-center justify-between gap-3 rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5"
      >
        <div class="min-w-0">
          <p class="truncate text-sm font-medium text-[var(--app-ink)]">
            {{ clip.original_filename || 'Clip enregistré' }}
          </p>
          <p class="text-muted text-xs">
            {{ clip.duration_seconds ? `${Math.round(clip.duration_seconds)} s` : 'durée inconnue' }} · intro
            {{ introSeconds }} s · outro {{ outroSeconds }} s
          </p>
        </div>
        <button
          type="button"
          class="text-muted flex h-8 shrink-0 cursor-pointer items-center gap-1 rounded-lg px-2 text-xs transition-colors hover:text-[var(--app-red)]"
          :disabled="isSaving"
          @click="removeClip"
        >
          <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
          Supprimer
        </button>
      </div>
      <p v-else class="text-muted text-sm">Aucun clip assistant pour le moment.</p>

      <div class="grid grid-cols-2 gap-3">
        <label class="flex flex-col gap-1">
          <span class="app-label !text-[0.6rem]">Intro (s)</span>
          <input v-model.number="introSeconds" type="number" min="0" max="30" step="0.5" class="app-input" />
        </label>
        <label class="flex flex-col gap-1">
          <span class="app-label !text-[0.6rem]">Outro (s)</span>
          <input v-model.number="outroSeconds" type="number" min="0" max="30" step="0.5" class="app-input" />
        </label>
      </div>

      <div
        v-if="clip.has_video"
        class="flex items-center justify-between gap-3 rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5"
      >
        <div class="min-w-0">
          <p class="text-sm font-medium text-[var(--app-ink)]">Génération automatique</p>
          <p class="text-muted text-xs">Chaque nouvel assistant génère sa vidéo tout seul.</p>
        </div>
        <UiSwitch
          id="assistant-video-auto-generate"
          :model-value="autoGenerate"
          :disabled="isSaving"
          @update:model-value="onToggleAutoGenerate"
        />
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <input
          ref="fileInput"
          type="file"
          accept="video/mp4,video/webm,video/quicktime,video/x-matroska"
          class="hidden"
          @change="onFilePicked"
        />
        <button type="button" class="btn-secondary h-9 text-xs" :disabled="isSaving" @click="fileInput?.click()">
          <UIcon name="i-lucide-upload" class="mr-1.5 h-4 w-4" />
          {{ selectedFile ? selectedFile.name : clip.has_video ? 'Remplacer le clip' : 'Choisir un clip' }}
        </button>
        <button
          v-if="selectedFile"
          type="button"
          class="btn-primary h-9 text-xs"
          :disabled="isSaving"
          @click="uploadClip"
        >
          <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
          Enregistrer
        </button>
      </div>
    </template>
  </section>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import { onMounted, ref } from 'vue'
import type { PresenterVideo } from '~/services/presenterVideoService'
import { PresenterVideoService } from '~/services/presenterVideoService'
import type { UseToastReturn } from '~/types/Composables'
import { useToast } from '~/composables/useToast'

/** The sellable module this clip belongs to — its speech presents the AI assistant, not a site. */
const CLIP_MODULE: string = 'ai-assistant'

const toast: UseToastReturn = useToast()

const clip: Ref<PresenterVideo> = ref({ has_video: false })
const isLoading: Ref<boolean> = ref(true)
const isSaving: Ref<boolean> = ref(false)
const introSeconds: Ref<number> = ref(4)
const outroSeconds: Ref<number> = ref(5)
const autoGenerate: Ref<boolean> = ref(false)
const selectedFile: Ref<File | null> = ref(null)
const fileInput: Ref<HTMLInputElement | null> = ref(null)

/**
 * Apply loaded clip metadata to the local state.
 * @param loaded - The clip metadata from the API.
 */
function applyClip(loaded: PresenterVideo): void {
  clip.value = loaded
  if (typeof loaded.intro_seconds === 'number') introSeconds.value = loaded.intro_seconds
  if (typeof loaded.outro_seconds === 'number') outroSeconds.value = loaded.outro_seconds
  if (typeof loaded.auto_generate === 'boolean') autoGenerate.value = loaded.auto_generate
}

/**
 * Persist the auto-generation toggle for the existing clip.
 * @param value - Whether every new assistant should generate its video automatically.
 * @returns A promise resolved once the setting is saved.
 */
async function onToggleAutoGenerate(value: boolean): Promise<void> {
  autoGenerate.value = value
  if (isSaving.value) return
  isSaving.value = true
  try {
    applyClip(
      await PresenterVideoService.updatePresenterVideoSettings(
        introSeconds.value,
        outroSeconds.value,
        value,
        null,
        CLIP_MODULE,
      ),
    )
  } catch {
    autoGenerate.value = !value
    toast.error('Réglage impossible pour le moment.')
  } finally {
    isSaving.value = false
  }
}

/**
 * Keep a picked file for upload.
 * @param event - The file input change event.
 */
function onFilePicked(event: Event): void {
  const target: HTMLInputElement = event.target as HTMLInputElement
  selectedFile.value = target.files?.[0] ?? null
}

/**
 * Upload the picked assistant clip.
 * @returns A promise resolved once the upload is attempted.
 */
async function uploadClip(): Promise<void> {
  const file: File | null = selectedFile.value
  if (!file || isSaving.value) return
  isSaving.value = true
  try {
    applyClip(
      await PresenterVideoService.uploadPresenterVideo(
        file,
        introSeconds.value,
        outroSeconds.value,
        autoGenerate.value,
        CLIP_MODULE,
      ),
    )
    selectedFile.value = null
    toast.success('Clip assistant enregistré.')
  } catch {
    toast.error('Enregistrement impossible (format ou durée du clip ?).')
  } finally {
    isSaving.value = false
  }
}

/**
 * Delete the assistant clip.
 * @returns A promise resolved once removed.
 */
async function removeClip(): Promise<void> {
  if (isSaving.value) return
  isSaving.value = true
  try {
    applyClip(await PresenterVideoService.deletePresenterVideo(CLIP_MODULE))
    toast.success('Clip assistant supprimé.')
  } catch {
    toast.error('Suppression impossible pour le moment.')
  } finally {
    isSaving.value = false
  }
}

onMounted(async (): Promise<void> => {
  try {
    applyClip(await PresenterVideoService.getPresenterVideo(CLIP_MODULE))
  } catch {
    toast.error('Chargement du clip assistant impossible.')
  } finally {
    isLoading.value = false
  }
})
</script>
