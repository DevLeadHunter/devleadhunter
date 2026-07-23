<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-[var(--app-ink)]">Acheter des crédits</h1>
    </div>

    <div v-if="showSuccess" class="card mb-6 border border-[var(--app-green)]/30 bg-[var(--app-green)]/10">
      <div class="flex items-center gap-2 text-[var(--app-green)]">
        <UIcon name="i-lucide-circle-check" class="h-4 w-4" />
        <p>Paiement réussi ! Vos crédits ont été ajoutés à votre compte.</p>
      </div>
    </div>

    <div v-if="showCancel" class="card mb-6 border border-[var(--app-red)]/30 bg-[var(--app-red)]/10">
      <div class="flex items-center gap-2 text-[var(--app-red)]">
        <UIcon name="i-lucide-circle-x" class="h-4 w-4" />
        <p>Paiement annulé. Aucun débit n'a été effectué.</p>
      </div>
    </div>

    <div v-if="!isLoading && creditSettings" class="card">
      <form @submit.prevent="handlePurchase">
        <div class="mb-6">
          <label for="credits" class="mb-2 block text-sm font-medium text-[var(--app-ink)]"> Nombre de crédits </label>
          <input
            id="credits"
            v-model.number="credits"
            type="number"
            :min="creditSettings?.minimum_credits_purchase || 1"
            step="1"
            required
            placeholder="Saisissez un nombre de crédits"
            class="input-field"
          />
          <p
            v-if="credits < (creditSettings?.minimum_credits_purchase || 1)"
            class="mt-1.5 text-xs text-[var(--app-red)]"
          >
            ⚠️ Minimum requis: {{ creditSettings?.minimum_credits_purchase || 1 }} crédit{{
              creditSettings?.minimum_credits_purchase !== 1 ? 's' : ''
            }}
          </p>
          <p v-else class="mt-1.5 text-xs text-[var(--app-ink-soft)]">
            Minimum: {{ creditSettings?.minimum_credits_purchase || 1 }} crédit{{
              creditSettings?.minimum_credits_purchase !== 1 ? 's' : ''
            }}
          </p>
        </div>

        <div
          v-if="credits > 0 && creditSettings"
          class="mb-6 rounded border border-[var(--app-line)] bg-[var(--app-bg)] p-4"
        >
          <div class="mb-2 flex items-center justify-between">
            <span class="text-sm text-[var(--app-ink-soft)]">Crédits :</span>
            <span class="text-sm font-medium text-[var(--app-ink)]">{{ credits }}</span>
          </div>
          <div class="mb-2 flex items-center justify-between">
            <span class="text-sm text-[var(--app-ink-soft)]">Prix par crédit :</span>
            <span class="text-sm font-medium text-[var(--app-ink)]"
              >{{ creditSettings.price_per_credit.toFixed(2) }} €</span
            >
          </div>
          <div class="flex items-center justify-between border-t border-[var(--app-line)] pt-2">
            <span class="text-base font-semibold text-[var(--app-ink)]">Total :</span>
            <span class="text-lg font-bold text-[var(--app-ink)]">{{ totalPrice.toFixed(2) }} €</span>
          </div>
        </div>

        <div v-if="currentBalance !== null" class="mb-6 rounded border border-[var(--app-line)] bg-[var(--app-bg)] p-4">
          <div class="flex items-center justify-between">
            <span class="text-sm text-[var(--app-ink-soft)]">Crédits disponibles actuellement :</span>
            <span class="text-sm font-medium text-[var(--app-ink)]">
              {{ currentBalance === -1 ? 'Illimités' : currentBalance }}
            </span>
          </div>
        </div>

        <div class="flex justify-end border-t border-[var(--app-line)] pt-4">
          <button
            type="submit"
            class="btn-primary cursor-pointer"
            :disabled="isProcessing || !creditSettings || credits < creditSettings.minimum_credits_purchase"
          >
            <span v-if="isProcessing">Redirection…</span>
            <span v-else>Procéder au paiement</span>
          </button>
        </div>
      </form>
    </div>

    <div v-if="isLoading" class="card">
      <div class="animate-pulse space-y-4">
        <div class="h-4 w-3/4 rounded bg-[var(--app-surface-2)]"></div>
        <div class="h-10 w-full rounded bg-[var(--app-surface-2)]"></div>
        <div class="h-4 w-5/6 rounded bg-[var(--app-surface-2)]"></div>
      </div>
    </div>

    <div v-if="error && !isLoading" class="card mt-6 border border-[var(--app-red)]/30 bg-[var(--app-red)]/10">
      <div class="flex items-center gap-2 text-[var(--app-red)]">
        <UIcon name="i-lucide-triangle-alert" class="h-4 w-4" />
        <p>{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { CreditSettings } from '~/types'
import type { ComputedRef, Ref } from 'vue'
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CreditSettingsService } from '~/services/creditSettingsService'
import { PaymentService } from '~/services/paymentService'
import { useUserStore } from '~/stores/user'
import { useToast } from '~/composables/useToast'

/**
 * Dashboard buy credits page
 */
definePageMeta({
  layout: 'dashboard',
  middleware: ['auth', 'admin'],
})

/**
 * Route and router
 */
const route = useRoute()
const router = useRouter()

/**
 * Credit settings state
 */
const creditSettings: Ref<CreditSettings | null> = ref(null)
const isLoading: Ref<boolean> = ref(false)
const isProcessing: Ref<boolean> = ref(false)
const error: Ref<string | null> = ref(null)

/**
 * Form state
 */
const credits: Ref<number> = ref(100)

/**
 * User store
 */
const userStore = useUserStore()

/**
 * Toast composable
 */
const toast = useToast()

/**
 * Success/Cancel flags from URL params
 */
const showSuccess: Ref<boolean> = ref(false)
const showCancel: Ref<boolean> = ref(false)

/**
 * Current user balance
 */
const currentBalance: Ref<number | null> = ref(null)

/**
 * Calculate total price
 */
const totalPrice: ComputedRef<number> = computed((): number => {
  if (!creditSettings.value || credits.value <= 0) {
    return 0
  }
  return credits.value * creditSettings.value.price_per_credit
})

/**
 * Load credit settings from API
 * @returns {Promise<void>}
 */
const loadCreditSettings = async (): Promise<void> => {
  try {
    isLoading.value = true
    error.value = null
    creditSettings.value = await CreditSettingsService.getCreditSettings()
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Erreur lors du chargement des paramètres de crédits'
    error.value = errorMessage
    toast.error(errorMessage)
  } finally {
    isLoading.value = false
  }
}

/**
 * Load current user balance
 * @returns {Promise<void>}
 */
const loadUserBalance = async (): Promise<void> => {
  try {
    if (userStore.user) {
      // Get balance from user store or API
      currentBalance.value = userStore.user.credits_available ?? null
    }
  } catch (err) {
    console.error('Failed to load user balance:', err)
  }
}

/**
 * Handle purchase form submission
 * @returns {Promise<void>}
 */
const handlePurchase = async (): Promise<void> => {
  if (!creditSettings.value || credits.value <= 0) {
    return
  }

  // Validate minimum purchase amount
  const minimum = creditSettings.value.minimum_credits_purchase
  if (credits.value < minimum) {
    toast.error(`Le minimum d'achat est de ${minimum} crédit${minimum !== 1 ? 's' : ''}.`)
    return
  }

  try {
    isProcessing.value = true
    error.value = null

    // Create checkout session
    const session = await PaymentService.createCheckoutSession({
      credits: credits.value,
    })

    // Store session ID in sessionStorage for verification after redirect
    if (session.session_id && import.meta.client) {
      sessionStorage.setItem('stripe_session_id', session.session_id)
    }

    // Redirect to Stripe Checkout
    if (session.url) {
      window.location.href = session.url
    } else {
      throw new Error('No checkout URL returned from server')
    }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Erreur lors de la création de la session de paiement'
    error.value = errorMessage
    toast.error(errorMessage)
    isProcessing.value = false
  }
}

/**
 * Check URL params for success/cancel
 * @returns {Promise<void>}
 */
const checkUrlParams = async (): Promise<void> => {
  if (route.query.success === 'true') {
    showSuccess.value = true

    // Get stored session ID from sessionStorage
    let sessionId: string | null = null
    if (import.meta.client) {
      sessionId = sessionStorage.getItem('stripe_session_id')
      if (sessionId) {
        sessionStorage.removeItem('stripe_session_id')
      }
    }

    // If we have a session ID, verify the payment and ensure credits are added
    if (sessionId) {
      try {
        const verification = await PaymentService.verifyCheckoutSession(sessionId)
        if (verification.paid && verification.status === 'success') {
          toast.success(
            `Paiement confirmé ! ${verification.credits_added || credits.value} crédit${(verification.credits_added || credits.value) !== 1 ? 's' : ''} ajouté${(verification.credits_added || credits.value) !== 1 ? 's' : ''}.`,
          )
        }
      } catch (err) {
        console.error('Failed to verify checkout session:', err)
        // Continue anyway - webhook might have processed it
      }
    }

    // Refresh user data from API to get updated credits
    try {
      await userStore.refreshUser()
    } catch (err) {
      console.error('Failed to refresh user data after payment:', err)
    }
    // Reload user balance after successful payment
    loadUserBalance()
    // Clear query params
    router.replace({ query: {} })
  }
  if (route.query.canceled === 'true') {
    showCancel.value = true
    // Clear stored session ID if payment was cancelled
    if (import.meta.client) {
      sessionStorage.removeItem('stripe_session_id')
    }
    // Clear query params
    router.replace({ query: {} })
  }
}

/**
 * Initialize component
 */
onMounted(async () => {
  await loadCreditSettings()
  await loadUserBalance()
  await checkUrlParams()
})
</script>
