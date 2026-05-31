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
          ? 'border-[#f9f9f9] bg-[#1a1a1a] shadow-lg ring-1 shadow-white/5 ring-[#f9f9f9]/20'
          : 'border-[#30363d] bg-[#1a1a1a] hover:border-[#484f58] hover:shadow-md',
      ]"
      @click="selectTemplate(template)"
    >
      <!-- Mini preview mockup -->
      <div class="relative h-44 overflow-hidden border-b border-[#30363d]">
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
          class="absolute top-3 right-3 flex h-7 w-7 items-center justify-center rounded-full bg-[#f9f9f9] text-[#050505]"
        >
          <i class="fa-solid fa-check text-xs"></i>
        </div>
      </div>

      <div class="p-5">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="font-semibold text-[#f9f9f9]">{{ template.name }}</p>
            <p class="mt-1 text-sm leading-relaxed text-[#8b949e]">{{ template.description }}</p>
          </div>
        </div>

        <!-- Color swatches -->
        <div class="mt-4 flex items-center gap-3">
          <span class="text-xs text-[#8b949e]">Couleurs</span>
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
            <span class="text-[10px] tracking-wide text-[#8b949e] uppercase">{{ colorLabels[colorKey] }}</span>
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
import type { DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'

const props = defineProps<{
  templates: DemoSiteTemplate[]
  modelValue: string
  theme: DemoSiteTheme
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:theme': [value: DemoSiteTheme]
}>()

type ColorKey = keyof DemoSiteTheme

const colorKeys: ColorKey[] = ['primary', 'secondary', 'accent']
const colorLabels: Record<ColorKey, string> = {
  primary: 'Principale',
  secondary: 'Fond',
  accent: 'Accent',
}

const colorInputRef = ref<HTMLInputElement | null>(null)
const activeColorKey = ref<ColorKey>('primary')

function previewGradient(template: DemoSiteTemplate): string {
  const t = props.modelValue === template.id ? props.theme : template.default_theme
  return `linear-gradient(135deg, ${t.secondary} 0%, ${t.primary} 100%)`
}

function getThemeColor(template: DemoSiteTemplate, key: ColorKey): string {
  return props.modelValue === template.id ? props.theme[key] : template.default_theme[key]
}

function selectTemplate(template: DemoSiteTemplate): void {
  emit('update:modelValue', template.id)
  emit('update:theme', { ...template.default_theme })
}

function openColorPicker(templateId: string, colorKey: ColorKey): void {
  if (props.modelValue !== templateId) {
    const template = props.templates.find((t) => t.id === templateId)
    if (template) selectTemplate(template)
  }
  activeColorKey.value = colorKey
  nextTick(() => {
    colorInputRef.value?.click()
  })
}

function onColorInput(event: Event): void {
  updateThemeColor(activeColorKey.value, (event.target as HTMLInputElement).value)
}

function updateThemeColor(key: ColorKey, value: string): void {
  if (!/^#[0-9A-Fa-f]{6}$/.test(value)) return
  emit('update:theme', { ...props.theme, [key]: value })
}
</script>
