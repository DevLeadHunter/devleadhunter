<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open && order"
        class="fixed top-0 right-0 z-50 flex h-[calc(100dvh-var(--app-drawer-bottom))] w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[var(--app-drawer-bottom-padding)] shadow-2xl"
      >
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>
          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon name="i-lucide-file-text" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>
          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Finaliser la vente</h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              {{ order.business_name || order.customer_email || `Commande #${order.id}` }}
            </p>
          </div>
          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto">
          <div v-if="isLoading" class="flex items-center justify-center py-16">
            <UIcon name="i-lucide-loader-circle" class="h-7 w-7 animate-spin text-[var(--app-accent)]" />
          </div>

          <template v-else-if="step === 'billing'">
            <div
              v-if="isInvoiceIssued"
              class="mx-5 mt-4 rounded-lg border border-[var(--app-green)]/40 bg-[var(--app-green)]/10 p-3"
            >
              <p class="text-xs font-medium text-[var(--app-ink)]">
                Facture {{ order.invoice_number || 'émise' }} déjà émise
              </p>
              <p class="mt-0.5 text-[11px] text-[var(--app-ink-soft)]">
                Une facture finalisée consomme un numéro : elle est réutilisée, jamais réémise.
              </p>
            </div>

            <div
              v-else-if="!hasConnectedProvider"
              class="mx-5 mt-4 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)] p-3"
            >
              <p class="text-xs font-medium text-[var(--app-ink)]">Aucun compte d'encaissement connecté</p>
              <p class="mt-0.5 text-[11px] text-[var(--app-ink-soft)]">
                La vente reste possible (virement, espèces) mais aucune facture ne sera émise. Connectez Qonto ou Stripe
                dans
                <NuxtLink
                  to="/dashboard/settings/billing"
                  class="font-medium text-[var(--app-blue)] underline underline-offset-2 transition-opacity hover:opacity-80"
                  @click="emit('close')"
                  >Facturation &amp; paiement</NuxtLink
                >.
              </p>
            </div>

            <form id="finalize-sale-form" class="space-y-4 p-5" @submit.prevent="handleIssueInvoice">
              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Pays de facturation
                </label>
                <select v-model="form.country_code" class="input-field" :disabled="isInvoiceIssued">
                  <option v-if="countryProfiles.length === 0" :value="form.country_code">
                    {{ ProspectCountries.option(form.country_code).flag }}
                    {{ ProspectCountries.option(form.country_code).label }}
                  </option>
                  <option
                    v-for="countryProfile in countryProfiles"
                    :key="countryProfile.code"
                    :value="countryProfile.code"
                  >
                    {{ ProspectCountries.option(countryProfile.code).flag }} {{ countryProfile.label }}
                  </option>
                </select>
              </div>

              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  {{ taxIdFieldLabel }}
                </label>
                <UiTaxIdLookupInput
                  v-if="isFranceSelected"
                  v-model="form.tax_id"
                  :disabled="isInvoiceIssued"
                  @prefill="applyRegistryPrefill"
                />
                <input
                  v-else
                  v-model="form.tax_id"
                  type="text"
                  class="input-field"
                  :placeholder="selectedCountryProfile?.tax_id_example ?? ''"
                  :disabled="isInvoiceIssued"
                />
                <p v-if="isTaxIdRequired" class="mt-1 text-[11px] text-[var(--app-ink-soft)]">
                  Exigé par Qonto pour émettre la facture.
                </p>
              </div>

              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                  >Montant (€)</label
                >
                <input
                  v-model.number="form.amount_euros"
                  type="number"
                  min="0"
                  step="1"
                  class="input-field"
                  placeholder="500"
                  :disabled="isInvoiceIssued"
                />
              </div>

              <p
                class="border-t border-[var(--app-surface-2)] pt-4 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase"
              >
                Coordonnées de facturation
              </p>

              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                  >Raison sociale</label
                >
                <input
                  v-model="form.name"
                  type="text"
                  class="input-field"
                  placeholder="Plomberie Martin"
                  :disabled="isInvoiceIssued"
                />
              </div>
              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                  >Email du client</label
                >
                <input
                  v-model="form.email"
                  type="email"
                  class="input-field"
                  placeholder="contact@plomberie-martin.fr"
                  :disabled="isInvoiceIssued"
                />
              </div>
              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                  >Adresse</label
                >
                <UiAddressAutocompleteInput
                  v-if="isFranceSelected"
                  v-model="form.address"
                  placeholder="12 rue de la Paix"
                  :disabled="isInvoiceIssued"
                  @select="handleAddressSelect"
                />
                <input
                  v-else
                  v-model="form.address"
                  type="text"
                  class="input-field"
                  placeholder="Numéro et rue"
                  :disabled="isInvoiceIssued"
                />
              </div>
              <div class="grid grid-cols-3 gap-3">
                <div>
                  <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                    >Code postal</label
                  >
                  <UiPostalCodeAutocompleteInput
                    v-if="isFranceSelected"
                    v-model="form.zip_code"
                    placeholder="35000"
                    :disabled="isInvoiceIssued"
                    @select="handlePostalCodeSelect"
                  />
                  <input
                    v-else
                    v-model="form.zip_code"
                    type="text"
                    class="input-field"
                    :placeholder="selectedCountryProfile?.postal_code_example ?? ''"
                    :disabled="isInvoiceIssued"
                  />
                </div>
                <div class="col-span-2">
                  <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                    >Ville</label
                  >
                  <UiCityAutocompleteInput
                    v-if="isFranceSelected"
                    v-model="form.city"
                    placeholder="Rennes"
                    :disabled="isInvoiceIssued"
                  />
                  <input
                    v-else
                    v-model="form.city"
                    type="text"
                    class="input-field"
                    placeholder="Ville"
                    :disabled="isInvoiceIssued"
                  />
                </div>
              </div>
              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                  >N° de TVA (facultatif)</label
                >
                <input
                  v-model="form.vat_number"
                  type="text"
                  class="input-field"
                  placeholder="FR32123456789"
                  :disabled="isInvoiceIssued"
                />
              </div>

              <template v-if="isQuebecProspect">
                <p
                  class="border-t border-[var(--app-surface-2)] pt-4 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase"
                >
                  Licence RBQ
                </p>
                <div v-if="storedProfessionalLicense" class="flex items-center gap-3">
                  <div class="min-w-0 flex-1">
                    <p class="text-[10px] text-[var(--app-ink-soft)]">{{ storedProfessionalLicense.label }}</p>
                    <p class="truncate text-sm font-medium text-[var(--app-ink)]">
                      {{ storedProfessionalLicense.number }}
                    </p>
                  </div>
                  <span v-if="professionalLicenseOriginLabel" class="app-badge app-badge--success text-[10px]">
                    {{ professionalLicenseOriginLabel }}
                  </span>
                </div>
                <div v-else>
                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <label
                        class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                        >Libellé</label
                      >
                      <input
                        v-model="professionalLicenseDraft.label"
                        type="text"
                        maxlength="60"
                        class="input-field"
                        :disabled="isInvoiceIssued"
                      />
                    </div>
                    <div>
                      <label
                        class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                        >Numéro (facultatif)</label
                      >
                      <input
                        v-model="professionalLicenseDraft.number"
                        type="text"
                        maxlength="60"
                        class="input-field"
                        placeholder="5678-1234-01"
                        :disabled="isInvoiceIssued"
                      />
                    </div>
                  </div>
                  <p class="mt-1 text-[11px] text-[var(--app-ink-soft)]">
                    Obligatoire sur le site d'un entrepreneur en construction au Québec
                  </p>
                </div>
              </template>

              <p v-if="missingLabel" class="text-xs text-[var(--app-red)]">Renseignez {{ missingLabel }}.</p>
            </form>
          </template>

          <template v-else>
            <div class="space-y-3 px-5 py-4">
              <div v-if="order.invoice_number" class="flex items-center gap-3">
                <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--app-surface-2)]">
                  <UIcon name="i-lucide-receipt" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
                </span>
                <div class="min-w-0 flex-1">
                  <p class="text-[10px] text-[var(--app-ink-soft)]">Facture</p>
                  <p class="truncate text-sm font-medium text-[var(--app-ink)]">{{ order.invoice_number }}</p>
                </div>
              </div>
              <div v-if="paymentUrl" class="flex items-center gap-2">
                <input :value="paymentUrl" readonly class="input-field flex-1 truncate text-xs" />
                <button
                  type="button"
                  class="flex h-9 w-9 shrink-0 items-center justify-center rounded border border-[var(--app-line)] text-[var(--app-ink-soft)] hover:text-[var(--app-accent-ink)]"
                  title="Copier le lien de paiement"
                  @click="copyPaymentLink"
                >
                  <UIcon name="i-lucide-copy" class="h-4 w-4" />
                </button>
              </div>
              <p v-else class="text-xs text-[var(--app-ink-soft)]">
                Aucun lien de paiement — le client règle par virement depuis sa facture.
              </p>
            </div>

            <div v-if="emailPreview" class="border-t border-[var(--app-surface-2)] px-5 py-4">
              <p class="mb-2 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
                Aperçu de l'email
              </p>
              <p class="mb-2 text-xs text-[var(--app-ink-soft)]">
                <span class="font-medium text-[var(--app-ink)]">Objet :</span> {{ emailPreview.subject }}
              </p>
              <iframe
                :srcdoc="emailPreview.body_html"
                class="h-72 w-full rounded border border-[var(--app-line)] bg-white"
                sandbox=""
              ></iframe>
              <p class="mt-2 text-[11px] text-[var(--app-ink-soft)]">
                Envoyé à {{ order.customer_email }}<span v-if="order.invoice_id">, facture en pièce jointe</span>, avec
                vous en copie cachée.
              </p>
            </div>
          </template>
        </div>

        <div class="border-t border-[var(--app-line)] px-5 py-4">
          <div v-if="step === 'billing'" class="flex gap-2">
            <button type="button" class="btn-secondary flex-1" :disabled="isBusy" @click="emit('back')">Annuler</button>
            <button
              type="submit"
              form="finalize-sale-form"
              class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="isBusy || missingLabel !== ''"
            >
              <UIcon v-if="isBusy" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
              {{ issueButtonLabel }}
            </button>
          </div>

          <div v-else class="flex gap-2">
            <button type="button" class="btn-secondary flex-1" :disabled="isBusy" @click="step = 'billing'">
              Retour
            </button>
            <button
              type="button"
              class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="isBusy || !emailPreview"
              @click="handleSendEmail"
            >
              <UIcon v-if="isBusy" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
              <UIcon v-else name="i-lucide-send" class="h-4 w-4" />
              Envoyer au client
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type {
  FinalizeSaleForm,
  FinalizeSaleStep,
  ProfessionalLicenseDraft,
  ProfessionalLicenseState,
  StoredProfessionalLicense,
  UiFinalizeSaleDrawerEmits,
  UiFinalizeSaleDrawerProps,
} from '~/types/UiFinalizeSaleDrawer'
import type { AddressSuggestion } from '~/types/AddressAutocompleteInput'
import type { CompanyBillingPrefill } from '~/types/CompanyRegistryLookup'
import type { CountryProfile } from '~/types/CountryProfile'
import type { PostalCodeCitySuggestion } from '~/types/PostalCodeAutocompleteInput'
import type { Prospect } from '~/types'
import type { ProspectEnrichment } from '~/services/enrichmentService'
import type {
  Order,
  OrderBillingDetails,
  OrderBillingPrefill,
  OrderPaymentEmailPreview,
} from '~/services/ordersService'
import { CountriesService } from '~/services/countriesService'
import { EnrichmentService } from '~/services/enrichmentService'
import { OrdersService } from '~/services/ordersService'
import { ProspectsService } from '~/services/prospectsService'
import { useToast } from '~/composables/useToast'
import { ProspectCountries } from '~/utils/prospectCountries'
import { PROFESSIONAL_LICENSE_DEFAULT_LABEL, PROFESSIONAL_LICENSE_SOURCE_LABELS } from '~/constants/professionalLicense'

/** Sale finalization drawer: reviewed billing details → invoice → sale email. */
const props: UiFinalizeSaleDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  order: {
    type: Object as PropType<Order | null>,
    default: null,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiFinalizeSaleDrawerEmits> = defineEmits<UiFinalizeSaleDrawerEmits>()

const toast: UseToastReturn = useToast()

const step: Ref<FinalizeSaleStep> = ref('billing')
const isLoading: Ref<boolean> = ref(false)
const isBusy: Ref<boolean> = ref(false)
const invoicingProvider: Ref<string | null> = ref(null)
const emailPreview: Ref<OrderPaymentEmailPreview | null> = ref(null)
const countryProfiles: Ref<CountryProfile[]> = ref([])
const isQuebecProspect: Ref<boolean> = ref(false)
const storedProfessionalLicense: Ref<StoredProfessionalLicense | null> = ref(null)
const professionalLicenseDraft: Ref<ProfessionalLicenseDraft> = ref({
  label: PROFESSIONAL_LICENSE_DEFAULT_LABEL,
  number: '',
})

const form: Ref<FinalizeSaleForm> = ref({
  name: '',
  email: '',
  address: '',
  zip_code: '',
  city: '',
  country_code: ProspectCountries.france.code,
  tax_id: '',
  vat_number: '',
  amount_euros: 0,
})

/** Whether the invoice was already issued (its number is burned — never reissue). */
const isInvoiceIssued: ComputedRef<boolean> = computed((): boolean => Boolean(props.order?.invoice_id))

/** Payment page of the issued invoice, falling back to the legacy platform link. */
const paymentUrl: ComputedRef<string> = computed(
  (): string => props.order?.payment_url || props.order?.stripe_payment_url || '',
)

/** Whether a provider will issue the invoice (drives the required fields). */
const hasConnectedProvider: ComputedRef<boolean> = computed((): boolean => invoicingProvider.value !== null)

const selectedCountryProfile: ComputedRef<CountryProfile | null> = computed(
  (): CountryProfile | null =>
    countryProfiles.value.find((profile: CountryProfile): boolean => profile.code === form.value.country_code) ?? null,
)

/** France is the only country with a registry lookup (SIRENE) and address autocomplete (BAN). */
const isFranceSelected: ComputedRef<boolean> = computed(
  (): boolean => form.value.country_code === ProspectCountries.france.code,
)

/** Qonto rejects a French invoice whose client carries no TIN; abroad the identifier is optional. */
const isTaxIdRequired: ComputedRef<boolean> = computed(
  (): boolean => invoicingProvider.value === 'qonto' && (selectedCountryProfile.value?.tax_id_required ?? false),
)

const taxIdLabel: ComputedRef<string> = computed(
  (): string => selectedCountryProfile.value?.tax_id_label ?? 'Identifiant fiscal',
)

const taxIdFieldLabel: ComputedRef<string> = computed((): string =>
  isTaxIdRequired.value ? taxIdLabel.value : `${taxIdLabel.value} (facultatif)`,
)

/** Whether the typed postal code has the shape of the selected country (empty or unknown shape passes). */
const hasValidPostalCodeShape: ComputedRef<boolean> = computed((): boolean => {
  const pattern: string | undefined = selectedCountryProfile.value?.postal_code_pattern
  const zipCode: string = form.value.zip_code.trim()
  if (!pattern || !zipCode) return true
  return new RegExp(`^(?:${pattern})$`, 'i').test(zipCode)
})

/** Human list of the still-missing billing fields (empty when ready to issue). */
const missingLabel: ComputedRef<string> = computed((): string => {
  if (isInvoiceIssued.value) return ''
  const missing: string[] = []
  if (!form.value.name.trim()) missing.push('la raison sociale')
  if (!form.value.email.trim()) missing.push("l'email du client")
  if (hasConnectedProvider.value) {
    if (!form.value.address.trim()) missing.push("l'adresse")
    if (!form.value.zip_code.trim()) missing.push('le code postal')
    if (!form.value.city.trim()) missing.push('la ville')
  }
  if (!hasValidPostalCodeShape.value) missing.push(`un code postal au format ${selectedCountryProfile.value?.label}`)
  if (isTaxIdRequired.value && !form.value.tax_id.trim()) missing.push(`le ${taxIdLabel.value}`)
  if (form.value.amount_euros <= 0) missing.push('un montant')
  return missing.join(', ')
})

const professionalLicenseOriginLabel: ComputedRef<string> = computed(
  (): string => PROFESSIONAL_LICENSE_SOURCE_LABELS[storedProfessionalLicense.value?.source ?? ''] ?? '',
)

/** Label of the primary button, which skips issuing when an invoice already exists. */
const issueButtonLabel: ComputedRef<string> = computed((): string => {
  if (isInvoiceIssued.value) return "Aperçu de l'email"
  return hasConnectedProvider.value ? 'Émettre la facture' : 'Préparer la vente'
})

/**
 * Load the pre-filled billing details (country pre-set from the prospect), the country facts, the provider and the RBQ license.
 * @returns A promise resolved once the form is ready.
 */
async function load(): Promise<void> {
  if (!props.order) return
  isLoading.value = true
  try {
    const [billing, profiles, professionalLicenseState]: [
      OrderBillingPrefill,
      CountryProfile[],
      ProfessionalLicenseState,
    ] = await Promise.all([
      OrdersService.getOrderBilling(props.order.id),
      countryProfiles.value.length > 0 ? countryProfiles.value : CountriesService.list(),
      fetchProfessionalLicenseState(props.order.prospect_id),
    ])
    countryProfiles.value = profiles
    isQuebecProspect.value = professionalLicenseState.isQuebecProspect
    storedProfessionalLicense.value = professionalLicenseState.storedLicense
    professionalLicenseDraft.value = { label: PROFESSIONAL_LICENSE_DEFAULT_LABEL, number: '' }
    invoicingProvider.value = billing.invoicing_provider
    form.value = {
      name: billing.name ?? '',
      email: billing.email ?? '',
      address: billing.address ?? '',
      zip_code: billing.zip_code ?? '',
      city: billing.city ?? '',
      country_code: billing.country_code || ProspectCountries.france.code,
      tax_id: billing.tax_id ?? '',
      vat_number: billing.vat_number ?? '',
      amount_euros: Math.round((props.order.amount_cents ?? 0) / 100),
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de charger les coordonnées de facturation')
  } finally {
    isLoading.value = false
  }
}

/**
 * Read whether the sold prospect is in Québec, and the RBQ license its enrichment already holds.
 * @param prospectId - Prospect of the order, null for a sale without one.
 * @returns What the license block shows.
 */
async function fetchProfessionalLicenseState(prospectId: number | null): Promise<ProfessionalLicenseState> {
  if (prospectId === null) return { isQuebecProspect: false, storedLicense: null }

  const prospect: Prospect = await ProspectsService.getProspect(prospectId)
  if (prospect.country !== 'CA') return { isQuebecProspect: false, storedLicense: null }

  const enrichment: ProspectEnrichment | null = await EnrichmentService.getProspectEnrichment(prospectId)
  return { isQuebecProspect: true, storedLicense: toStoredProfessionalLicense(enrichment) }
}

/**
 * The license an enrichment holds, with its origin.
 * @param enrichment - The prospect's enrichment record, null when none exists yet.
 * @returns The stored license, or null when the enrichment has no number.
 */
function toStoredProfessionalLicense(enrichment: ProspectEnrichment | null): StoredProfessionalLicense | null {
  const number: string = enrichment?.professional_license_number?.trim() ?? ''
  if (!enrichment || !number) return null
  return {
    label: enrichment.professional_license_label?.trim() || PROFESSIONAL_LICENSE_DEFAULT_LABEL,
    number,
    source: enrichment.professional_license_source,
  }
}

/**
 * Store the RBQ license typed for a Québec prospect on its enrichment, before the invoice is issued.
 * @returns A promise resolved once the license is saved, or at once when no number was typed.
 */
async function saveProfessionalLicense(): Promise<void> {
  const prospectId: number | null = props.order?.prospect_id ?? null
  const number: string = professionalLicenseDraft.value.number.trim()
  if (prospectId === null || !isQuebecProspect.value || storedProfessionalLicense.value || !number) return

  const enrichment: ProspectEnrichment = await EnrichmentService.updateProspectEnrichment(prospectId, {
    professional_license_label: professionalLicenseDraft.value.label.trim() || PROFESSIONAL_LICENSE_DEFAULT_LABEL,
    professional_license_number: number,
  })
  storedProfessionalLicense.value = toStoredProfessionalLicense(enrichment)
}

/** Billing payload sent to the API. */
function buildBillingPayload(): OrderBillingDetails {
  return {
    name: form.value.name.trim() || null,
    email: form.value.email.trim() || null,
    address: form.value.address.trim() || null,
    city: form.value.city.trim() || null,
    zip_code: form.value.zip_code.trim() || null,
    country_code: form.value.country_code || ProspectCountries.france.code,
    tax_id: form.value.tax_id.trim() || null,
    vat_number: form.value.vat_number.trim() || null,
  }
}

/** Issue the invoice at the provider, then move on to the email review. */
async function handleIssueInvoice(): Promise<void> {
  if (!props.order) return
  isBusy.value = true
  try {
    await saveProfessionalLicense()
    const updated: Order = await OrdersService.finalizeOrder(
      props.order.id,
      buildBillingPayload(),
      Math.round(form.value.amount_euros * 100),
    )
    emit('updated', updated)
    if (updated.invoice_number) toast.success(`Facture ${updated.invoice_number} générée`)
    emailPreview.value = await OrdersService.previewOrderPaymentEmail(updated.id)
    step.value = 'email'
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Impossible d'émettre la facture")
  } finally {
    isBusy.value = false
  }
}

/** Send the sale email (invoice attached, user in BCC). */
async function handleSendEmail(): Promise<void> {
  if (!props.order) return
  isBusy.value = true
  try {
    const updated: Order = await OrdersService.sendOrderPaymentEmail(props.order.id)
    emit('updated', updated)
    toast.success('Email envoyé au client')
    emit('back')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'envoi")
  } finally {
    isBusy.value = false
  }
}

/** Copy the invoice payment page to the clipboard. */
async function copyPaymentLink(): Promise<void> {
  if (!paymentUrl.value) return
  await navigator.clipboard.writeText(paymentUrl.value)
  toast.success('Lien copié')
}

/**
 * Prefill billing fields from a registry lookup triggered by SIREN/SIRET.
 * @param prefill - Company data returned by recherche-entreprises.api.gouv.fr.
 */
function applyRegistryPrefill(prefill: CompanyBillingPrefill): void {
  form.value.name = prefill.name
  form.value.address = prefill.address
  form.value.zip_code = prefill.zip_code
  form.value.city = prefill.city
  form.value.tax_id = prefill.tax_id
  if (prefill.vat_number) {
    form.value.vat_number = prefill.vat_number
  }
}

/**
 * Prefill postal code and city when the user picks a BAN address suggestion.
 * @param suggestion - Selected street address.
 */
function handleAddressSelect(suggestion: AddressSuggestion): void {
  form.value.zip_code = suggestion.postcode
  form.value.city = suggestion.city
}

/**
 * Prefill the city when the user picks a commune for the typed postal code.
 * @param suggestion - Commune linked to the postal code.
 */
function handlePostalCodeSelect(suggestion: PostalCodeCitySuggestion): void {
  form.value.city = suggestion.nom
}

watch(
  (): [boolean, number | undefined] => [props.open, props.order?.id],
  ([open]: [boolean, number | undefined]): void => {
    if (!open) return
    step.value = 'billing'
    emailPreview.value = null
    void load()
  },
  { immediate: true },
)
</script>

<style scoped>
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
