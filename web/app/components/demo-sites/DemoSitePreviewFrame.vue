<template>
  <div class="overflow-hidden rounded-xl border border-[#30363d] bg-[#0d1117] shadow-2xl">
    <div class="flex items-center gap-2 border-b border-[#30363d] bg-[#1a1a1a] px-4 py-2">
      <span class="h-3 w-3 rounded-full bg-[#DC4747]"></span>
      <span class="h-3 w-3 rounded-full bg-[#f59e0b]"></span>
      <span class="h-3 w-3 rounded-full bg-[#2BAD5F]"></span>
      <span class="ml-2 truncate text-xs text-[#8b949e]">{{ previewLabel }}</span>
    </div>
    <div class="preview-viewport bg-white" :style="viewportStyle">
      <DemoSitesDemoPlumberPreview
        v-if="templateId === 'plumber-simple'"
        embedded
        :content="content"
        :business-name="businessName"
      />
    </div>
  </div>
</template>

<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    content: Record<string, unknown>
    businessName: string
    templateId?: string
    height?: number
    previewLabel?: string
  }>(),
  {
    templateId: 'plumber-simple',
    height: 720,
    previewLabel: 'Aperçu du site',
  },
)

const viewportStyle = computed(() => ({
  height: `${props.height}px`,
  maxHeight: 'min(75vh, 800px)',
}))
</script>

<style scoped>
.preview-viewport {
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}
</style>
