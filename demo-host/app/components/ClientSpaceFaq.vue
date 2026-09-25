<template>
  <ClientSpaceSection title="Ce que vos clients demandent" :meta="metaLabel">
    <p v-if="props.unanswered.length === 0 && props.faq.length === 0" class="cs-muted">
      Dès qu'un visiteur pose une question à laquelle {{ props.assistantName }} ne sait pas répondre, elle apparaît ici.
      Répondez en une phrase : {{ props.assistantName }} la reprendra telle quelle.
    </p>

    <ul v-if="props.unanswered.length > 0" class="csf__list">
      <li v-for="(entry, index) in props.unanswered" :key="entry.question" class="csf__item">
        <p class="csf__question">
          « {{ entry.question }} »
          <span v-if="entry.count > 1" class="csf__count">demandé {{ entry.count }} fois</span>
        </p>
        <template v-if="props.readOnly" />
        <template v-else-if="openIndex === index">
          <textarea
            v-model="draft"
            class="cs-input csf__answer"
            rows="3"
            maxlength="1000"
            placeholder="Votre réponse, comme vous la diriez au téléphone"
            :disabled="props.isBusy"
          />
          <div class="csf__actions">
            <button type="button" class="cs-button" :disabled="!draft.trim() || props.isBusy" @click="submit(entry)">
              {{ props.isBusy ? 'Enregistrement…' : 'Enregistrer la réponse' }}
            </button>
            <button type="button" class="cs-button cs-button--outline" :disabled="props.isBusy" @click="closeAnswer">
              Annuler
            </button>
          </div>
        </template>
        <div v-else class="csf__actions">
          <button
            type="button"
            class="cs-button cs-button--outline"
            :disabled="props.isBusy"
            @click="openAnswer(index)"
          >
            Répondre
          </button>
          <button type="button" class="csf__dismiss" :disabled="props.isBusy" @click="emit('dismiss', index)">
            Ignorer
          </button>
        </div>
      </li>
    </ul>

    <div v-if="props.faq.length > 0" class="csf__faq">
      <p class="cs-label">Vos réponses ({{ props.faq.length }})</p>
      <dl class="csf__answers">
        <template v-for="entry in props.faq" :key="`${entry.question}-${entry.created_at}`">
          <dt class="csf__faq-question">{{ entry.question }}</dt>
          <dd class="csf__faq-answer">{{ entry.answer }}</dd>
        </template>
      </dl>
    </div>

    <p v-if="props.errorMessage" class="cs__notice cs__notice--error">{{ props.errorMessage }}</p>
  </ClientSpaceSection>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import { computed, ref } from 'vue'
import type { AiAssistantClientFaqEntry, AiAssistantClientUnansweredEntry } from '~/types/AiAssistantClientSpace'
import type { ClientSpaceFaqEmits, ClientSpaceFaqProps } from '~/types/ClientSpaceFaq'

/** The questions visitors asked without an answer, each with a field to answer it, then the answers in place. */
const props: ClientSpaceFaqProps = defineProps({
  assistantName: {
    type: String,
    required: true,
  },
  unanswered: {
    type: Array as PropType<AiAssistantClientUnansweredEntry[]>,
    required: true,
  },
  faq: {
    type: Array as PropType<AiAssistantClientFaqEntry[]>,
    required: true,
  },
  isBusy: {
    type: Boolean,
    default: false,
  },
  errorMessage: {
    type: String as PropType<string | null>,
    default: null,
  },
  readOnly: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<ClientSpaceFaqEmits> = defineEmits<ClientSpaceFaqEmits>()

/** The question being answered, as its position in the list; none when -1. */
const openIndex: Ref<number> = ref(-1)
const draft: Ref<string> = ref('')

const metaLabel: ComputedRef<string | null> = computed((): string | null =>
  props.unanswered.length > 0 ? `${props.unanswered.length} sans réponse` : null,
)

/**
 * Open the answer field under a question.
 * @param index - The question's position.
 */
function openAnswer(index: number): void {
  openIndex.value = index
  draft.value = ''
}

/** Close the answer field without recording anything. */
function closeAnswer(): void {
  openIndex.value = -1
  draft.value = ''
}

/**
 * Hand the answer over, then close the field.
 * @param entry - The question answered.
 */
function submit(entry: AiAssistantClientUnansweredEntry): void {
  const answer: string = draft.value.trim()
  if (!answer) return
  emit('answer', entry.question, answer)
  closeAnswer()
}
</script>

<style scoped>
.csf__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 14px;
}
.csf__item {
  display: grid;
  gap: 10px;
  padding: 14px 16px;
  border: 1px solid var(--cs-line);
  border-radius: 14px;
  background: var(--cs-card);
}
.csf__question {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.45;
}
.csf__count {
  margin-left: 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--cs-ink-dim);
}
.csf__answer {
  resize: vertical;
  min-height: 84px;
  font: inherit;
}
.csf__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.csf__dismiss {
  border: 0;
  background: transparent;
  color: var(--cs-ink-dim);
  font: inherit;
  font-size: 13px;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
  padding: 8px 4px;
}
.csf__dismiss:disabled {
  cursor: default;
  opacity: 0.6;
}
.csf__faq {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}
.csf__answers {
  margin: 0;
  display: grid;
  gap: 12px;
}
.csf__faq-question {
  font-weight: 600;
  font-size: 14px;
}
.csf__faq-answer {
  margin: 2px 0 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--cs-ink-dim);
}
</style>
