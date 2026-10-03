<template>
  <div>
    <input
      :id="inputId"
      :value="displayValue"
      type="text"
      inputmode="numeric"
      autocomplete="off"
      :placeholder="placeholder"
      :disabled="disabled"
      class="input-field"
      :class="inputStateClass"
      @input="handleInput"
    />

    <p v-if="lookupStatus === 'loading'" class="mt-1 flex items-center gap-1.5 text-[11px] text-[var(--app-ink-soft)]">
      <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
      Recherche dans l'annuaire des entreprises…
    </p>
    <p v-else-if="verifiedCompanyName" class="mt-1 text-[11px] font-medium text-[var(--app-green)]">
      {{ verifiedCompanyName }}
    </p>
    <p v-else-if="errorMessage" class="mt-1 text-[11px] text-[var(--app-red)]">
      {{ errorMessage }}
    </p>
    <p v-else class="mt-1 text-[11px] text-[var(--app-ink-soft)]">
      Saisissez un SIREN (9 chiffres) ou un SIRET (14 chiffres) pour préremplir la fiche.
    </p>
  </div>
</template>

<script lang="ts" setup>
import type { UiTaxIdLookupInputEmits } from '~/types/UiTaxIdLookupInput'
import type { CompanyBillingPrefill, TaxIdLookupInputProps, TaxIdLookupStatus } from '~/types/CompanyRegistryLookup'
import type { ComputedRef, EmitFn, Ref } from 'vue'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { lookupCompanyBilling } from '~/services/companyRegistryLookupService'
import {
  formatTaxIdForDisplay,
  hasValidTaxIdChecksum,
  isCompleteTaxId,
  isIncompleteTaxId,
  normalizeTaxIdDigits,
} from '~/utils/taxIdUtils'

const LOOKUP_DEBOUNCE_MS: number = 500
const SIRET_DIGIT_COUNT: number = 14

/** Optional SIREN/SIRET field with registry lookup to prefill billing details. */
const props: TaxIdLookupInputProps = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
  inputId: {
    type: String,
    default: undefined,
  },
  placeholder: {
    type: String,
    default: '123 456 789 ou 123 456 789 00012',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiTaxIdLookupInputEmits> = defineEmits<UiTaxIdLookupInputEmits>()

const lookupStatus: Ref<TaxIdLookupStatus> = ref('idle')
const verifiedCompanyName: Ref<string | null> = ref(null)
const hasTypedLetters: Ref<boolean> = ref(false)

let lookupDebounceTimeout: ReturnType<typeof setTimeout> | null = null
let lookupAbortController: AbortController | null = null
let lookupRequestId: number = 0

const compactTaxId: ComputedRef<string> = computed((): string => normalizeTaxIdDigits(props.modelValue))

const displayValue: ComputedRef<string> = computed((): string => formatTaxIdForDisplay(compactTaxId.value))

const inputStateClass: ComputedRef<string | undefined> = computed((): string | undefined => {
  if (lookupStatus.value === 'verified') {
    return 'border-[var(--app-green)]'
  }
  if (errorMessage.value) {
    return 'border-[var(--app-red)]'
  }
  return undefined
})

const errorMessage: ComputedRef<string | undefined> = computed((): string | undefined => {
  if (compactTaxId.value.length === 0 || lookupStatus.value === 'loading' || lookupStatus.value === 'verified') {
    return undefined
  }

  if (hasTypedLetters.value) {
    return 'Un SIREN / SIRET ne contient que des chiffres : pour un client étranger, choisissez son pays.'
  }

  if (isIncompleteTaxId(compactTaxId.value)) {
    return 'SIREN (9 chiffres) ou SIRET (14 chiffres) incomplet.'
  }

  if (!isCompleteTaxId(compactTaxId.value)) {
    return undefined
  }

  if (!hasValidTaxIdChecksum(compactTaxId.value)) {
    return 'Numéro SIREN / SIRET invalide.'
  }

  if (lookupStatus.value === 'not-found') {
    return 'Aucune entreprise trouvée pour ce numéro.'
  }

  if (lookupStatus.value === 'error') {
    return "Impossible de consulter l'annuaire pour le moment."
  }

  return undefined
})

/**
 * Propagate formatted typing to the parent model as compact digits.
 * @param event - Native input event.
 */
function handleInput(event: Event): void {
  if (props.disabled) {
    return
  }
  const rawValue: string = (event.target as HTMLInputElement).value
  hasTypedLetters.value = /\p{L}/u.test(rawValue)
  emit('update:modelValue', normalizeTaxIdDigits(rawValue).slice(0, SIRET_DIGIT_COUNT))
}

/**
 * Schedule a debounced registry lookup for the current tax id.
 * @param digits - Compact SIREN/SIRET typed by the user.
 */
function scheduleLookup(digits: string): void {
  clearLookupDebounce()
  abortLookupRequest()
  lookupRequestId += 1
  verifiedCompanyName.value = null

  if (digits.length === 0) {
    lookupStatus.value = 'idle'
    return
  }

  if (hasTypedLetters.value || !isCompleteTaxId(digits) || !hasValidTaxIdChecksum(digits)) {
    lookupStatus.value = 'idle'
    return
  }

  lookupStatus.value = 'loading'
  lookupDebounceTimeout = setTimeout((): void => {
    void runLookup(digits)
  }, LOOKUP_DEBOUNCE_MS)
}

/**
 * Query the public company registry and emit billing prefill data.
 * @param digits - Complete, checksum-valid SIREN or SIRET.
 */
async function runLookup(digits: string): Promise<void> {
  const requestId: number = lookupRequestId + 1
  lookupRequestId = requestId

  const abortController: AbortController = new AbortController()
  lookupAbortController = abortController

  try {
    const prefill: CompanyBillingPrefill | null = await lookupCompanyBilling(digits, abortController.signal)
    if (requestId !== lookupRequestId || compactTaxId.value !== digits) {
      return
    }

    if (!prefill) {
      lookupStatus.value = 'not-found'
      return
    }

    lookupStatus.value = 'verified'
    verifiedCompanyName.value = `Entreprise trouvée : ${prefill.name}`
    emit('prefill', prefill)
  } catch {
    if (requestId !== lookupRequestId || abortController.signal.aborted) {
      return
    }
    lookupStatus.value = 'error'
  }
}

/**
 * Cancel the debounced lookup timer.
 */
function clearLookupDebounce(): void {
  if (lookupDebounceTimeout !== null) {
    clearTimeout(lookupDebounceTimeout)
    lookupDebounceTimeout = null
  }
}

/**
 * Abort the in-flight registry request.
 */
function abortLookupRequest(): void {
  if (lookupAbortController !== null) {
    lookupAbortController.abort()
    lookupAbortController = null
  }
}

watch(compactTaxId, (digits: string): void => {
  scheduleLookup(digits)
})

onBeforeUnmount((): void => {
  clearLookupDebounce()
  abortLookupRequest()
})
</script>
