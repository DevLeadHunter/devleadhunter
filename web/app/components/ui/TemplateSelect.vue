<template>
  <div>
    <UiTemplateSelectCreateLink v-if="showCreateTop" wrapper-class="mb-1.5" @click="emit('create')" />

    <div class="relative">
      <select :value="modelValue ?? 0" class="input-field appearance-none pr-9" @change="onChange">
        <option :value="0">— Sélectionner un template —</option>
        <option v-for="tpl in templates" :key="tpl.id" :value="tpl.id">
          {{ tpl.name }}
        </option>
      </select>
      <UIcon
        name="i-lucide-chevron-down"
        class="pointer-events-none absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2 text-[var(--app-ink-soft)]"
      />
    </div>
    <p v-if="selected" class="text-muted mt-1.5 flex items-center gap-1.5 text-xs">
      <UIcon name="i-lucide-mail" class="h-3 w-3 shrink-0" />
      <span class="truncate italic">Objet : {{ selected.subject }}</span>
    </p>

    <UiTemplateSelectCreateLink v-if="showCreateBottom" wrapper-class="mt-1.5" @click="emit('create')" />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type {
  TemplateSelectCreateButtonPosition,
  TemplateSelectOption,
  TemplateSelectProps,
} from '~/types/TemplateSelect'

/** Email template picker with optional inline create action. */
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
  createButtonPosition: {
    type: String as PropType<TemplateSelectCreateButtonPosition>,
    default: 'top',
  },
})

const emit: {
  /** Fired when the selection changes. ``0`` means "none". */
  (e: 'update:modelValue', value: number): void
  /** Fired when the user asks to create a new template (parent opens the drawer). */
  (e: 'create'): void
} = defineEmits<{
  /** Fired when the selection changes. ``0`` means "none". */
  (e: 'update:modelValue', value: number): void
  /** Fired when the user asks to create a new template (parent opens the drawer). */
  (e: 'create'): void
}>()

const selected: ComputedRef<TemplateSelectOption | undefined> = computed((): TemplateSelectOption | undefined =>
  props.templates.find((t: TemplateSelectOption): boolean => t.id === props.modelValue),
)

const showCreateTop: ComputedRef<boolean> = computed(
  (): boolean =>
    Boolean(props.allowCreate) && (props.createButtonPosition === 'top' || props.createButtonPosition === 'both'),
)

const showCreateBottom: ComputedRef<boolean> = computed(
  (): boolean =>
    Boolean(props.allowCreate) && (props.createButtonPosition === 'bottom' || props.createButtonPosition === 'both'),
)

/**
 * Emit the new numeric template ID on change.
 * @param event - Native select change event.
 */
function onChange(event: Event): void {
  const value: number = Number((event.target as HTMLSelectElement).value)
  emit('update:modelValue', value)
}
</script>
