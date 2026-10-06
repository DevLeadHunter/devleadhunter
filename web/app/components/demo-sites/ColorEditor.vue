<template>
  <div v-if="template" class="space-y-4">
    <div v-if="showBrandSourcePicker" role="group" aria-label="Couleur des boutons">
      <p class="app-label mb-2">Couleur des boutons</p>
      <div class="grid grid-cols-2 gap-2">
        <button
          type="button"
          :class="[
            'flex items-center gap-3 rounded-xl border p-3 text-left transition-colors',
            useBrandColor
              ? 'border-[var(--app-ink)] bg-[var(--app-surface-2)]'
              : 'border-[var(--app-line)] hover:border-[var(--app-ink-soft)]',
          ]"
          :aria-pressed="useBrandColor === true"
          @click="selectBrandSource(true)"
        >
          <span
            class="h-10 w-10 shrink-0 rounded-lg border border-black/10"
            :style="{ backgroundColor: brandColor ?? undefined }"
          ></span>
          <span class="min-w-0 flex-1">
            <span class="block text-sm font-semibold text-[var(--app-ink)]">Celle du logo</span>
            <span class="font-label block text-[11px] text-[var(--app-ink-soft)] uppercase">{{ brandColor }}</span>
          </span>
          <UIcon v-if="useBrandColor" name="i-lucide-check" class="h-4 w-4 shrink-0 text-[var(--app-ink)]" />
        </button>
        <button
          type="button"
          :class="[
            'flex items-center gap-3 rounded-xl border p-3 text-left transition-colors',
            !useBrandColor
              ? 'border-[var(--app-ink)] bg-[var(--app-surface-2)]'
              : 'border-[var(--app-line)] hover:border-[var(--app-ink-soft)]',
          ]"
          :aria-pressed="useBrandColor === false"
          @click="selectBrandSource(false)"
        >
          <span
            class="h-10 w-10 shrink-0 rounded-lg border border-black/10"
            :style="{ backgroundColor: templateActionColor ?? undefined }"
          ></span>
          <span class="min-w-0 flex-1">
            <span class="block text-sm font-semibold text-[var(--app-ink)]">Celle de la template</span>
            <span class="font-label block text-[11px] text-[var(--app-ink-soft)] uppercase">
              {{ templateActionColor }}
            </span>
          </span>
          <UIcon v-if="!useBrandColor" name="i-lucide-check" class="h-4 w-4 shrink-0 text-[var(--app-ink)]" />
        </button>
      </div>
    </div>
    <div>
      <p class="app-label mb-2.5">{{ showBrandSourcePicker ? 'Toutes les couleurs' : 'Couleurs du site' }}</p>
      <div class="flex flex-wrap gap-3">
        <div v-for="color in editableColors" :key="color.key" class="min-w-[7rem] flex-1">
          <span class="mb-1 flex items-center gap-1 text-[10px] tracking-wide text-[var(--app-ink-soft)] uppercase">
            {{ color.label }}
          </span>
          <div class="flex items-center gap-1.5">
            <div class="group relative h-10 w-10 shrink-0">
              <div
                class="pointer-events-none h-10 w-10 rounded-lg border border-[var(--app-line)] transition-transform group-hover:scale-105"
                :style="{ backgroundColor: theme[color.key] }"
              ></div>
              <input
                :value="theme[color.key]"
                type="color"
                :title="`Choisir la couleur ${color.label.toLowerCase()}`"
                :aria-label="`Choisir la couleur ${color.label.toLowerCase()}`"
                class="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                @input="onEditColor(color.key, ($event.target as HTMLInputElement).value)"
              />
            </div>
            <input
              :value="theme[color.key]"
              type="text"
              class="input-field h-10 min-w-0 text-xs"
              placeholder="#1d4ed8"
              maxlength="7"
              @input="onEditColor(color.key, ($event.target as HTMLInputElement).value)"
            />
          </div>
        </div>
      </div>
      <p class="mt-3 flex items-center gap-1.5 text-[11px] text-[var(--app-ink-soft)]">
        <UIcon name="i-lucide-info" class="h-3 w-3 shrink-0" />
        Vos couleurs s'appliquent en direct dans l'aperçu.
      </p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ColorEditorEmits, ColorEditorProps, EditableColor } from '~/types/ColorEditor'
import type { TemplateThemeColorKey } from '~/types/TemplatePicker'
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type { ColorRole, DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'

/** Site colour editor: role-driven swatches + Logo ⟷ Template action-colour source. */
const props: ColorEditorProps = defineProps({
  template: {
    type: Object as PropType<DemoSiteTemplate | null>,
    default: null,
  },
  theme: {
    type: Object as PropType<DemoSiteTheme>,
    required: true,
  },
  useBrandColor: {
    type: Boolean as PropType<boolean | null>,
    default: null,
  },
  brandColor: {
    type: String as PropType<string | null>,
    default: null,
  },
})

const emit: EmitFn<ColorEditorEmits> = defineEmits<ColorEditorEmits>()

const colorKeys: TemplateThemeColorKey[] = ['primary', 'secondary', 'accent']
const colorLabels: Record<TemplateThemeColorKey, string> = {
  primary: 'Principale',
  secondary: 'Fond',
  accent: 'Accent',
}

const ROLE_ORDER: ColorRole[] = ['action', 'fond', 'secondaire']
const ROLE_LABELS: Record<ColorRole, string> = {
  action: "Couleur d'action",
  fond: 'Fond',
  secondaire: 'Secondaire',
}

/**
 * The colours the editor exposes: the template's canonical roles (only those a layer visibly
 * uses — dead fields are hidden). Falls back to the three raw keys for a template without role metadata.
 */
const editableColors: ComputedRef<EditableColor[]> = computed((): EditableColor[] => {
  const roles: Partial<Record<ColorRole, TemplateThemeColorKey>> | undefined = props.template?.color_roles
  if (!roles || Object.keys(roles).length === 0) {
    return colorKeys.map(
      (key: TemplateThemeColorKey): EditableColor => ({
        key,
        label: colorLabels[key],
        isAction: false,
      }),
    )
  }
  return ROLE_ORDER.filter((role: ColorRole): boolean => Boolean(roles[role])).map(
    (role: ColorRole): EditableColor => ({
      key: roles[role] as TemplateThemeColorKey,
      label: ROLE_LABELS[role],
      isAction: role === 'action',
    }),
  )
})

/** The template's own default for the action colour (the « Celle de la template » card). */
const templateActionColor: ComputedRef<string | null> = computed((): string | null => {
  const tpl: DemoSiteTemplate | null = props.template
  const actionKey: TemplateThemeColorKey | undefined = tpl?.color_roles?.action ?? tpl?.brand_color_key
  return tpl && actionKey ? tpl.default_theme[actionKey] : null
})

/** Show the Logo ⟷ Template picker only on a saved site that has a usable logo colour. */
const showBrandSourcePicker: ComputedRef<boolean> = computed(
  (): boolean => props.useBrandColor !== null && Boolean(props.brandColor),
)

/** The theme key that holds the action colour, or null for a template without role metadata. */
const actionKey: ComputedRef<TemplateThemeColorKey | null> = computed(
  (): TemplateThemeColorKey | null => props.template?.color_roles?.action ?? props.template?.brand_color_key ?? null,
)

/**
 * Update a single theme color when the hex value is valid.
 * @param key - Theme key being edited.
 * @param value - Candidate hex color.
 */
function updateThemeColor(key: TemplateThemeColorKey, value: string): void {
  if (!/^#[0-9A-Fa-f]{6}$/.test(value)) return
  emit('update:theme', { ...props.theme, [key]: value })
}

/**
 * Apply a hand-picked colour and, when it is the action colour, stop deriving it from the logo — a
 * manual choice is an explicit override that must survive regeneration.
 * @param key - Theme key being edited.
 * @param value - Candidate hex color.
 */
function onEditColor(key: TemplateThemeColorKey, value: string): void {
  updateThemeColor(key, value)
  if (key === actionKey.value && props.useBrandColor === true) {
    emit('update:useBrandColor', false)
  }
}

/**
 * Pick the action-colour source: apply the colour to the theme AND flag it, so the choice sticks
 * through regeneration.
 * @param fromLogo - True → the extracted logo colour; false → the template default.
 */
function selectBrandSource(fromLogo: boolean): void {
  const action: EditableColor | undefined = editableColors.value.find((c: EditableColor): boolean => c.isAction)
  const color: string | null = (fromLogo ? (props.brandColor ?? null) : templateActionColor.value) ?? null
  if (action && color) {
    updateThemeColor(action.key, color)
  }
  emit('update:useBrandColor', fromLogo)
}
</script>
