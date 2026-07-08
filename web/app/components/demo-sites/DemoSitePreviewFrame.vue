<template>
  <div class="overflow-hidden rounded-xl border border-[#30363d] bg-[#0d1117] shadow-2xl">
    <div class="flex items-center gap-2 border-b border-[#30363d] bg-[#1a1a1a] px-4 py-2">
      <span class="h-3 w-3 rounded-full bg-[#DC4747]"></span>
      <span class="h-3 w-3 rounded-full bg-[#f59e0b]"></span>
      <span class="h-3 w-3 rounded-full bg-[#2BAD5F]"></span>
      <span class="ml-2 truncate text-xs text-[#8b949e]">{{ previewLabel }}</span>
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

/**
 * Frame previewing a demo site by iframing the demo-host renderer — the real published
 * site when a ``slug`` is given, otherwise a placeholder render of the chosen template.
 */
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

const config = useRuntimeConfig()

/**
 * Build the demo-host URL: the real published demo (by slug) or a placeholder template
 * preview (by template id, with the client's business name overlaid) before creation.
 */
const previewSrc: ComputedRef<string> = computed((): string => {
  const base: string = String(config.public.demoHostBase).replace(/\/$/, '')
  if (props.slug) {
    return `${base}/${props.slug}`
  }
  const params = new URLSearchParams({ t: props.templateId })
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
