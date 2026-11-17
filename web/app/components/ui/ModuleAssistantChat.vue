<template>
  <div class="mx-auto flex min-h-full w-full max-w-180 flex-col">
    <header class="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
      <div class="min-w-0">
        <h1 class="app-page-title">{{ MODULE_ASSISTANT_LABEL }}</h1>
        <p v-if="!hasStartedConversation && home !== null" class="mt-1.5 text-sm text-[var(--app-ink-soft)]">
          {{ home.lead }}
        </p>
      </div>
      <button
        v-if="hasStartedConversation"
        type="button"
        class="app-btn-secondary @max-xl:w-11 @max-xl:px-0 pointer-coarse:min-h-11"
        @click="startNewConversation"
      >
        <UIcon name="i-lucide-plus" class="size-4" aria-hidden="true" />
        <span class="@max-xl:sr-only">Nouvelle conversation</span>
      </button>
    </header>

    <section v-if="!hasStartedConversation" class="mt-5" aria-label="Suggestions de questions">
      <UiLoader v-if="home === null && isLoadingHome" label="Chargement de l’assistant…" />
      <template v-else-if="home !== null">
        <p class="app-label mb-2.5">Suggestions</p>
        <div class="flex flex-col gap-3">
          <button
            v-for="suggestion in home.suggestions"
            :key="suggestion.label"
            type="button"
            class="flex min-h-16 w-full cursor-pointer items-center gap-3.5 rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] py-3 pr-4 pl-3 text-left transition-colors hover:border-[var(--app-ink-soft)] focus-visible:border-[var(--app-ink)] focus-visible:outline-none"
            @click="sendQuestion(suggestion.label)"
          >
            <span
              class="flex size-10 shrink-0 items-center justify-center rounded-xl"
              :class="MODULE_ASSISTANT_TONE_CLASSES[suggestion.tone]"
              aria-hidden="true"
            >
              <UIcon :name="suggestion.icon" class="size-5" />
            </span>
            <span class="min-w-0 flex-1 text-sm leading-normal text-[var(--app-ink)]">{{ suggestion.label }}</span>
            <UIcon
              name="i-lucide-corner-down-left"
              class="size-4 shrink-0 text-[var(--app-ink-soft)]"
              aria-hidden="true"
            />
          </button>
        </div>
      </template>
    </section>

    <div v-else class="mt-5 flex flex-col gap-7" aria-live="polite">
      <article
        v-for="(exchange, exchangeIndex) in exchanges"
        :key="exchange.id"
        ref="exchangeElements"
        class="flex scroll-mt-5 flex-col gap-4"
        :class="{ 'min-h-[calc(100dvh-19rem)]': exchangeIndex === exchanges.length - 1 }"
      >
        <p
          class="max-w-[86%] self-end rounded-[18px_18px_4px_18px] bg-[var(--app-surface-2)] px-3.5 py-2 text-sm text-[var(--app-ink)]"
        >
          {{ exchange.question }}
        </p>

        <div v-if="exchange.hasFailed" class="flex flex-col items-start gap-2">
          <p class="text-[15px] leading-normal text-[var(--app-ink)]">
            La réponse n’a pas pu être préparée. Vérifiez votre connexion et réessayez.
          </p>
          <button type="button" class="app-btn-secondary pointer-coarse:min-h-11" @click="retryExchange(exchange)">
            <UIcon name="i-lucide-refresh-cw" class="size-4" aria-hidden="true" />
            Réessayer
          </button>
        </div>

        <p v-else-if="exchange.answer === null" class="flex items-center gap-2 text-sm text-[var(--app-ink-soft)]">
          <UIcon
            name="i-lucide-loader-circle"
            class="size-4 animate-spin motion-reduce:animate-none"
            aria-hidden="true"
          />
          Recherche en cours…
        </p>

        <div v-else class="flex flex-col gap-3.5">
          <p class="text-[15px] leading-normal whitespace-pre-line text-[var(--app-ink)]">{{ exchange.answer.text }}</p>

          <div v-if="exchange.answer.cards.length > 0" class="grid grid-cols-1 gap-3.5 @2xl:grid-cols-2">
            <template v-for="(card, cardIndex) in exchange.answer.cards" :key="cardIndex">
              <slot name="card" :card="card" />
            </template>
          </div>

          <UiBarChart
            v-if="exchange.answer.chart !== null"
            :title="exchange.answer.chart.title"
            :bars="exchange.answer.chart.bars"
          />

          <UiModuleAssistantHighlightCard
            v-if="exchange.answer.highlight !== null"
            :highlight="exchange.answer.highlight"
          />

          <div
            v-if="exchangeIndex === exchanges.length - 1 && exchange.answer.next_questions.length > 0"
            class="flex flex-col items-start gap-2"
          >
            <button
              v-for="nextQuestion in exchange.answer.next_questions"
              :key="nextQuestion"
              type="button"
              class="min-h-11 cursor-pointer rounded-full border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-2 text-left text-sm text-[var(--app-ink)] transition-colors hover:border-[var(--app-ink-soft)]"
              @click="sendQuestion(nextQuestion)"
            >
              {{ nextQuestion }}
            </button>
          </div>
        </div>
      </article>
    </div>

    <form
      class="sticky bottom-0 mt-auto bg-[var(--app-bg)] pt-3 pb-1 shadow-[0_2.5rem_0_0_var(--app-bg)]"
      @submit.prevent="submitDraftQuestion"
    >
      <div
        class="flex min-h-12.5 items-center gap-1.5 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)] pr-1.5 pl-4 focus-within:border-[var(--app-ink-soft)]"
      >
        <input
          v-model="draftQuestion"
          type="text"
          enterkeyhint="send"
          autocomplete="off"
          :maxlength="MODULE_ASSISTANT_QUESTION_MAXIMUM_LENGTH"
          placeholder="Posez votre question"
          aria-label="Votre question"
          class="h-11 min-w-0 flex-1 border-0 bg-transparent text-base text-[var(--app-ink)] outline-none placeholder:text-[var(--app-ink-soft)]"
        />
        <button
          type="submit"
          :disabled="!canSubmitDraftQuestion"
          aria-label="Envoyer la question"
          class="flex size-9.5 shrink-0 cursor-pointer items-center justify-center rounded-full bg-[var(--app-btn-bg)] text-[var(--app-btn-text)] transition-opacity disabled:cursor-default disabled:opacity-40"
        >
          <UIcon name="i-lucide-arrow-up" class="size-5" aria-hidden="true" />
        </button>
      </div>
    </form>
  </div>
</template>

<script lang="ts" setup generic="AnswerCard">
import type { ComputedRef, PropType, Ref, ShallowRef } from 'vue'
import type {
  ModuleAssistantAnswer,
  ModuleAssistantExchange,
  ModuleAssistantHome,
  ModuleAssistantPastExchange,
} from '~/types/ModuleAssistant'
import type { UiModuleAssistantChatProps } from '~/types/UiModuleAssistantChat'
import { computed, nextTick, onMounted, ref, useTemplateRef } from 'vue'
import {
  MODULE_ASSISTANT_HISTORY_MAXIMUM_LENGTH,
  MODULE_ASSISTANT_LABEL,
  MODULE_ASSISTANT_QUESTION_MAXIMUM_LENGTH,
  MODULE_ASSISTANT_TONE_CLASSES,
} from '~/constants/moduleAssistant'

/** The chat of a module's assistant; the `card` slot draws one record of an answer, with the module's own card. */
const props: UiModuleAssistantChatProps<AnswerCard> = defineProps({
  conversationKey: {
    type: String,
    required: true,
  },
  loadHome: {
    type: Function as PropType<() => Promise<ModuleAssistantHome>>,
    required: true,
  },
  askQuestion: {
    type: Function as PropType<
      (question: string, history: ModuleAssistantPastExchange[]) => Promise<ModuleAssistantAnswer<AnswerCard>>
    >,
    required: true,
  },
})

defineSlots<{
  card: (slotProps: { card: AnswerCard }) => unknown
}>()

const exchangeElements: Readonly<ShallowRef<HTMLElement[] | null>> = useTemplateRef<HTMLElement[]>('exchangeElements')

const home: Ref<ModuleAssistantHome | null> = ref(null)
const isLoadingHome: Ref<boolean> = ref(true)
const exchanges: Ref<ModuleAssistantExchange<AnswerCard>[]> = useState(
  `module-assistant-conversation:${props.conversationKey}`,
  (): ModuleAssistantExchange<AnswerCard>[] => [],
)
const draftQuestion: Ref<string> = ref('')

const hasStartedConversation: ComputedRef<boolean> = computed((): boolean => exchanges.value.length > 0)

const isAwaitingAnswer: ComputedRef<boolean> = computed((): boolean =>
  exchanges.value.some(
    (exchange: ModuleAssistantExchange<AnswerCard>): boolean => exchange.answer === null && !exchange.hasFailed,
  ),
)

const canSubmitDraftQuestion: ComputedRef<boolean> = computed(
  (): boolean => draftQuestion.value.trim().length > 0 && !isAwaitingAnswer.value,
)

/**
 * Read the sentence under the title and the suggestions.
 * @returns A promise resolved once they are shown; a failure leaves the question field alone on screen.
 */
async function loadAssistantHome(): Promise<void> {
  try {
    home.value = await props.loadHome()
  } catch {
    home.value = null
  } finally {
    isLoadingHome.value = false
  }
}

/**
 * Bring the last question to the top of the screen, its answer coming under it.
 * @returns A promise resolved once the question is in view.
 */
async function revealLastExchange(): Promise<void> {
  await nextTick()
  exchangeElements.value?.at(-1)?.scrollIntoView({ block: 'start', behavior: 'smooth' })
}

/**
 * The answered exchanges that came before one, as the API reads the conversation so far.
 * @param exchangeId - The exchange being asked.
 * @returns Their questions and the words of their answers, oldest first.
 */
function listPastExchanges(exchangeId: number): ModuleAssistantPastExchange[] {
  const pastExchanges: ModuleAssistantPastExchange[] = []

  for (const exchange of exchanges.value) {
    if (exchange.id < exchangeId && exchange.answer !== null) {
      pastExchanges.push({
        question: exchange.question,
        answer: exchange.answer.text,
        context: exchange.answer.context,
      })
    }
  }
  return pastExchanges.slice(-MODULE_ASSISTANT_HISTORY_MAXIMUM_LENGTH)
}

/**
 * Ask the question of an exchange and store its answer.
 * @param exchangeId - The exchange awaiting its answer.
 * @param question - The question to ask.
 * @returns A promise resolved once the answer, or its failure, is shown.
 */
async function answerExchange(exchangeId: number, question: string): Promise<void> {
  let answer: ModuleAssistantAnswer<AnswerCard> | null = null
  try {
    answer = await props.askQuestion(question, listPastExchanges(exchangeId))
  } catch {
    answer = null
  }
  const answeredExchange: ModuleAssistantExchange<AnswerCard> | undefined = exchanges.value.find(
    (exchange: ModuleAssistantExchange<AnswerCard>): boolean => exchange.id === exchangeId,
  )

  if (answeredExchange === undefined) {
    return
  }
  answeredExchange.answer = answer
  answeredExchange.hasFailed = answer === null
}

/**
 * Send a question: it joins the conversation, then its answer is awaited.
 * @param question - The question, typed or picked among the suggestions.
 * @returns A promise resolved once the answer, or its failure, is shown.
 */
async function sendQuestion(question: string): Promise<void> {
  const trimmedQuestion: string = question.trim()

  if (trimmedQuestion.length === 0 || isAwaitingAnswer.value) {
    return
  }
  const exchangeId: number =
    Math.max(0, ...exchanges.value.map((exchange: ModuleAssistantExchange<AnswerCard>): number => exchange.id)) + 1
  exchanges.value.push({ id: exchangeId, question: trimmedQuestion, answer: null, hasFailed: false })
  draftQuestion.value = ''
  revealLastExchange()
  await answerExchange(exchangeId, trimmedQuestion)
}

/** Send what the question field holds. */
function submitDraftQuestion(): void {
  if (canSubmitDraftQuestion.value) {
    sendQuestion(draftQuestion.value)
  }
}

/**
 * Ask again a question whose answer failed.
 * @param exchange - The failed exchange.
 * @returns A promise resolved once the answer, or its failure, is shown.
 */
async function retryExchange(exchange: ModuleAssistantExchange<AnswerCard>): Promise<void> {
  if (isAwaitingAnswer.value) {
    return
  }
  exchange.hasFailed = false
  await answerExchange(exchange.id, exchange.question)
}

/** Empty the conversation and come back to the suggestions. */
function startNewConversation(): void {
  exchanges.value = []
  draftQuestion.value = ''
}

onMounted((): void => {
  loadAssistantHome()
})
</script>
