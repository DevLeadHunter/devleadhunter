<template>
  <div class="overflow-hidden border border-muted rounded-lg bg-[#1a1a1a]">
    <table class="w-full border-collapse">
      <thead>
        <tr class="bg-[#050505]">
          <th class="px-3 py-2.5 text-left text-xs font-semibold text-muted border-b border-muted">
            Name
          </th>
          <th class="px-3 py-2.5 text-left text-xs font-semibold text-muted border-b border-muted">
            Address
          </th>
          <th class="px-3 py-2.5 text-left text-xs font-semibold text-muted border-b border-muted">
            City
          </th>
          <th class="px-3 py-2.5 text-left text-xs font-semibold text-muted border-b border-muted">
            Phone
          </th>
          <th class="px-3 py-2.5 text-left text-xs font-semibold text-muted border-b border-muted">
            Email
          </th>
          <th class="px-3 py-2.5 text-left text-xs font-semibold text-muted border-b border-muted">
            Website
          </th>
          <th class="px-3 py-2.5 text-left text-xs font-semibold text-muted border-b border-muted">
            Source
          </th>
          <th class="px-3 py-2.5 text-left text-xs font-semibold text-muted border-b border-muted">
            Actions
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="prospect in prospects"
          :key="prospect.id"
          class="hover:bg-[#2a2a2a] border-b border-muted last:border-b-0 transition-colors"
        >
          <td class="px-3 py-2.5 text-sm text-[#f9f9f9]">
            {{ prospect.name }}
          </td>
          <td class="px-3 py-2.5 text-sm text-muted">
            {{ prospect.address }}
          </td>
          <td class="px-3 py-2.5 text-sm text-[#f9f9f9]">
            {{ prospect.city }}
          </td>
          <td class="px-3 py-2.5 text-sm text-muted">
            {{ prospect.phone }}
          </td>
          <td class="px-3 py-2.5 text-sm text-muted">
            {{ prospect.email || '-' }}
          </td>
          <td class="px-3 py-2.5">
            <span
              v-if="prospect.website && prospect.website !== ''"
              class="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-[#2BAD5F]/20 text-[#3fb950]"
            >
              Has Website
            </span>
            <span
              v-else
              class="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-[#da3633]/20 text-[#DC4747]"
            >
              No Website
            </span>
          </td>
          <td class="px-3 py-2.5 text-xs text-muted">
            {{ formatSource(prospect.source) }}
          </td>
          <td class="px-3 py-2.5">
            <div class="flex gap-1.5">
              <button
                @click="handleAddToCampaign(prospect.id)"
                class="btn-secondary"
              >
                <i class="fa-solid fa-plus mr-1"></i> Add to Campaign
              </button>
              <button
                v-if="prospect.email"
                @click="handleSendEmail(prospect)"
                class="btn-secondary"
              >
                <i class="fa-solid fa-envelope mr-1"></i> Send Email
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Empty State -->
    <div v-if="prospects.length === 0" class="text-center py-12">
      <i class="fa-solid fa-magnifying-glass text-4xl text-muted mb-3"></i>
      <p class="text-muted text-sm">No prospects found. Start a search to find prospects.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Prospect } from '~/types';
import { useToast } from '~/composables/useToast';

/**
 * Props for the ProspectTable component
 */
interface Props {
  /**
   * Array of prospects to display
   */
  prospects: Prospect[];
  /**
   * Array of selected prospect IDs
   */
  selectedProspects?: string[];
}

/**
 * Props definition
 */
const props = defineProps<Props>();

/**
 * Emit events
 */
const emit = defineEmits<{
  toggleProspect: [id: number];
  viewProspect: [prospect: Prospect];
  deleteProspect: [prospect: Prospect];
}>();

/**
 * Toast composable
 */
const toast = useToast();

/**
 * Format source name for display
 * @param {string} source - Source name
 * @returns {string} Formatted source name
 */
const formatSource = (source: string): string => {
  const sourceMap: Record<string, string> = {
    'google': 'Google',
    'pagesjaunes': 'Pages Jaunes',
    'yelp': 'Yelp',
    'osm': 'OSM',
    'mappy': 'Mappy',
    'mock': 'Mock'
  };
  
  return sourceMap[source] || source;
};

/**
 * Handle add to campaign click
 * @param {number} prospectId - Prospect ID
 * @returns {void}
 */
const handleAddToCampaign = (prospectId: number): void => {
  navigateTo(`/dashboard/campaigns?addProspect=${prospectId}`);
  toast.info('Navigate to campaigns to add this prospect');
};

/**
 * Handle send email click
 * @param {Prospect} prospect - Prospect object
 * @returns {void}
 */
const handleSendEmail = (prospect: Prospect): void => {
  // This would open a modal or navigate to email page
  toast.info('Email functionality would open here');
};

/**
 * Handle view prospect
 * @param {Prospect} prospect - Prospect object
 * @returns {void}
 */
const handleViewProspect = (prospect: Prospect): void => {
  emit('viewProspect', prospect);
};

/**
 * Handle delete prospect
 * @param {Prospect} prospect - Prospect object
 * @returns {void}
 */
const handleDeleteProspect = (prospect: Prospect): void => {
  emit('deleteProspect', prospect);
};
</script>
