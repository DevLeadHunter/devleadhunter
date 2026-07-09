<template>
  <div class="overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full min-w-[720px] border-collapse">
        <thead>
          <tr class="bg-[var(--app-surface-2)]">
            <th class="w-12 border-b border-[var(--app-line)] px-4 py-3 text-left">
              <input
                type="checkbox"
                class="h-4 w-4 cursor-pointer accent-(--app-accent)"
                :checked="allSelected"
                :indeterminate.prop="someSelected && !allSelected"
                aria-label="Tout sélectionner sur cette page"
                @change="onToggleAll"
              />
            </th>
            <th class="app-label border-b border-[var(--app-line)] px-4 py-3 text-left">Nom</th>
            <th class="app-label border-b border-[var(--app-line)] px-4 py-3 text-left">Ville</th>
            <th class="app-label border-b border-[var(--app-line)] px-4 py-3 text-left">Téléphone</th>
            <th class="app-label border-b border-[var(--app-line)] px-4 py-3 text-left">Email</th>
            <th class="app-label border-b border-[var(--app-line)] px-4 py-3 text-left">Site web</th>
            <th class="app-label border-b border-[var(--app-line)] px-4 py-3 text-left">Contacté</th>
            <th class="app-label border-b border-[var(--app-line)] px-4 py-3 text-left">Source</th>
            <th class="border-b border-[var(--app-line)] px-4 py-3 text-center">
              <span class="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="prospect in prospects"
            :key="prospect.id"
            class="group border-b border-[var(--app-line-soft)] transition-colors last:border-b-0 hover:bg-[var(--app-surface-2)]/60"
            :class="isSelected(prospect) ? 'bg-[var(--app-accent-soft)]' : ''"
          >
            <!-- Row selection -->
            <td class="px-4 py-3.5">
              <input
                type="checkbox"
                class="h-4 w-4 cursor-pointer accent-(--app-accent)"
                :checked="isSelected(prospect)"
                :aria-label="`Sélectionner ${prospect.name}`"
                @change="emit('toggleSelect', prospect)"
              />
            </td>

            <!-- Name — clickable to open detail drawer -->
            <td class="px-4 py-3.5">
              <button
                type="button"
                class="cursor-pointer text-left text-sm font-semibold text-[var(--app-ink)] underline decoration-transparent underline-offset-4 transition-colors hover:decoration-[var(--app-accent)]"
                @click="emit('viewProspect', prospect)"
              >
                {{ prospect.name }}
              </button>
            </td>

            <td class="px-4 py-3.5 text-sm text-[var(--app-ink-soft)]">{{ prospect.city || '—' }}</td>

            <td class="font-label px-4 py-3.5 text-xs text-[var(--app-ink-soft)]">{{ prospect.phone || '—' }}</td>

            <td class="px-4 py-3.5">
              <span v-if="prospect.email" class="font-label text-xs text-[var(--app-ink)]">{{ prospect.email }}</span>
              <span v-else class="text-sm text-[var(--app-faint)]">—</span>
            </td>

            <!-- Website: no website = the amber opportunity, not an error -->
            <td class="px-4 py-3.5">
              <span v-if="prospect.website" class="app-badge">
                <UIcon name="i-lucide-circle-check" class="h-3 w-3" />
                Oui
              </span>
              <span v-else class="app-badge app-badge--progress">
                <UIcon name="i-lucide-sparkle" class="h-3 w-3" />
                Non
              </span>
            </td>

            <!-- Contacted status (read-only — toggle lives in the prospect drawer) -->
            <td class="px-4 py-3.5">
              <span v-if="prospect.contacted" class="app-badge app-badge--success">
                <UIcon name="i-lucide-circle-check" class="h-3 w-3" />
                Oui
              </span>
              <span v-else class="app-badge">Non</span>
            </td>

            <td class="px-4 py-3.5">
              <UiProspectSourceBadge :source="prospect.source" />
            </td>

            <!-- Delete quick action (revealed on row hover) -->
            <td class="px-4 py-3.5 text-center">
              <button
                type="button"
                class="inline-flex h-7 w-7 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] opacity-0 transition-all group-hover:opacity-100 hover:bg-[var(--app-red-soft)] hover:text-[var(--app-red)] focus-visible:opacity-100"
                title="Supprimer ce prospect"
                @click="emit('deleteProspect', prospect)"
              >
                <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <div v-if="prospects.length === 0" class="py-12 text-center">
      <LandingAsterisk class="mb-3 text-3xl text-[var(--app-accent)]" />
      <p class="text-sm text-[var(--app-ink-soft)]">Aucun prospect trouvé.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ComputedRef } from 'vue'
import { computed } from 'vue'
import type { Prospect } from '~/types'

/**
 * Props for the ProspectTable component.
 */
interface Props {
  /** Array of prospects to display */
  prospects: Prospect[]
  /** Array of selected prospect IDs (as strings) */
  selectedProspects?: string[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  /** Row name clicked — open the detail drawer */
  viewProspect: [prospect: Prospect]
  /** Quick-delete icon clicked */
  deleteProspect: [prospect: Prospect]
  /** Row checkbox toggled */
  toggleSelect: [prospect: Prospect]
  /** Header checkbox toggled — select/clear all rows on the current page */
  toggleSelectAll: [checked: boolean]
}>()

/** Fast lookup set of the currently-selected prospect IDs. */
const selectedSet: ComputedRef<Set<string>> = computed((): Set<string> => new Set(props.selectedProspects ?? []))

/** Whether every visible prospect is selected. */
const allSelected: ComputedRef<boolean> = computed(
  (): boolean =>
    props.prospects.length > 0 && props.prospects.every((p: Prospect): boolean => selectedSet.value.has(String(p.id))),
)

/** Whether at least one visible prospect is selected. */
const someSelected: ComputedRef<boolean> = computed((): boolean =>
  props.prospects.some((p: Prospect): boolean => selectedSet.value.has(String(p.id))),
)

/**
 * Whether a given prospect is currently selected.
 * @param prospect - The prospect to test.
 * @returns True when the prospect's id is in the selection.
 */
function isSelected(prospect: Prospect): boolean {
  return selectedSet.value.has(String(prospect.id))
}

/**
 * Relay the header checkbox toggle to the parent.
 * @param event - The native change event.
 */
function onToggleAll(event: Event): void {
  emit('toggleSelectAll', (event.target as HTMLInputElement).checked)
}
</script>
