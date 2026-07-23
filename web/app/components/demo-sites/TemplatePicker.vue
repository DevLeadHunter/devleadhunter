<template>
  <div class="grid gap-6 lg:grid-cols-2">
    <input ref="colorInputRef" type="color" class="sr-only" :value="theme[activeColorKey]" @input="onColorInput" />
    <button
      v-for="template in templates"
      :key="template.id"
      type="button"
      :class="[
        'group overflow-hidden rounded-2xl border text-left transition-all duration-300',
        modelValue === template.id
          ? 'border-[var(--app-ink)] bg-[var(--app-surface)] shadow-[var(--app-shadow-soft)] ring-1 ring-[var(--app-ink)]/15'
          : 'border-[var(--app-line)] bg-[var(--app-surface)] hover:border-[var(--app-ink-soft)] hover:shadow-md',
      ]"
      @click="selectTemplate(template)"
    >
      <div class="relative h-44 overflow-hidden border-b border-[var(--app-line)]">
        <div
          class="absolute inset-0 transition-transform duration-500 group-hover:scale-105"
          :style="{ background: previewGradient(template) }"
        >
          <div class="absolute inset-x-0 top-0 flex items-center gap-1.5 px-4 py-3">
            <span class="h-2 w-2 rounded-full bg-white/30"></span>
            <span class="h-2 w-2 rounded-full bg-white/30"></span>
            <span class="h-2 w-2 rounded-full bg-white/30"></span>
          </div>
          <div class="px-6 pt-8">
            <div class="h-2 w-16 rounded bg-white/40"></div>
            <div class="mt-4 h-4 w-3/4 max-w-[200px] rounded bg-white/80"></div>
            <div class="mt-2 h-2 w-1/2 max-w-[120px] rounded bg-white/40"></div>
            <div
              class="mt-6 inline-block rounded-lg px-4 py-2 text-xs font-bold"
              :style="{ backgroundColor: template.default_theme.accent, color: template.default_theme.secondary }"
            >
              Appeler
            </div>
          </div>
          <div class="absolute right-0 bottom-0 left-0 grid grid-cols-3 gap-2 p-4">
            <div v-for="i in 3" :key="i" class="h-8 rounded bg-white/10 backdrop-blur-sm"></div>
          </div>
        </div>
        <div
          v-if="modelValue === template.id"
          class="absolute top-3 right-3 flex h-7 w-7 items-center justify-center rounded-full bg-[var(--app-ink)] text-[var(--app-bg)]"
        >
          <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
        </div>
      </div>

      <div class="p-5">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="font-semibold text-[var(--app-ink)]">{{ template.name }}</p>
            <p class="mt-1 text-sm leading-relaxed text-[var(--app-ink-soft)]">{{ template.description }}</p>
          </div>
        </div>

        <div class="mt-4 flex items-center gap-3">
          <span class="text-xs text-[var(--app-ink-soft)]">Couleurs</span>
          <div class="flex gap-2">
            <button
              v-for="colorKey in colorKeys"
              :key="colorKey"
              type="button"
              :title="colorLabels[colorKey]"
              :class="[
                'h-7 w-7 rounded-full border-2 transition hover:scale-110',
                modelValue === template.id ? 'border-white/40' : 'border-transparent',
              ]"
              :style="{ backgroundColor: getThemeColor(template, colorKey) }"
              @click.stop="openColorPicker(template.id, colorKey)"
            />
          </div>
        </div>

        <div v-if="modelValue === template.id" class="mt-4 grid grid-cols-3 gap-2">
          <label v-for="colorKey in colorKeys" :key="colorKey" class="space-y-1">
            <span class="text-[10px] tracking-wide text-[var(--app-ink-soft)] uppercase">{{
              colorLabels[colorKey]
            }}</span>
            <input
              :value="theme[colorKey]"
              type="text"
              class="input-field h-8 text-xs"
              maxlength="7"
              @input="updateThemeColor(colorKey, ($event.target as HTMLInputElement).value)"
            />
          </label>
        </div>
      </div>
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { TemplateThemeColorKey, TemplatePickerProps } from '~/types/TemplatePicker'
import type { PropType, Ref } from 'vue'
import type { DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'

/** Demo site template picker with live theme color editing. */
const props: TemplatePickerProps = defineProps({
  templates: {
    type: Array as PropType<DemoSiteTemplate[]>,
    required: true,
  },
  modelValue: {
    type: String,
    required: true,
  },
  theme: {
    type: Object as PropType<DemoSiteTheme>,
    required: true,
  },
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:theme': [value: DemoSiteTheme]
}>()

const colorKeys: TemplateThemeColorKey[] = ['primary', 'secondary', 'accent']
const colorLabels: Record<TemplateThemeColorKey, string> = {
  primary: 'Principale',
  secondary: 'Fond',
  accent: 'Accent',
}

const colorInputRef: Ref<HTMLInputElement | null> = ref(null)
const activeColorKey: Ref<TemplateThemeColorKey> = ref('primary')

/**
 * Build a CSS gradient preview from the template theme.
 */
function previewGradient(template: DemoSiteTemplate): string {
  const t = props.modelValue === template.id ? props.theme : template.default_theme
  return `linear-gradient(135deg, ${t.secondary} 0%, ${t.primary} 100%)`
}

/**
 * Resolve a theme color for the given template and key.
 */
function getThemeColor(template: DemoSiteTemplate, key: TemplateThemeColorKey): string {
  return props.modelValue === template.id ? props.theme[key] : template.default_theme[key]
}

/**
 * Select a template and sync its default theme.
 */
function selectTemplate(template: DemoSiteTemplate): void {
  emit('update:modelValue', template.id)
  emit('update:theme', { ...template.default_theme })
}

/**
 * Open the native color picker for a template swatch.
 */
function openColorPicker(templateId: string, colorKey: TemplateThemeColorKey): void {
  if (props.modelValue !== templateId) {
    const template = props.templates.find((template) => template.id === templateId)
    if (template) selectTemplate(template)
  }
  activeColorKey.value = colorKey
  nextTick(() => {
    colorInputRef.value?.click()
  })
}

/**
 * Handle a color input change from the hidden picker.
 */
function onColorInput(event: Event): void {
  updateThemeColor(activeColorKey.value, (event.target as HTMLInputElement).value)
}

/**
 * Update a single theme color when the hex value is valid.
 */
function updateThemeColor(key: TemplateThemeColorKey, value: string): void {
  if (!/^#[0-9A-Fa-f]{6}$/.test(value)) return
  emit('update:theme', { ...props.theme, [key]: value })
}
</script>
