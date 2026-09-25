<template>
  <div class="ai-langs" role="group" aria-label="Langue">
    <button
      v-for="code in props.languages"
      :key="code"
      type="button"
      class="ai-langs__pill"
      :aria-pressed="code === props.modelValue"
      @click="emit('update:modelValue', code)"
    >
      {{ LANGUAGE_LABELS[code] }}
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { EmitFn, PropType } from 'vue'
import type { AssistantWidgetLang } from '~/types/AiAssistant'
import type {
  AssistantChatLanguagePillsEmits,
  AssistantChatLanguagePillsProps,
} from '~/types/AssistantChatLanguagePills'
import { LANGUAGE_LABELS } from '~/constants/AssistantWidgetLabels'

const props: AssistantChatLanguagePillsProps = defineProps({
  languages: {
    type: Array as PropType<AssistantWidgetLang[]>,
    required: true,
  },
  modelValue: {
    type: String as PropType<AssistantWidgetLang>,
    required: true,
  },
})

const emit: EmitFn<AssistantChatLanguagePillsEmits> = defineEmits<AssistantChatLanguagePillsEmits>()
</script>

<style scoped>
.ai-langs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 14px 0;
  background: var(--ai-paper-2);
}
.ai-langs__pill {
  border: 1px solid var(--ai-line);
  background: var(--ai-card);
  color: var(--ai-ink-dim);
  font: inherit;
  font-size: 0.72rem;
  font-weight: 500;
  padding: 6px 11px;
  border-radius: 999px;
  cursor: pointer;
}
.ai-langs__pill[aria-pressed='true'] {
  border-color: var(--ai-ink);
  color: var(--ai-ink);
}
</style>
