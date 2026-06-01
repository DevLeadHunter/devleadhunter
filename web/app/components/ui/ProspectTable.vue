<template>
  <div class="border-muted overflow-hidden rounded-lg border bg-[#1a1a1a]">
    <table class="w-full border-collapse">
      <thead>
        <tr class="bg-[#050505]">
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Nom</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Ville</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Téléphone</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Email</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Site web</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Source</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-center text-xs font-semibold">
            <span class="sr-only">Actions</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="prospect in prospects"
          :key="prospect.id"
          class="border-muted border-b transition-colors last:border-b-0 hover:bg-[#222222]"
        >
          <!-- Name — clickable to open detail drawer -->
          <td class="px-3 py-2.5">
            <button
              type="button"
              class="cursor-pointer text-left text-sm font-medium text-[#f9f9f9] underline decoration-[#30363d] underline-offset-2 transition-colors hover:text-[#58a6ff] hover:decoration-[#58a6ff]"
              @click="emit('viewProspect', prospect)"
            >
              {{ prospect.name }}
            </button>
          </td>

          <td class="text-muted px-3 py-2.5 text-sm">{{ prospect.city || '—' }}</td>

          <td class="text-muted px-3 py-2.5 text-sm">{{ prospect.phone || '—' }}</td>

          <td class="text-muted px-3 py-2.5 text-sm">
            <span v-if="prospect.email" class="text-[#f9f9f9]">{{ prospect.email }}</span>
            <span v-else class="text-[#30363d]">—</span>
          </td>

          <td class="px-3 py-2.5">
            <span
              v-if="prospect.website"
              class="inline-flex items-center rounded bg-[#2BAD5F]/20 px-2 py-0.5 text-xs font-medium text-[#3fb950]"
            >
              <i class="fa-solid fa-circle-check mr-1 text-[10px]"></i>
              Oui
            </span>
            <span
              v-else
              class="inline-flex items-center rounded bg-[#da3633]/20 px-2 py-0.5 text-xs font-medium text-[#DC4747]"
            >
              Non
            </span>
          </td>

          <td class="px-3 py-2.5">
            <UiProspectSourceBadge :source="prospect.source" />
          </td>

          <!-- Delete quick action -->
          <td class="px-3 py-2.5 text-center">
            <button
              type="button"
              class="inline-flex h-7 w-7 cursor-pointer items-center justify-center rounded bg-[#da3633]/20 text-[#DC4747] transition-colors hover:bg-[#da3633]/40"
              title="Supprimer ce prospect"
              @click="emit('deleteProspect', prospect)"
            >
              <i class="fa-regular fa-trash-can text-xs"></i>
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Empty State -->
    <div v-if="prospects.length === 0" class="py-12 text-center">
      <i class="fa-solid fa-magnifying-glass text-muted mb-3 text-4xl"></i>
      <p class="text-muted text-sm">Aucun prospect trouvé.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Prospect } from '~/types'

/**
 * Props for the ProspectTable component.
 */
interface Props {
  /** Array of prospects to display */
  prospects: Prospect[]
  /** Array of selected prospect IDs */
  selectedProspects?: string[]
}

defineProps<Props>()

const emit = defineEmits<{
  /** Row name clicked — open the detail drawer */
  viewProspect: [prospect: Prospect]
  /** Quick-delete icon clicked */
  deleteProspect: [prospect: Prospect]
}>()
</script>
