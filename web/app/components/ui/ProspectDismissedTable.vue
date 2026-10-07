<template>
  <div class="overflow-hidden">
    <BaseTable min-width="860px" is-stacked-on-touch-tablet>
      <template #head>
        <BaseTableTh>Nom</BaseTableTh>
        <BaseTableTh>Raison</BaseTableTh>
        <BaseTableTh>Écarté</BaseTableTh>
        <BaseTableTh align="right" sr-only>Action</BaseTableTh>
      </template>

      <BaseTableTr
        v-for="prospect in props.prospects"
        :key="prospect.id"
        class="cursor-pointer"
        @click="onRowClick(prospect, $event)"
      >
        <BaseTableTd>
          <button
            type="button"
            class="cursor-pointer text-left text-sm font-semibold text-[var(--app-ink)] underline decoration-transparent underline-offset-4 transition-colors hover:decoration-[var(--app-accent)]"
            @click="emit('open', prospect)"
          >
            {{ prospect.name }}
          </button>
          <p class="mt-0.5 flex items-center gap-1.5 text-[11px] text-[var(--app-ink-soft)]">
            <UiCountryFlag
              v-if="prospect.country && prospect.country !== 'FR'"
              :code="prospect.country"
              :title="ProspectCountries.option(prospect.country).label"
              size="compact"
            />
            <span>{{ [prospect.category, prospect.city].filter(Boolean).join(' · ') }}</span>
          </p>
        </BaseTableTd>

        <BaseTableTd label="Raison" is-long-text>
          <span class="block text-sm text-[var(--app-ink)] md:max-w-[420px]">{{ prospect.dismissal_reason }}</span>
        </BaseTableTd>

        <BaseTableTd label="Écarté" class="whitespace-nowrap">
          <div>
            <span class="font-label block text-xs text-[var(--app-ink-soft)]">
              {{ formatRelativeTime(prospect.dismissed_at) }}
            </span>
            <span class="mt-0.5 block text-[11px] text-[var(--app-ink-soft)]">
              {{ prospect.dismissed_by_user_id === null ? "Par l'app" : 'À la main' }}
            </span>
          </div>
        </BaseTableTd>

        <BaseTableTd align="right">
          <button
            type="button"
            class="app-btn-secondary h-10 min-h-10 w-full px-3 text-xs md:w-auto pointer-coarse:min-h-11 md:pointer-fine:h-9 md:pointer-fine:min-h-9"
            :disabled="isRestoring(prospect)"
            @click="emit('restore', prospect)"
          >
            <UIcon
              :name="isRestoring(prospect) ? 'i-lucide-loader-circle' : 'i-lucide-undo-2'"
              :class="['h-3.5 w-3.5', isRestoring(prospect) && 'animate-spin']"
            />
            Remettre dans mes prospects
          </button>
        </BaseTableTd>
      </BaseTableTr>
    </BaseTable>
  </div>
</template>

<script lang="ts" setup>
import type { EmitFn, PropType } from 'vue'
import type { Prospect } from '~/types'
import type { UiProspectDismissedTableEmits, UiProspectDismissedTableProps } from '~/types/UiProspectDismissedTable'
import { formatRelativeTime } from '~/utils/date'
import { ProspectCountries } from '~/utils/prospectCountries'

const props: UiProspectDismissedTableProps = defineProps({
  prospects: {
    type: Array as PropType<Prospect[]>,
    required: true,
  },
  restoringProspectIds: {
    type: Array as PropType<number[]>,
    required: true,
  },
})

const emit: EmitFn<UiProspectDismissedTableEmits> = defineEmits<UiProspectDismissedTableEmits>()

/**
 * Whether a prospect is being taken back.
 * @param prospect - The prospect of the row.
 * @returns True while its button must stay still.
 */
function isRestoring(prospect: Prospect): boolean {
  return props.restoringProspectIds.includes(prospect.id)
}

/**
 * Open the prospect when a bare part of its row is clicked, leaving the button to its own handler.
 * @param prospect - The prospect of the clicked row.
 * @param event - The native click event.
 */
function onRowClick(prospect: Prospect, event: MouseEvent): void {
  const target: HTMLElement | null = event.target instanceof HTMLElement ? event.target : null
  if (target?.closest('button, a, input, label, select, textarea')) return
  emit('open', prospect)
}
</script>
