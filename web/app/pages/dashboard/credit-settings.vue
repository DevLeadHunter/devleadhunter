<template>
  <div>
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-[#f9f9f9]">Credit Settings</h1>
    </div>

    <!-- Credit Settings Form -->
    <div v-if="!isLoading && creditSettings" class="card">
      <form @submit.prevent="handleSubmit">
        <!-- Grid Layout: 2 columns on desktop, 1 on mobile -->
        <div class="mb-6 grid grid-cols-1 gap-6 md:grid-cols-2">
          <!-- Price per Credit -->
          <div>
            <label for="price-per-credit" class="mb-2 block text-sm font-medium text-[#f9f9f9]">
              Price per Credit (EUR)
            </label>
            <div class="relative">
              <span class="absolute top-1/2 left-3 -translate-y-1/2 text-[#8b949e]">€</span>
              <input
                id="price-per-credit"
                v-model.number="form.price_per_credit"
                type="number"
                step="0.01"
                min="0.01"
                required
                placeholder="0.10"
                class="input-field pl-8"
              />
            </div>
            <p class="mt-1.5 text-xs text-[#8b949e]">Unit price of one credit in euros</p>
          </div>

          <!-- Credits per Search -->
          <div>
            <label for="credits-per-search" class="mb-2 block text-sm font-medium text-[#f9f9f9]">
              Credits per Search
            </label>
            <input
              id="credits-per-search"
              v-model.number="form.credits_per_search"
              type="number"
              min="1"
              required
              placeholder="5"
              class="input-field"
            />
            <p class="mt-1.5 text-xs text-[#8b949e]">Number of credits required to launch a search (minimum)</p>
          </div>

          <!-- Credits per Result -->
          <div>
            <label for="credits-per-result" class="mb-2 block text-sm font-medium text-[#f9f9f9]">
              Credits per Result
            </label>
            <input
              id="credits-per-result"
              v-model.number="form.credits_per_result"
              type="number"
              min="1"
              required
              placeholder="1"
              class="input-field"
            />
            <p class="mt-1.5 text-xs text-[#8b949e]">Number of credits required per prospect found</p>
          </div>

          <!-- Credits per Email -->
          <div>
            <label for="credits-per-email" class="mb-2 block text-sm font-medium text-[#f9f9f9]">
              Credits per Email
            </label>
            <input
              id="credits-per-email"
              v-model.number="form.credits_per_email"
              type="number"
              min="1"
              required
              placeholder="3"
              class="input-field"
            />
            <p class="mt-1.5 text-xs text-[#8b949e]">Number of credits required to send an email</p>
          </div>

          <!-- Free Credits on Signup -->
          <div>
            <label for="free-credits" class="mb-2 block text-sm font-medium text-[#f9f9f9]">
              Free Credits on Signup
            </label>
            <input
              id="free-credits"
              v-model.number="form.free_credits_on_signup"
              type="number"
              min="0"
              required
              placeholder="15"
              class="input-field"
            />
            <p class="mt-1.5 text-xs text-[#8b949e]">Number of credits offered when a new user registers</p>
          </div>

          <!-- Minimum Credits Purchase -->
          <div>
            <label for="minimum-credits-purchase" class="mb-2 block text-sm font-medium text-[#f9f9f9]">
              Minimum Credits Purchase
            </label>
            <input
              id="minimum-credits-purchase"
              v-model.number="form.minimum_credits_purchase"
              type="number"
              min="1"
              required
              placeholder="10"
              class="input-field"
            />
            <p class="mt-1.5 text-xs text-[#8b949e]">Minimum number of credits that can be purchased</p>
          </div>
        </div>

        <!-- Form Actions -->
        <div class="flex flex-col gap-3 border-t border-[#30363d] pt-4 sm:flex-row sm:justify-end">
          <button type="button" class="btn-secondary flex-1 sm:flex-none" :disabled="isSaving" @click="resetForm">
            Reset
          </button>
          <button
            type="submit"
            class="btn-primary flex-1 cursor-pointer sm:flex-none"
            :disabled="isSaving || !hasChanges"
          >
            <span v-if="isSaving">Saving...</span>
            <span v-else>Save Changes</span>
          </button>
        </div>
      </form>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="card">
      <div class="animate-pulse space-y-4">
        <div class="h-4 w-3/4 rounded bg-[#2a2a2a]"></div>
        <div class="h-10 w-full rounded bg-[#2a2a2a]"></div>
        <div class="h-4 w-5/6 rounded bg-[#2a2a2a]"></div>
        <div class="h-10 w-full rounded bg-[#2a2a2a]"></div>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error && !isLoading" class="card mt-6 border border-[#da3633]/30 bg-[#da3633]/10">
      <div class="flex items-center gap-2 text-[#DC4747]">
        <i class="fa-solid fa-circle-exclamation"></i>
        <p>{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CreditSettings } from '~/types'
import type { Ref } from 'vue'
import { ref, computed, onMounted } from 'vue'
import * as creditSettingsService from '~/services/creditSettingsService'
import { useToast } from '~/composables/useToast'

/**
 * Dashboard credit settings page
 */
definePageMeta({
  layout: 'dashboard',
  middleware: ['auth', 'admin'],
})

/**
 * Credit settings state
 */
const creditSettings: Ref<CreditSettings | null> = ref(null)
const isLoading: Ref<boolean> = ref(false)
const isSaving: Ref<boolean> = ref(false)
const error: Ref<string | null> = ref(null)

/**
 * Form state
 */
const form: Ref<{
  price_per_credit: number
  credits_per_search: number
  credits_per_result: number
  credits_per_email: number
  free_credits_on_signup: number
  minimum_credits_purchase: number
}> = ref({
  price_per_credit: 0.1,
  credits_per_search: 5,
  credits_per_result: 1,
  credits_per_email: 3,
  free_credits_on_signup: 15,
  minimum_credits_purchase: 10,
})

/**
 * Original form values for comparison
 */
const originalForm: Ref<{
  price_per_credit: number
  credits_per_search: number
  credits_per_result: number
  credits_per_email: number
  free_credits_on_signup: number
  minimum_credits_purchase: number
}> = ref({
  price_per_credit: 0.1,
  credits_per_search: 5,
  credits_per_result: 1,
  credits_per_email: 3,
  free_credits_on_signup: 15,
  minimum_credits_purchase: 10,
})

/**
 * Toast composable
 */
const toast = useToast()

/**
 * Check if form has changes
 */
const hasChanges = computed((): boolean => {
  return (
    form.value.price_per_credit !== originalForm.value.price_per_credit ||
    form.value.credits_per_search !== originalForm.value.credits_per_search ||
    form.value.credits_per_result !== originalForm.value.credits_per_result ||
    form.value.credits_per_email !== originalForm.value.credits_per_email ||
    form.value.free_credits_on_signup !== originalForm.value.free_credits_on_signup ||
    form.value.minimum_credits_purchase !== originalForm.value.minimum_credits_purchase
  )
})

/**
 * Load credit settings from API
 * @returns {Promise<void>}
 */
const loadCreditSettings = async (): Promise<void> => {
  try {
    isLoading.value = true
    error.value = null
    creditSettings.value = await creditSettingsService.getCreditSettings()

    // Update form with loaded values
    form.value = {
      price_per_credit: creditSettings.value.price_per_credit,
      credits_per_search: creditSettings.value.credits_per_search,
      credits_per_result: creditSettings.value.credits_per_result,
      credits_per_email: creditSettings.value.credits_per_email,
      free_credits_on_signup: creditSettings.value.free_credits_on_signup,
      minimum_credits_purchase: creditSettings.value.minimum_credits_purchase,
    }

    // Update original form for comparison
    originalForm.value = { ...form.value }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Failed to load credit settings'
    error.value = errorMessage
    toast.error(errorMessage)
  } finally {
    isLoading.value = false
  }
}

/**
 * Reset form to original values
 * @returns {void}
 */
const resetForm = (): void => {
  if (originalForm.value) {
    form.value = { ...originalForm.value }
  }
}

/**
 * Handle form submission
 * @returns {Promise<void>}
 */
const handleSubmit = async (): Promise<void> => {
  if (!creditSettings.value) return

  try {
    isSaving.value = true
    error.value = null

    // Prepare update data (only changed fields)
    const updateData: Partial<CreditSettings> = {}
    if (form.value.price_per_credit !== originalForm.value.price_per_credit) {
      updateData.price_per_credit = form.value.price_per_credit
    }
    if (form.value.credits_per_search !== originalForm.value.credits_per_search) {
      updateData.credits_per_search = form.value.credits_per_search
    }
    if (form.value.credits_per_result !== originalForm.value.credits_per_result) {
      updateData.credits_per_result = form.value.credits_per_result
    }
    if (form.value.credits_per_email !== originalForm.value.credits_per_email) {
      updateData.credits_per_email = form.value.credits_per_email
    }
    if (form.value.free_credits_on_signup !== originalForm.value.free_credits_on_signup) {
      updateData.free_credits_on_signup = form.value.free_credits_on_signup
    }
    if (form.value.minimum_credits_purchase !== originalForm.value.minimum_credits_purchase) {
      updateData.minimum_credits_purchase = form.value.minimum_credits_purchase
    }

    // Update credit settings
    const updated = await creditSettingsService.updateCreditSettings(updateData)

    // Update local state
    creditSettings.value = updated
    form.value = {
      price_per_credit: updated.price_per_credit,
      credits_per_search: updated.credits_per_search,
      credits_per_result: updated.credits_per_result,
      credits_per_email: updated.credits_per_email,
      free_credits_on_signup: updated.free_credits_on_signup,
      minimum_credits_purchase: updated.minimum_credits_purchase,
    }
    originalForm.value = { ...form.value }

    toast.success('Credit settings updated successfully')
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Failed to update credit settings'
    error.value = errorMessage
    toast.error(errorMessage)
  } finally {
    isSaving.value = false
  }
}

/**
 * Initialize component
 */
onMounted(() => {
  loadCreditSettings()
})
</script>
