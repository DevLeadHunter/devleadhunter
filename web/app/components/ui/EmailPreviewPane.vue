<template>
  <div class="min-w-0 rounded-lg border border-[var(--app-line)] bg-white p-6">
    <div class="mb-4 border-b border-neutral-200 pb-4">
      <p class="text-xs text-neutral-500">Sujet :</p>
      <p class="text-sm font-medium break-words text-neutral-900">{{ subject }}</p>
    </div>
    <iframe
      v-if="isWholeDocument"
      ref="frameRef"
      class="block min-h-48 w-full rounded-lg border-0"
      title="Aperçu de l'email"
      sandbox="allow-same-origin"
      :srcdoc="bodyHtml"
      @load="fitFrameToEmail"
    ></iframe>
    <!-- Without this scroll container, a fixed-width signature table widens the whole drawer. -->
    <div v-else class="email-preview-pane__body overflow-x-auto">
      <!-- eslint-disable-next-line vue/no-v-html -- Preview of the user's own email template HTML -->
      <div class="prose max-w-none text-sm text-neutral-900" v-html="bodyHtml"></div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { UiEmailPreviewPaneProps } from '~/types/UiEmailPreviewPane'
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'

/** Rendered email, on the white background a mail client would use. */
const props: UiEmailPreviewPaneProps = defineProps({
  subject: {
    type: String,
    default: '',
  },
  bodyHtml: {
    type: String,
    default: '',
  },
})

const frameRef: Ref<HTMLIFrameElement | null> = ref(null)

const isWholeDocument: ComputedRef<boolean> = computed((): boolean => /^\s*<!doctype/i.test(props.bodyHtml ?? ''))

/** Size the frame to the email it shows, again once each image has loaded. */
function fitFrameToEmail(): void {
  const frame: HTMLIFrameElement | null = frameRef.value
  const emailDocument: Document | null = frame?.contentDocument ?? null
  if (!frame || !emailDocument) return
  const fitToContentHeight: () => void = (): void => {
    frame.style.height = `${emailDocument.documentElement.scrollHeight}px`
  }
  fitToContentHeight()
  Array.from(emailDocument.images).forEach((image: HTMLImageElement): void => {
    if (!image.complete) image.addEventListener('load', fitToContentHeight, { once: true })
  })
}
</script>

<style scoped>
/* The body is arbitrary user HTML — reined in here rather than trusted. */
.email-preview-pane__body :deep(img) {
  max-width: 100%;
  height: auto;
}

.email-preview-pane__body :deep(table) {
  max-width: 100%;
}

.email-preview-pane__body :deep(a) {
  word-break: break-word;
}
</style>
