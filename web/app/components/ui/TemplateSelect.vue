<template>
  <div>
    <div class="flex items-center gap-2">
      <!-- Portalled to body with no z-index of its own: without this it opens behind a drawer. -->
      <USelectMenu
        :model-value="selectedItem"
        :items="items"
        :search-input="{ placeholder: 'Rechercher un modèle…' }"
        placeholder="— Sélectionner un modèle —"
        :ui="{ content: 'z-[110]' }"
        class="min-w-0 flex-1"
        @update:model-value="onSelect"
      />
      <button
        v-if="selected"
        type="button"
        class="app-btn-secondary h-9 shrink-0 px-3 text-xs"
        title="Aperçu du modèle"
        aria-label="Aperçu du modèle"
        @click="emit('preview', selected.id)"
      >
        <UIcon name="i-lucide-eye" class="h-3.5 w-3.5" />
      </button>
      <button
        v-if="allowCreate"
        type="button"
        class="app-btn-primary h-9 shrink-0 px-3 text-xs whitespace-nowrap"
        @click="emit('create')"
      >
        <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
        Nouveau
      </button>
    </div>

    <p v-if="selected" class="mt-1.5 flex items-center gap-1.5 text-xs text-[var(--app-ink-soft)]">
      <UIcon name="i-lucide-mail" class="h-3 w-3 shrink-0" />
      <span class="truncate italic">Objet : {{ selected.subject }}</span>
    </p>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import { computed } from 'vue'
import type {
  TemplateSelectEmits,
  TemplateSelectItem,
  TemplateSelectOption,
  TemplateSelectProps,
} from '~/types/TemplateSelect'

/** Searchable email template picker, with inline preview and create actions. */
const props: TemplateSelectProps = defineProps({
  modelValue: {
    type: Number as PropType<number | null>,
    default: null,
  },
  templates: {
    type: Array as PropType<TemplateSelectOption[]>,
    required: true,
  },
  allowCreate: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<TemplateSelectEmits> = defineEmits<TemplateSelectEmits>()

/** Menu entries: the active templates, plus the selected one even if it was deactivated since. */
const items: ComputedRef<TemplateSelectItem[]> = computed((): TemplateSelectItem[] =>
  props.templates
    .filter((template: TemplateSelectOption): boolean => template.is_active || template.id === props.modelValue)
    .map(
      (template: TemplateSelectOption): TemplateSelectItem => ({
        value: template.id,
        label: template.name,
        description: template.subject,
      }),
    ),
)

const selected: ComputedRef<TemplateSelectOption | undefined> = computed((): TemplateSelectOption | undefined =>
  props.templates.find((template: TemplateSelectOption): boolean => template.id === props.modelValue),
)

const selectedItem: ComputedRef<TemplateSelectItem | undefined> = computed((): TemplateSelectItem | undefined =>
  items.value.find((item: TemplateSelectItem): boolean => item.value === props.modelValue),
)

/**
 * Relay the picked menu entry as its numeric template id.
 * @param item - Entry chosen in the menu, undefined when cleared.
 */
function onSelect(item: TemplateSelectItem | undefined): void {
  emit('update:modelValue', item?.value ?? 0)
}
</script>
