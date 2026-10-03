<template>
  <section class="app-card flex min-w-0 flex-col overflow-hidden" aria-labelledby="campaign-results-todo-title">
    <header class="flex items-start gap-3 px-[18px] pt-4">
      <div class="min-w-0 flex-1">
        <h3 id="campaign-results-todo-title" class="text-[15px] font-medium text-[var(--app-ink)]">À traiter</h3>
        <p class="mt-0.5 text-[13px] text-[var(--app-ink-soft)]">Classé par chance de vente.</p>
      </div>
      <span v-if="props.todos.length > 0" class="text-sm text-[var(--app-ink-soft)] tabular-nums">
        {{ props.todos.length }}
      </span>
    </header>

    <ul v-if="props.todos.length > 0" class="mt-3">
      <li
        v-for="todo in visibleTodos"
        :key="todo.key"
        class="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-3.5 gap-y-1 border-t border-[var(--app-line-soft)] px-[18px] py-3.5 transition-colors hover:bg-[var(--app-surface-2)]/40 @xl:grid-cols-[auto_minmax(0,1fr)_auto] @xl:items-center"
      >
        <UIcon :name="todo.icon" class="mt-0.5 h-[18px] w-[18px] @xl:mt-0" :class="TONE_CLASSES[todo.tone]" />
        <div class="min-w-0">
          <p class="flex flex-wrap items-center gap-x-2 gap-y-1 text-[14.5px] font-medium text-[var(--app-ink)]">
            {{ todo.title }}
            <span v-if="todo.verdict" class="app-badge" :class="CAMPAIGN_RESULTS_VERDICT_BADGE_CLASSES[todo.verdict]">
              {{ CAMPAIGN_RESULTS_VERDICT_LABELS[todo.verdict] }}
            </span>
          </p>
          <p class="mt-0.5 text-[13px] leading-snug text-[var(--app-ink-soft)]">{{ todo.text }}</p>
        </div>
        <button
          type="button"
          class="col-start-2 mt-1.5 inline-flex cursor-pointer items-center gap-1.5 justify-self-start text-[13.5px] font-medium whitespace-nowrap text-[var(--app-ink)] transition-[gap] hover:gap-2.5 @xl:col-start-3 @xl:mt-0"
          @click="emit('act', todo.action)"
        >
          {{ todo.actionLabel }}
          <UIcon name="i-lucide-arrow-right" class="h-[15px] w-[15px]" />
        </button>
      </li>
    </ul>

    <p
      v-else
      class="mt-3 border-t border-[var(--app-line-soft)] px-[18px] py-4 text-[13.5px] text-[var(--app-ink-soft)]"
    >
      Rien à traiter pour l'instant : aucune réponse ni visite n'attend de suite.
    </p>

    <div v-if="hiddenTodoCount > 0" class="mt-auto border-t border-[var(--app-line-soft)] px-[18px] py-3">
      <button
        type="button"
        class="inline-flex cursor-pointer items-center gap-1.5 text-[13px] font-medium text-[var(--app-ink)]/80 transition-colors hover:text-[var(--app-ink)]"
        @click="isShowingAllTodos = true"
      >
        {{ CampaignResultsFormat.count(hiddenTodoCount, 'autre point', 'autres points') }} à traiter
        <UIcon name="i-lucide-chevron-down" class="h-[15px] w-[15px]" />
      </button>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { CampaignResultsTodo, CampaignResultsTodoTone } from '~/types/CampaignResults'
import type { CampaignResultsTodoCardEmits, CampaignResultsTodoCardProps } from '~/types/CampaignResultsTodoCard'
import { computed, ref } from 'vue'
import { CAMPAIGN_RESULTS_VERDICT_BADGE_CLASSES, CAMPAIGN_RESULTS_VERDICT_LABELS } from '~/constants/campaignResults'
import { CampaignResultsFormat } from '~/utils/campaignResultsFormat'

const props: CampaignResultsTodoCardProps = defineProps({
  todos: {
    type: Array as PropType<CampaignResultsTodo[]>,
    required: true,
  },
})

const emit: EmitFn<CampaignResultsTodoCardEmits> = defineEmits<CampaignResultsTodoCardEmits>()

const TODOS_SHOWN_FOLDED: number = 5

const TONE_CLASSES: Record<CampaignResultsTodoTone, string> = {
  green: 'text-[var(--app-green)]',
  blue: 'text-[var(--app-blue)]',
  amber: 'text-[var(--app-accent-ink)]',
  red: 'text-[var(--app-red)]',
}

const isShowingAllTodos: Ref<boolean> = ref(false)

const visibleTodos: ComputedRef<CampaignResultsTodo[]> = computed((): CampaignResultsTodo[] =>
  isShowingAllTodos.value ? props.todos : props.todos.slice(0, TODOS_SHOWN_FOLDED),
)

const hiddenTodoCount: ComputedRef<number> = computed((): number => props.todos.length - visibleTodos.value.length)
</script>
