<template>
  <div>
    <div v-if="props.pickedClipPreviewUrl" class="mb-3">
      <video
        :src="props.pickedClipPreviewUrl"
        controls
        playsinline
        preload="metadata"
        class="aspect-video w-full rounded-xl border border-[var(--app-line)] bg-black"
      />
    </div>

    <div
      :class="[
        'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed text-center transition-colors',
        props.compact || props.pickedClipPreviewUrl ? 'px-5 py-8' : 'px-6 py-14',
        props.isDragging
          ? 'border-[var(--app-ink)] bg-[var(--app-surface-2)]'
          : 'border-[var(--app-line)] hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)]',
      ]"
      role="button"
      tabindex="0"
      @click="emit('pick')"
      @keydown.enter.prevent="emit('pick')"
      @dragover.prevent="emit('dragging', true)"
      @dragleave.prevent="emit('dragging', false)"
      @drop.prevent="onDrop"
    >
      <span
        :class="[
          'flex items-center justify-center rounded-full bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]',
          props.compact || props.pickedClipPreviewUrl ? 'h-9 w-9' : 'h-12 w-12',
        ]"
      >
        <UIcon
          :name="props.selectedFile ? 'i-lucide-file-video' : 'i-lucide-upload'"
          :class="props.compact || props.pickedClipPreviewUrl ? 'h-4 w-4' : 'h-5 w-5'"
        />
      </span>

      <template v-if="props.selectedFile">
        <p class="text-sm font-medium text-[var(--app-ink)]">{{ props.selectedFile.name }}</p>
        <p class="text-muted text-xs">{{ selectedFileSizeLabel }} — cliquez pour changer de fichier</p>
      </template>
      <template v-else>
        <p class="text-sm font-medium text-[var(--app-ink)]">
          {{ compact ? 'Glissez un nouveau clip ici' : 'Glissez votre clip webcam ici' }}
        </p>
        <p class="text-muted text-xs">ou cliquez pour parcourir vos fichiers</p>
        <p class="text-muted mt-1 text-[11px]">MP4, WebM, MOV ou MKV — 12 à 90 s (cible : 30-45 s)</p>
      </template>
    </div>

    <div v-if="props.isCompressing" class="mt-3 space-y-2">
      <p class="text-muted flex items-center gap-2 text-xs">
        <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
        Optimisation de la vidéo — {{ compressionPercentLabel }}
      </p>
      <div class="h-1 w-full overflow-hidden rounded-full bg-[var(--app-surface-2)]">
        <div class="h-full bg-[var(--app-ink)] transition-[width]" :style="{ width: compressionPercentLabel }" />
      </div>
      <p class="text-muted text-[11px] leading-relaxed">
        L'optimisation se déroule en temps réel : comptez la durée du clip. Gardez la fenêtre ouverte.
      </p>
    </div>

    <p v-else-if="compressionGainLabel" class="text-muted mt-3 flex items-center gap-2 text-xs">
      <UIcon name="i-lucide-check" class="h-3.5 w-3.5 text-[var(--app-ink)]" />
      <UiArrowText :text="compressionGainLabel" />
    </p>

    <UiCallout v-if="props.sizeErrorMessage" variant="danger" class="mt-3">
      {{ props.sizeErrorMessage }}
    </UiCallout>

    <button
      v-if="selectedFile"
      type="button"
      class="btn-primary mt-4 disabled:cursor-not-allowed disabled:opacity-50"
      :disabled="isSendDisabled"
      @click="emit('upload')"
    >
      <UIcon
        v-if="isUploading || props.isCompressing"
        name="i-lucide-loader-circle"
        class="mr-1.5 h-4 w-4 animate-spin"
      />
      {{ sendButtonLabel }}
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { UiPresenterVideoDropzoneProps } from '~/types/UiPresenterVideoDropzone'
import { computed } from 'vue'

/** Drag-and-drop zone for presenter video upload. */
const props: UiPresenterVideoDropzoneProps = defineProps({
  selectedFile: {
    type: Object as PropType<File | null>,
    default: null,
  },
  isDragging: {
    type: Boolean,
    default: false,
  },
  isUploading: {
    type: Boolean,
    default: false,
  },
  compact: {
    type: Boolean,
    default: false,
  },
  pickedClipPreviewUrl: {
    type: String as PropType<string | null>,
    default: null,
  },
  isCompressing: {
    type: Boolean,
    default: false,
  },
  compressionProgress: {
    type: Number,
    default: 0,
  },
  bytesBeforeCompression: {
    type: Number as PropType<number | null>,
    default: null,
  },
  sizeErrorMessage: {
    type: String as PropType<string | null>,
    default: null,
  },
})

const emit: {
  (e: 'pick' | 'upload'): void
  (e: 'drop-file', file: File): void
  (e: 'dragging', value: boolean): void
} = defineEmits<{
  (e: 'pick' | 'upload'): void
  (e: 'drop-file', file: File): void
  (e: 'dragging', value: boolean): void
}>()

/** Weight of the file that will actually be sent. */
const selectedFileSizeLabel: ComputedRef<string> = computed((): string =>
  props.selectedFile ? formatFileSize(props.selectedFile.size) : '',
)

/** Re-encoding progress as a CSS-ready percentage (also drives the bar width). */
const compressionPercentLabel: ComputedRef<string> = computed(
  (): string => `${Math.round(Math.min(1, Math.max(0, props.compressionProgress ?? 0)) * 100)}%`,
)

/** « 262 Mo → 12 Mo » once the clip has been re-encoded, empty otherwise. */
const compressionGainLabel: ComputedRef<string> = computed((): string => {
  const before: number | null = props.bytesBeforeCompression ?? null
  if (before === null || !props.selectedFile || before <= props.selectedFile.size) return ''
  return `Vidéo optimisée : ${formatFileSize(before)} → ${formatFileSize(props.selectedFile.size)}, sans perte de qualité finale.`
})

/** Sending is blocked while busy, and whenever the clip is too heavy. */
const isSendDisabled: ComputedRef<boolean> = computed(
  (): boolean => Boolean(props.isUploading) || Boolean(props.isCompressing) || Boolean(props.sizeErrorMessage),
)

/** Button wording, which doubles as the progress indicator. */
const sendButtonLabel: ComputedRef<string> = computed((): string => {
  if (props.isCompressing) return 'Optimisation…'
  if (props.isUploading) return 'Envoi en cours…'
  return 'Envoyer le clip'
})

/**
 * Forward a dropped file to the parent, clearing the drag highlight first.
 * @param event - Native drop event from the dashed zone.
 */
function onDrop(event: DragEvent): void {
  emit('dragging', false)
  const file: File | undefined = event.dataTransfer?.files?.[0]
  if (file) emit('drop-file', file)
}

/**
 * Format a file size in a human-readable French label.
 * @param bytes - Raw size in bytes.
 * @returns Formatted label (e.g. « 245 Mo »).
 */
function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${Math.round(bytes / (1024 * 1024))} Mo`
  return `${Math.max(1, Math.round(bytes / 1024))} Ko`
}
</script>
