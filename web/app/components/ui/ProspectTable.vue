<template>
  <div class="border-muted overflow-hidden rounded-lg border bg-[#1a1a1a]">
    <table class="w-full border-collapse">
      <thead>
        <tr class="bg-[#050505]">
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Name</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Address</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">City</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Phone</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Email</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Website</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Source</th>
          <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="prospect in prospects"
          :key="prospect.id"
          class="border-muted border-b transition-colors last:border-b-0 hover:bg-[#2a2a2a]"
        >
          <td class="px-3 py-2.5 text-sm text-[#f9f9f9]">
            {{ prospect.name }}
          </td>
          <td class="text-muted px-3 py-2.5 text-sm">
            {{ prospect.address }}
          </td>
          <td class="px-3 py-2.5 text-sm text-[#f9f9f9]">
            {{ prospect.city }}
          </td>
          <td class="text-muted px-3 py-2.5 text-sm">
            {{ prospect.phone }}
          </td>
          <td class="text-muted px-3 py-2.5 text-sm">
            {{ prospect.email || '-' }}
          </td>
          <td class="px-3 py-2.5">
            <span
              v-if="prospect.website && prospect.website !== ''"
              class="inline-flex items-center rounded bg-[#2BAD5F]/20 px-2.5 py-0.5 text-xs font-medium text-[#3fb950]"
            >
              Has Website
            </span>
            <span
              v-else
              class="inline-flex items-center rounded bg-[#da3633]/20 px-2.5 py-0.5 text-xs font-medium text-[#DC4747]"
            >
              No Website
            </span>
          </td>
          <td class="text-muted px-3 py-2.5 text-xs">
            {{ formatSource(prospect.source) }}
          </td>
          <td class="px-3 py-2.5">
            <div class="flex gap-1.5">
              <button class="btn-secondary" @click="handleAddToCampaign(prospect.id)">
                <i class="fa-solid fa-plus mr-1"></i> Add to Campaign
              </button>
              <button v-if="prospect.email" class="btn-secondary" @click="handleSendEmail(prospect)">
                <i class="fa-solid fa-envelope mr-1"></i> Send Email
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Empty State -->
    <div v-if="prospects.length === 0" class="py-12 text-center">
      <i class="fa-solid fa-magnifying-glass text-muted mb-3 text-4xl"></i>
      <p class="text-muted text-sm">No prospects found. Start a search to find prospects.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Prospect } from '~/types'
import { useToast } from '~/composables/useToast'

/**
 * Props for the ProspectTable component
 */
interface Props {
  /**
   * Array of prospects to display
   */
  prospects: Prospect[]
  /**
   * Array of selected prospect IDs
   */
  selectedProspects?: string[]
}

/**
 * Props definition
 */
defineProps<Props>()

/**
 * Emit events
 */
defineEmits<{
  toggleProspect: [id: number]
  viewProspect: [prospect: Prospect]
  deleteProspect: [prospect: Prospect]
}>()

/**
 * Toast composable
 */
const toast = useToast()

/**
 * Format source name for display
 * @param {string} source - Source name
 * @returns {string} Formatted source name
 */
const formatSource = (source: string): string => {
  const sourceMap: Record<string, string> = {
    google: 'Google',
    pagesjaunes: 'Pages Jaunes',
    yelp: 'Yelp',
    osm: 'OSM',
    mappy: 'Mappy',
    mock: 'Mock',
  }

  return sourceMap[source] || source
}

/**
 * Handle add to campaign click
 * @param {number} prospectId - Prospect ID
 * @returns {void}
 */
const handleAddToCampaign = (prospectId: number): void => {
  navigateTo(`/dashboard/campaigns?addProspect=${prospectId}`)
  toast.info('Navigate to campaigns to add this prospect')
}

/**
 * Handle send email click.
 */
const handleSendEmail = (_prospect: Prospect): void => {
  toast.info('Email functionality would open here')
}
</script>
