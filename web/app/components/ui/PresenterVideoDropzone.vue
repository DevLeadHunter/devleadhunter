<template>
  <div>
    <div
      :class="[
        'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed text-center transition-colors',
        props.compact ? 'px-5 py-8' : 'px-6 py-14',
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
          props.compact ? 'h-9 w-9' : 'h-12 w-12',
        ]"
      >
        <UIcon
          :name="props.selectedFile ? 'i-lucide-file-video' : 'i-lucide-upload'"
          :class="props.compact ? 'h-4 w-4' : 'h-5 w-5'"
        />
      </span>

      <template v-if="props.selectedFile">
        <p class="text-sm font-medium text-[var(--app-ink)]">{{ props.selectedFile.name }}</p>
        <p class="text-muted text-xs">
          {{ formatFileSize(props.selectedFile.size) }} — cliquez pour changer de fichier
        </p>
      </template>
      <template v-else>
        <p class="text-sm font-medium text-[var(--app-ink)]">
          {{ compact ? 'Glissez un nouveau clip ici' : 'Glissez votre clip webcam ici' }}
        </p>
        <p class="text-muted text-xs">ou cliquez pour parcourir vos fichiers</p>
        <p class="text-muted mt-1 text-[11px]">MP4, WebM, MOV ou MKV — 12 à 90 s (cible : 30-45 s)</p>
      </template>
    </div>

    <button
      v-if="selectedFile"
      type="button"
      class="btn-primary mt-4 disabled:cursor-not-allowed disabled:opacity-50"
      :disabled="isUploading"
      @click="emit('upload')"
    >
      <UIcon v-if="isUploading" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
      {{ isUploading ? 'Envoi en cours…' : 'Envoyer le clip' }}
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { UiPresenterVideoDropzoneProps } from '~/types/UiPresenterVideoDropzone'

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
