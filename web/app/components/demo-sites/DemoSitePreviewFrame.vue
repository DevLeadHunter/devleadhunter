<template>
  <div class="overflow-hidden rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] shadow-2xl">
    <div class="flex items-center gap-2 border-b border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-2">
      <span class="h-3 w-3 rounded-full bg-[var(--app-red)]"></span>
      <span class="h-3 w-3 rounded-full bg-[#f59e0b]"></span>
      <span class="h-3 w-3 rounded-full bg-[var(--app-green)]"></span>
      <span class="ml-2 truncate text-xs text-[var(--app-ink-soft)]">{{ previewLabel }}</span>
    </div>
    <iframe
      :src="previewSrc"
      :style="viewportStyle"
      class="w-full border-0 bg-white"
      title="Aperçu du site"
      loading="lazy"
    />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { DemoSitePreviewFrameProps } from '~/types/DemoSitePreviewFrame'

/** Iframe preview of a demo site or template placeholder. */
const props: DemoSitePreviewFrameProps = defineProps({
  templateId: {
    type: String,
    required: true,
  },
  businessName: {
    type: String,
    default: '',
  },
  content: {
    type: Object as PropType<Record<string, unknown>>,
    default: () => ({}),
  },
  slug: {
    type: String as PropType<string | null>,
    default: null,
  },
  height: {
    type: Number,
    default: 720,
  },
  previewLabel: {
    type: String,
    default: 'Aperçu du site',
  },
})

const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

/** Demo-host iframe URL (published slug or placeholder template preview). */
const previewSrc: ComputedRef<string> = computed((): string => {
  const base: string = String(config.public.demoHostBase).replace(/\/$/, '')
  if (props.slug) {
    return `${base}/${props.slug}`
  }
  const params: URLSearchParams = new URLSearchParams({ t: props.templateId })
  if (props.businessName) {
    params.set('business', props.businessName)
  }
  return `${base}/preview-layers?${params.toString()}`
})

/** Iframe viewport height (capped to the visible area). */
const viewportStyle: ComputedRef<Record<string, string>> = computed(
  (): Record<string, string> => ({
    height: `${props.height}px`,
    maxHeight: 'min(75vh, 800px)',
  }),
)
</script>
