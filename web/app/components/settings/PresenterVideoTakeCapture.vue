<template>
  <div class="space-y-5">
    <div class="space-y-3">
      <button
        v-if="props.canGoBackToTakes && captureMode === null"
        type="button"
        class="cursor-pointer text-xs font-medium text-[var(--app-ink-soft)] underline underline-offset-4 transition-colors hover:text-[var(--app-ink)]"
        @click="emit('back-to-takes')"
      >
        Revenir à vos prises
      </button>
      <div v-if="captureMode === null" class="grid gap-3 @2xl:grid-cols-2">
        <button
          v-for="option in CAPTURE_OPTIONS"
          :key="option.mode"
          type="button"
          class="flex cursor-pointer flex-col items-start gap-2 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-4 text-left transition-colors hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)]"
          @click="captureMode = option.mode"
        >
          <span
            class="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]"
          >
            <UIcon :name="option.icon" class="h-4 w-4 text-[var(--app-ink)]" />
          </span>
          <span class="text-sm font-semibold text-[var(--app-ink)]">{{ option.title }}</span>
          <span class="text-muted text-xs leading-relaxed">{{ option.detail }}</span>
          <span v-if="option.badge" class="app-badge app-badge--info mt-1 font-medium">{{ option.badge }}</span>
        </button>
      </div>
      <UiPresenterVideoRecorder
        v-else-if="captureMode === 'record'"
        :module="props.module"
        :auto-generate="props.autoGenerate"
        @saved="announceSavedTake"
        @cancel="captureMode = null"
      />
      <div v-else class="space-y-3">
        <UiPresenterVideoDropzone
          :selected-file="selectedFile"
          :is-dragging="isDragging"
          :is-uploading="isUploading"
          :picked-clip-preview-url="pickedClipPreviewUrl"
          :is-compressing="isCompressing"
          :compression-progress="compressionProgress"
          :bytes-before-compression="pickedClipOriginalBytes"
          :size-error-message="clipSizeErrorMessage"
          @pick="openFilePicker"
          @drop-file="adoptPickedClip"
          @dragging="isDragging = $event"
          @upload="handleUpload"
        />
        <button
          type="button"
          class="cursor-pointer text-xs font-medium text-[var(--app-ink-soft)] underline underline-offset-4 transition-colors hover:text-[var(--app-ink)]"
          @click="captureMode = null"
        >
          Revenir au choix
        </button>
      </div>
    </div>

    <PresenterVideoRecordingGuide
      v-if="captureMode !== 'record'"
      :module="props.module"
      :is-importing="captureMode === 'import'"
    />

    <input
      ref="fileInputRef"
      type="file"
      accept="video/mp4,video/webm,video/quicktime,video/x-matroska,.mp4,.webm,.mov,.mkv"
      class="hidden"
      @change="handleFileSelected"
    />
  </div>
</template>

<script lang="ts" setup>
import type { EmitFn, PropType, Ref } from 'vue'
import type { UseToastReturn } from '~/types/Composables'
import type { ProspectionScriptModule } from '~/composables/useProspectionScript'
import type { UseVideoCompressionReturn, VideoCompressionResult } from '~/composables/useVideoCompression'
import type { PresenterVideoTake } from '~/types/PresenterVideoTake'
import type {
  PresenterVideoCaptureMode,
  PresenterVideoCaptureOption,
  PresenterVideoTakeCaptureEmits,
  PresenterVideoTakeCaptureProps,
} from '~/types/PresenterVideoTakeCapture'
import { onBeforeUnmount, ref } from 'vue'
import { PresenterVideoService } from '~/services/presenterVideoService'
import { PRESENTER_VIDEO_WORDINGS } from '~/constants/presenterVideoWordings'
import { PRESENTER_VIDEO_MAX_BYTES, useVideoCompression } from '~/composables/useVideoCompression'
import { useToast } from '~/composables/useToast'

const props: PresenterVideoTakeCaptureProps = defineProps({
  module: {
    type: String as PropType<ProspectionScriptModule>,
    required: true,
  },
  autoGenerate: {
    type: Boolean,
    default: true,
  },
  canGoBackToTakes: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<PresenterVideoTakeCaptureEmits> = defineEmits<PresenterVideoTakeCaptureEmits>()

const toast: UseToastReturn = useToast()
const { isCompressing, compressionProgress, compressPresenterClip }: UseVideoCompressionReturn = useVideoCompression()

const CAPTURE_OPTIONS: PresenterVideoCaptureOption[] = [
  {
    mode: 'record',
    icon: 'i-lucide-video',
    title: 'Filmer ici, avec le texte à lire',
    detail:
      'Trois prises courtes — intro, milieu, fin — guidées par un prompteur. Chacune se refait toute seule si elle ne vous plaît pas.',
    badge: 'Le plus simple',
  },
  {
    mode: 'import',
    icon: 'i-lucide-upload',
    title: 'Importer un fichier',
    detail: 'Vous avez déjà filmé, au reflex, au téléphone ou avec un autre outil ? Déposez le fichier ici.',
    badge: '',
  },
]

const IMPORTED_INTRO_SECONDS: number = 4
const IMPORTED_OUTRO_SECONDS: number = 5

const captureMode: Ref<PresenterVideoCaptureMode | null> = ref(null)
const isUploading: Ref<boolean> = ref(false)
const isDragging: Ref<boolean> = ref(false)
const selectedFile: Ref<File | null> = ref(null)
const fileInputRef: Ref<HTMLInputElement | null> = ref(null)

/** Playable preview of the clip just picked, before it is sent. */
const pickedClipPreviewUrl: Ref<string | null> = ref(null)

/** Weight of the picked clip before compression, to show what was gained. */
const pickedClipOriginalBytes: Ref<number | null> = ref(null)

/** Blocking message when the picked clip is still too heavy to be sent. */
const clipSizeErrorMessage: Ref<string | null> = ref(null)

/**
 * Tell the user where the new take stands, then hand it to the takes list.
 * @param take - The take the API just stored.
 */
function announceSavedTake(take: PresenterVideoTake): void {
  if (take.is_active) {
    toast.success(PRESENTER_VIDEO_WORDINGS[props.module].uploadedToast)
  } else {
    toast.success(
      `Prise ${take.take_number} enregistrée. Elle ne sert pas encore : comparez-la aux autres, puis choisissez celle à utiliser.`,
    )
  }
  captureMode.value = null
  emit('saved', take)
}

/** Open the hidden file input from the drop zone. */
function openFilePicker(): void {
  fileInputRef.value?.click()
}

/**
 * Keep the file chosen in the file picker.
 * @param event - Native change event of the file input.
 */
async function handleFileSelected(event: Event): Promise<void> {
  const input: HTMLInputElement | null = event.target as HTMLInputElement | null
  const file: File | null = input?.files?.[0] ?? null
  if (file) await adoptPickedClip(file)
}

/** Drop the preview of the clip awaiting upload (avoids leaking blobs). */
function releasePickedClipPreview(): void {
  if (pickedClipPreviewUrl.value) {
    URL.revokeObjectURL(pickedClipPreviewUrl.value)
    pickedClipPreviewUrl.value = null
  }
}

/** Forget the clip awaiting upload, along with its preview and messages. */
function resetPickedClip(): void {
  releasePickedClipPreview()
  selectedFile.value = null
  pickedClipOriginalBytes.value = null
  clipSizeErrorMessage.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
}

/**
 * Show a picked clip right away, then shrink it to the montage canvas.
 *
 * Compression is transparent: the user drops a file and sees the preview, the
 * final weight, and — if the clip still cannot be sent — why.
 *
 * @param file - The clip dropped on the zone or chosen in the file picker.
 */
async function adoptPickedClip(file: File): Promise<void> {
  // Two concurrent re-encodings would race to overwrite `selectedFile`.
  if (isCompressing.value || isUploading.value) return

  releasePickedClipPreview()
  selectedFile.value = file
  pickedClipOriginalBytes.value = null
  clipSizeErrorMessage.value = null
  pickedClipPreviewUrl.value = URL.createObjectURL(file)

  const result: VideoCompressionResult = await compressPresenterClip(file)
  selectedFile.value = result.file
  pickedClipOriginalBytes.value = result.wasCompressed ? result.originalBytes : null
  clipSizeErrorMessage.value = describeOversizedClip(result)
}

/**
 * Explain, in the user's terms, why a clip cannot be sent as-is.
 *
 * Returning `null` means the clip is good to go.
 *
 * @param result - Outcome of the compression attempt.
 * @returns A sentence naming the fix, or `null` when the clip fits.
 */
function describeOversizedClip(result: VideoCompressionResult): string | null {
  if (result.file.size <= PRESENTER_VIDEO_MAX_BYTES) return null

  const currentMb: number = Math.round(result.file.size / (1024 * 1024))
  const maxMb: number = Math.round(PRESENTER_VIDEO_MAX_BYTES / (1024 * 1024))
  const limits: string = `Cette vidéo pèse ${currentMb} Mo, au-delà de la limite d'envoi de ${maxMb} Mo.`

  if (result.skipReason === 'undecodable') {
    return `${limits} Son format n'a pas pu être lu ici pour l'alléger automatiquement — ré-exportez-la en MP4 (H.264), 720p suffit.`
  }
  return `${limits} Ré-exportez-la en 720p ou raccourcissez-la (30 à 45 s suffisent).`
}

/** Send the picked clip; the API keeps it as a new take next to the older ones. */
async function handleUpload(): Promise<void> {
  if (!selectedFile.value || isCompressing.value) return

  // Without this guard the request dies in nginx, surfacing as « Failed to fetch ».
  if (selectedFile.value.size > PRESENTER_VIDEO_MAX_BYTES) {
    toast.error(clipSizeErrorMessage.value ?? 'Cette vidéo est trop lourde pour être envoyée.')
    return
  }

  isUploading.value = true
  try {
    const take: PresenterVideoTake = await PresenterVideoService.uploadPresenterVideo(
      selectedFile.value,
      IMPORTED_INTRO_SECONDS,
      IMPORTED_OUTRO_SECONDS,
      props.autoGenerate,
      props.module,
    )
    resetPickedClip()
    announceSavedTake(take)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'envoi du clip")
  } finally {
    isUploading.value = false
  }
}

onBeforeUnmount((): void => {
  releasePickedClipPreview()
})
</script>
