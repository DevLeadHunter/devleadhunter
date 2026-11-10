<template>
  <div class="max-w-3xl space-y-5">
    <UiPageHeader
      eyebrow="Compte"
      title="Facturation & paiement"
      description="Connectez le compte qui émettra vos factures et encaissera vos ventes. DevLeadHunter ne touche jamais l'argent : tout passe par votre propre compte."
    />

    <PaymentProviderConfig />

    <section>
      <div class="app-card p-5">
        <div class="flex items-start gap-3">
          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon name="i-lucide-tag" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>
          <div>
            <h2 class="text-sm font-semibold text-[var(--app-ink)]">Prix de vente d'un site</h2>
            <p class="mt-0.5 text-xs text-[var(--app-ink-soft)]">
              Le tarif appliqué par défaut à une nouvelle vente, et affiché dans vos relances via la variable
              <code class="rounded bg-[var(--app-surface-2)] px-1 py-0.5 text-[0.7rem]">{prix}</code>.
            </p>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap items-end gap-3 border-t border-[var(--app-line-soft)] pt-4">
          <label class="min-w-[12rem] flex-1">
            <span class="mb-1 block text-xs font-medium text-[var(--app-ink-soft)]">Montant (€)</span>
            <input
              v-model.number="priceEuros"
              type="number"
              min="0"
              step="10"
              class="app-input w-full"
              @keydown.enter="savePrice"
            />
          </label>
          <button
            type="button"
            class="app-btn-primary h-9 px-4 text-xs"
            :disabled="!canSave || isSaving"
            @click="savePrice"
          >
            <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
            Enregistrer
          </button>
        </div>

        <p
          v-if="feedback"
          class="mt-2 text-xs"
          :class="feedbackIsError ? 'text-[var(--app-red)]' : 'text-[var(--app-accent)]'"
        >
          {{ feedback }}
        </p>
      </div>
    </section>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import { useUserStore } from '~/stores/user'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

const DEFAULT_SALE_PRICE_CENTS: number = 50000

const userStore: ReturnType<typeof useUserStore> = useUserStore()

const priceEuros: Ref<number> = ref(DEFAULT_SALE_PRICE_CENTS / 100)
const isSaving: Ref<boolean> = ref(false)
const feedback: Ref<string> = ref('')
const feedbackIsError: Ref<boolean> = ref(false)

/** True when the entered amount is a finite, non-negative number the user can persist. */
const canSave: ComputedRef<boolean> = computed(
  (): boolean => Number.isFinite(priceEuros.value) && priceEuros.value >= 0,
)

/**
 * Persist the sale price (converted to cents) on the user's profile.
 */
async function savePrice(): Promise<void> {
  if (!canSave.value || isSaving.value) return
  isSaving.value = true
  feedback.value = ''
  try {
    await userStore.updateProfile({ site_sale_price_cents: Math.round(priceEuros.value * 100) })
    feedbackIsError.value = false
    feedback.value = 'Prix de vente enregistré.'
  } catch (err) {
    feedbackIsError.value = true
    feedback.value = err instanceof Error ? err.message : "L'enregistrement a échoué."
  } finally {
    isSaving.value = false
  }
}

onMounted((): void => {
  const cents: number = userStore.user?.site_sale_price_cents ?? DEFAULT_SALE_PRICE_CENTS
  priceEuros.value = cents / 100
})
</script>
