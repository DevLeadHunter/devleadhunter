<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open && (order || isCreateMode)"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-2xl"
      >
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="$emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>
          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)]"
          >
            <UIcon name="i-lucide-shopping-cart" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </div>
          <div class="min-w-0 flex-1">
            <div v-if="!isCreateMode" class="mb-1 flex flex-wrap items-center gap-1.5">
              <span :class="['inline-flex items-center rounded px-2 py-0.5 text-[10px] font-medium', statusBadgeClass]">
                {{ statusLabel }}
              </span>
              <span
                class="inline-flex items-center rounded border border-[var(--app-line)] bg-[var(--app-surface)] px-2 py-0.5 text-[10px] font-medium text-[var(--app-ink-soft)]"
              >
                {{ productLabel }}
              </span>
            </div>
            <h2 class="truncate text-base leading-tight font-semibold text-[var(--app-ink)]">
              {{ drawerTitle }}
            </h2>
            <p v-if="isCreateMode" class="mt-0.5 text-[11px] text-[var(--app-ink-soft)]">
              La vente sera créée en brouillon à l'enregistrement.
            </p>
            <p v-else class="mt-0.5 text-sm font-semibold text-[var(--app-accent-ink)]">{{ amountLabel }}</p>
          </div>
          <div class="flex shrink-0 items-center gap-0.5">
            <button
              v-if="!showForm && order"
              class="flex h-7 w-7 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
              title="Modifier cette vente"
              aria-label="Modifier cette vente"
              @click="startEdit"
            >
              <UIcon name="i-lucide-square-pen" class="h-4 w-4" />
            </button>
            <button
              v-if="!showForm && order"
              class="flex h-7 w-7 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-red-soft)] hover:text-[var(--app-red)]"
              title="Supprimer cette vente"
              aria-label="Supprimer cette vente"
              @click="deleteConfirmModal?.open()"
            >
              <UIcon name="i-lucide-trash-2" class="h-4 w-4" />
            </button>
            <button
              class="flex h-7 w-7 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface)] hover:text-[var(--app-ink)]"
              aria-label="Fermer"
              @click="$emit('close')"
            >
              <UIcon name="i-lucide-x" class="h-4 w-4" />
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto">
          <template v-if="!showForm && order">
            <div class="space-y-3 px-5 py-4">
              <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Client</p>
              <div class="flex items-center gap-3">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--app-surface)]">
                  <UIcon name="i-lucide-mail" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-[10px] text-[var(--app-ink-soft)]">Email</p>
                  <p class="truncate text-sm font-medium text-[var(--app-ink)]">{{ order.customer_email || '—' }}</p>
                </div>
              </div>
              <div v-if="order.domain" class="flex items-center gap-3">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--app-surface)]">
                  <UIcon name="i-lucide-globe" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-[10px] text-[var(--app-ink-soft)]">Domaine</p>
                  <p class="truncate text-sm font-medium text-[var(--app-ink)]">{{ order.domain }}</p>
                </div>
              </div>
            </div>

            <div class="border-t border-[var(--app-surface-2)]"></div>

            <div class="space-y-2 px-5 py-4">
              <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Paiement</p>
              <p v-if="order.invoice_number" class="text-sm font-medium text-[var(--app-ink)]">
                Facture {{ order.invoice_number }}
              </p>
              <div v-if="paymentUrl" class="flex items-center gap-2">
                <input :value="paymentUrl" readonly class="input-field flex-1 truncate text-xs" />
                <button
                  class="flex h-9 w-9 shrink-0 items-center justify-center rounded border border-[var(--app-line)] text-[var(--app-ink-soft)] hover:text-[var(--app-accent-ink)]"
                  title="Copier"
                  @click="copyLink"
                >
                  <UIcon name="i-lucide-copy" class="h-4 w-4" />
                </button>
              </div>
              <p v-else class="text-sm text-[var(--app-faint)]">Aucune facture émise.</p>
              <p v-if="order.payment_link_sent_at" class="text-[10px] text-[var(--app-ink-soft)]">
                Email envoyé le {{ formatShortMonthDateTime(order.payment_link_sent_at) }}
              </p>
              <p v-if="order.paid_at" class="text-[10px] text-[var(--app-green)]">
                Payé le {{ formatShortMonthDateTime(order.paid_at) }}
              </p>
            </div>

            <div v-if="canGoLive" class="border-t border-[var(--app-surface-2)] px-5 py-4">
              <div class="mb-1 flex items-center justify-between">
                <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Mise en ligne du site
                </p>
                <button
                  v-if="order.prospect_id || order.business_name"
                  type="button"
                  class="flex items-center gap-1 text-[11px] font-medium text-[var(--app-accent-ink)] transition-colors hover:underline disabled:opacity-50"
                  :disabled="isSuggestingDomain"
                  @click="suggestDomain"
                >
                  <UIcon
                    :name="isSuggestingDomain ? 'i-lucide-loader-circle' : 'i-lucide-wand-sparkles'"
                    :class="['h-3 w-3', { 'animate-spin': isSuggestingDomain }]"
                  />
                  Suggérer
                </button>
              </div>
              <p class="mb-2 text-[11px] text-[var(--app-ink-soft)]">{{ goLiveHint }}</p>
              <input
                v-model="goLiveDomain"
                type="text"
                class="input-field"
                placeholder="sonentreprise.fr"
                autocapitalize="off"
                autocomplete="off"
              />
              <div v-if="goLiveDomain.trim()" class="mt-1 flex items-center gap-1.5 text-[11px]">
                <UIcon
                  v-if="isCheckingDomain"
                  name="i-lucide-loader-circle"
                  class="h-3 w-3 animate-spin text-[var(--app-faint)]"
                />
                <template v-else-if="domainStatus">
                  <span
                    :class="[
                      'h-1.5 w-1.5 shrink-0 rounded-full',
                      domainStatus.available === true
                        ? 'bg-[var(--app-green)]'
                        : domainStatus.available === false
                          ? 'bg-[var(--app-red)]'
                          : 'bg-[var(--app-faint)]',
                    ]"
                  />
                  <span
                    :class="
                      domainStatus.available === true
                        ? 'text-[var(--app-green)]'
                        : domainStatus.available === false
                          ? 'text-[var(--app-red)]'
                          : 'text-[var(--app-faint)]'
                    "
                  >
                    {{
                      domainStatus.available === true
                        ? 'disponible'
                        : domainStatus.available === false
                          ? 'déjà pris'
                          : 'disponibilité inconnue'
                    }}
                  </span>
                  <span v-if="domainStatus.price_eur" class="text-[var(--app-faint)]"
                    >· {{ domainStatus.price_eur }} € TTC/an</span
                  >
                </template>
              </div>
              <div v-if="domainCandidates.length" class="mt-1.5 flex flex-wrap gap-1.5">
                <button
                  v-for="candidate in domainCandidates"
                  :key="candidate.domain"
                  type="button"
                  :class="[
                    'inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] transition-colors',
                    goLiveDomain === candidate.domain
                      ? 'border-[var(--app-accent)] bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
                      : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:border-[var(--app-accent)]',
                  ]"
                  :title="
                    candidate.available === true
                      ? 'Disponible'
                      : candidate.available === false
                        ? 'Déjà pris'
                        : 'Disponibilité inconnue'
                  "
                  @click="goLiveDomain = candidate.domain"
                >
                  {{ candidate.domain }}
                  <span
                    :class="[
                      'h-1.5 w-1.5 shrink-0 rounded-full',
                      candidate.available === true
                        ? 'bg-[var(--app-green)]'
                        : candidate.available === false
                          ? 'bg-[var(--app-red)]'
                          : 'bg-[var(--app-faint)]',
                    ]"
                  />
                </button>
              </div>
              <button
                type="button"
                class="btn-primary mt-2 w-full"
                :disabled="isProvisioning || !goLiveDomain.trim() || domainStatus?.available === false"
                :title="
                  domainStatus?.available === false
                    ? 'Ce domaine est déjà pris'
                    : 'Achat réel (~6 €) puis mise en ligne du site du client'
                "
                @click="provisionDomain"
              >
                <UIcon
                  :name="isProvisioning ? 'i-lucide-loader-circle' : 'i-lucide-rocket'"
                  :class="['mr-1.5 h-4 w-4', { 'animate-spin': isProvisioning }]"
                />
                Acheter le domaine et mettre en ligne{{
                  domainStatus?.price_eur ? ` (${domainStatus.price_eur} € TTC)` : ''
                }}
              </button>
            </div>

            <div
              v-if="order.domain && (order.status === 'deploying' || order.status === 'delivered')"
              class="border-t border-[var(--app-surface-2)] px-5 py-4"
            >
              <p class="mb-2 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
                Mise en ligne du site
              </p>
              <div v-if="order.status === 'delivered'" class="flex items-center gap-2 text-sm">
                <span class="h-2 w-2 shrink-0 rounded-full bg-[var(--app-green)]" />
                <span class="text-[var(--app-ink)]"
                  >En ligne sur <span class="font-medium">{{ order.domain }}</span></span
                >
                <a
                  :href="`https://${order.domain}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="ml-auto text-[11px] font-medium text-[var(--app-accent-ink)] hover:underline"
                  >Ouvrir →</a
                >
              </div>
              <div v-else class="flex items-start gap-2 text-sm">
                <UIcon
                  name="i-lucide-loader-circle"
                  class="mt-0.5 h-3.5 w-3.5 shrink-0 animate-spin text-[var(--app-accent-ink)]"
                />
                <span class="text-[var(--app-ink-soft)]">
                  Domaine <span class="font-medium text-[var(--app-ink)]">{{ order.domain }}</span> acheté — mise en
                  ligne en cours (propagation DNS, quelques minutes). Suivi dans Paramètres → Monitoring.
                  <span v-if="ovhOrderStatusLabel" class="mt-1 block">
                    Commande OVH : <span class="font-medium text-[var(--app-ink)]">{{ ovhOrderStatusLabel }}</span>
                  </span>
                </span>
              </div>
            </div>

            <div v-if="order.delivery_warning" class="border-t border-[var(--app-surface-2)] px-5 py-4">
              <div
                class="flex items-start gap-2 rounded-lg border border-[var(--app-blue)]/30 bg-[var(--app-blue-soft)] px-3 py-2"
              >
                <UIcon name="i-lucide-info" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-blue)]" />
                <p class="text-[12px] text-[var(--app-ink)]">{{ order.delivery_warning }}</p>
              </div>
            </div>

            <div v-if="order.notes" class="border-t border-[var(--app-surface-2)] px-5 py-4">
              <p class="mb-1 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Notes</p>
              <p class="text-sm whitespace-pre-line text-[var(--app-ink)]">{{ order.notes }}</p>
            </div>
          </template>

          <form v-else id="order-edit-form" class="space-y-4 p-5" @submit.prevent="handleSave">
            <p
              v-if="isCreateMode"
              class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase"
            >
              Informations de la vente
            </p>
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                >Montant (€)</label
              >
              <input
                v-model.number="editForm.amount_euros"
                type="number"
                min="0"
                step="1"
                class="input-field"
                placeholder="500"
              />
            </div>
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                >Nom de l'entreprise</label
              >
              <input v-model="editForm.business_name" type="text" class="input-field" placeholder="Plomberie Martin" />
            </div>
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                >Email client</label
              >
              <input
                v-model="editForm.customer_email"
                type="email"
                class="input-field"
                placeholder="contact@plomberie-martin.fr"
              />
            </div>
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                >Statut</label
              >
              <UiSelectField v-model="editForm.status" :options="statusOptions" :disabled="isCreateMode" />
            </div>
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                >Notes</label
              >
              <textarea
                v-model="editForm.notes"
                rows="3"
                class="input-field"
                placeholder="Négociation, contexte de la vente, à relancer le…"
              ></textarea>
            </div>
          </form>
        </div>

        <div class="border-t border-[var(--app-line)] px-5 py-4">
          <div v-if="!showForm && order" class="space-y-2">
            <button v-if="!order.paid_at" class="btn-primary w-full" :disabled="isBusy" @click="$emit('finalize')">
              <UIcon name="i-lucide-file-text" class="h-4 w-4" />
              {{ order.invoice_id ? "Reprendre l'envoi au client" : 'Finaliser la vente' }}
            </button>
            <button
              v-if="order.payment_provider && !order.paid_at"
              class="btn-secondary w-full"
              :disabled="isBusy"
              @click="handleCheckPayment"
            >
              <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />Vérifier le paiement
            </button>
            <div class="flex gap-2">
              <button v-if="!order.paid_at" class="btn-secondary flex-1" :disabled="isBusy" @click="handleMarkPaid">
                <UIcon name="i-lucide-circle-check" class="h-4 w-4" />Marquer payé
              </button>
              <button class="btn-secondary flex-1" :disabled="isBusy" @click="handleDeploy">
                <UIcon name="i-lucide-rocket" class="h-4 w-4" />Mettre en ligne
              </button>
            </div>
            <button
              v-if="order.paid_at && order.status !== 'refunded'"
              class="btn-secondary w-full"
              :disabled="isBusy"
              @click="refundConfirmModal?.open()"
            >
              <UIcon name="i-lucide-rotate-ccw" class="h-4 w-4" />Rembourser le paiement
            </button>
          </div>

          <div v-else-if="showForm" class="flex gap-2">
            <button
              type="button"
              class="btn-secondary flex-1"
              :disabled="isBusy"
              @click="isCreateMode ? emit('close') : (editMode = false)"
            >
              Annuler
            </button>
            <button type="submit" form="order-edit-form" class="btn-primary flex-1" :disabled="isBusy">
              <UIcon v-if="isBusy" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
              {{ isCreateMode ? 'Créer la vente' : 'Enregistrer' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <UiConfirmModal
      ref="deleteConfirmModal"
      title="Supprimer cette vente"
      message="Une facture déjà émise reste chez votre banque : à annuler de son côté."
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="handleDelete"
    />
    <UiConfirmModal
      ref="refundConfirmModal"
      title="Rembourser le paiement"
      :message="refundMessage"
      confirm-text="Rembourser"
      cancel-text="Annuler"
      @confirm="handleRefund"
    />
  </Teleport>
</template>

<script lang="ts" setup>
import { formatShortMonthDateTime } from '~/utils/date'
import type { UseToastReturn } from '~/types/Composables'
import type { OrderEditForm, UiOrderDrawerEmits, UiOrderDrawerProps } from '~/types/UiOrderDrawer'
import type { OrderDrawerMode } from '~/types/DrawerStack'
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import { ref, computed, watch } from 'vue'
import type { Order, OrderPaymentCheckResult } from '~/services/ordersService'
import { OrdersService } from '~/services/ordersService'
import type { DomainCandidate, DomainSuggestions, DomainRegisterResult } from '~/services/domainsService'
import { DomainsService } from '~/services/domainsService'
import { useToast } from '~/composables/useToast'
import { useUserStore } from '~/stores/user'

const DEFAULT_SALE_PRICE_CENTS: number = 50000

/** Order detail drawer for payment, deployment and client email. */
const props: UiOrderDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  order: {
    type: Object as PropType<Order | null>,
    default: null,
  },
  mode: {
    type: String as PropType<OrderDrawerMode>,
    default: 'view',
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiOrderDrawerEmits> = defineEmits<UiOrderDrawerEmits>()

const toast: UseToastReturn = useToast()
const userStore: ReturnType<typeof useUserStore> = useUserStore()

const editMode: Ref<boolean> = ref(false)
const isBusy: Ref<boolean> = ref(false)
const deleteConfirmModal: Ref<{ open: () => void } | null> = ref(null)
const refundConfirmModal: Ref<{ open: () => void } | null> = ref(null)
const isSuggestingDomain: Ref<boolean> = ref(false)
const domainCandidates: Ref<DomainCandidate[]> = ref([])
const isCheckingDomain: Ref<boolean> = ref(false)
const domainStatus: Ref<DomainCandidate | null> = ref(null)
const isProvisioning: Ref<boolean> = ref(false)
const domainCheckTimer: Ref<ReturnType<typeof setTimeout> | null> = ref(null)
// The go-live domain input lives in the PAID view (buy + deploy in one action), seeded from the order.
const goLiveDomain: Ref<string> = ref('')

const editForm: Ref<OrderEditForm> = ref({
  amount_euros: 0,
  business_name: '',
  customer_email: '',
  domain: '',
  status: 'draft',
  notes: '',
})

const statusOptions: { value: string; label: string }[] = [
  { value: 'draft', label: 'Brouillon' },
  { value: 'payment_pending', label: 'Paiement en attente' },
  { value: 'paid', label: 'Payé' },
  { value: 'deploying', label: 'Mise en ligne' },
  { value: 'delivered', label: 'Livré' },
  { value: 'cancelled', label: 'Annulé' },
  { value: 'refunded', label: 'Remboursé' },
]

const STATUS_LABELS: Record<string, string> = Object.fromEntries(
  statusOptions.map((option: { value: string; label: string }) => [option.value, option.label]),
)
const PRODUCT_LABELS: Record<string, string> = {
  website: 'Site web',
  apple_wallet: 'Carte Apple Wallet',
}

const isCreateMode: ComputedRef<boolean> = computed((): boolean => props.mode === 'create')

/** Whether the editable form is shown (new sale or edit an existing one). */
const showForm: ComputedRef<boolean> = computed((): boolean => isCreateMode.value || editMode.value)

const drawerTitle: ComputedRef<string> = computed((): string => {
  if (isCreateMode.value) return 'Nouvelle vente'
  if (!props.order) return 'Vente'
  return props.order.business_name || props.order.customer_email || `Commande #${props.order.id}`
})

const statusLabel: ComputedRef<string> = computed(
  (): string => STATUS_LABELS[props.order?.status ?? ''] ?? props.order?.status ?? '',
)
const productLabel: ComputedRef<string> = computed(
  (): string => PRODUCT_LABELS[props.order?.product_type ?? ''] ?? props.order?.product_type ?? '',
)

/** Payment page of the issued invoice, falling back to the legacy platform link. */
const paymentUrl: ComputedRef<string> = computed(
  (): string => props.order?.payment_url || props.order?.stripe_payment_url || '',
)

const amountLabel: ComputedRef<string> = computed((): string => {
  if (!props.order) return ''
  const euros: number = props.order.amount_cents / 100
  return `${euros % 1 === 0 ? euros.toFixed(0) : euros.toFixed(2)} €`
})

const refundMessage: ComputedRef<string> = computed(
  (): string => `Le montant de ${amountLabel.value} sera remboursé au client via le provider. Action irréversible.`,
)

const statusBadgeClass: ComputedRef<string> = computed((): string => {
  switch (props.order?.status) {
    case 'paid':
    case 'delivered':
      return 'border border-[var(--app-green)]/40 bg-[var(--app-green)]/10 text-[var(--app-green)]'
    case 'payment_pending':
    case 'deploying':
      return 'border border-[var(--app-accent)]/40 bg-[var(--app-accent)]/10 text-[var(--app-accent)]'
    case 'cancelled':
    case 'refunded':
      return 'border border-[var(--app-red)]/40 bg-[var(--app-red)]/10 text-[var(--app-red)]'
    default:
      return 'border border-[var(--app-line)] bg-[var(--app-surface)] text-[var(--app-ink-soft)]'
  }
})

watch(
  (): [boolean, OrderDrawerMode] => [props.open, props.mode],
  ([open, mode]: [boolean, OrderDrawerMode]): void => {
    if (open && mode === 'create') {
      resetCreateForm()
    }
    if (!open) {
      setTimeout((): void => {
        editMode.value = false
      }, 250)
    }
  },
)

// OVH order status → operator wording (mirrors the API's OVH_STATUS_LABELS; raw status when unknown).
const OVH_ORDER_STATUS_LABELS: Record<string, string> = {
  checking: 'paiement en cours de validation',
  delivering: 'commande validée, domaine en cours de livraison',
  delivered: 'commande livrée, domaine enregistré',
  notPaid: 'en attente de paiement (à régler dans le manager OVH)',
  documentsRequested: 'justificatifs demandés par OVH',
  cancelling: 'commande en cours d’annulation',
  cancelled: 'commande annulée',
}

/** Operator wording of the sale's OVH order status, empty when none is tracked. */
const ovhOrderStatusLabel: ComputedRef<string> = computed((): string => {
  const status: string | null = props.order?.ovh_order_status ?? null
  if (!status) return ''
  return OVH_ORDER_STATUS_LABELS[status] ?? status
})

// Sale statuses offering the go-live block: paid, but also unpaid — the operator delivers before invoicing.
const GO_LIVE_STATUSES: string[] = ['draft', 'payment_pending', 'paid']

/** Whether the go-live block (domain purchase + deploy) is offered for this sale. */
const canGoLive: ComputedRef<boolean> = computed((): boolean =>
  Boolean(props.order && GO_LIVE_STATUSES.includes(props.order.status)),
)

/** Go-live helper line — tells whether the client already paid (delivery can precede the invoice). */
const goLiveHint: ComputedRef<string> = computed((): string =>
  props.order?.status === 'paid'
    ? 'Le client a payé — choisis son nom de domaine et mets son site en ligne.'
    : "Choisis son nom de domaine et mets son site en ligne — le paiement n'est pas encore encaissé (livraison avant facturation).",
)

// Seed the go-live domain from the order (and reset it when the drawer switches order).
watch(
  (): string | null | undefined => props.order?.domain,
  (domain: string | null | undefined): void => {
    goLiveDomain.value = domain ?? ''
  },
  { immediate: true },
)

// Any change to the go-live domain (typing, a suggestion chip, « Suggérer ») re-checks availability + price.
watch(
  (): string => goLiveDomain.value,
  (): void => scheduleDomainCheck(),
)

/**
 * Prefill the create form with the user's default sale price.
 */
function resetCreateForm(): void {
  const defaultCents: number = userStore.user?.site_sale_price_cents ?? DEFAULT_SALE_PRICE_CENTS
  editForm.value = {
    amount_euros: Math.round(defaultCents / 100),
    business_name: '',
    customer_email: '',
    domain: '',
    status: 'draft',
    notes: '',
  }
}

/** Copy the invoice payment page to the clipboard. */
async function copyLink(): Promise<void> {
  if (!paymentUrl.value) return
  await navigator.clipboard.writeText(paymentUrl.value)
  toast.success('Lien copié')
}

/** Populate the edit form and enter edit mode. */
function startEdit(): void {
  if (!props.order) return
  editForm.value = {
    amount_euros: Math.round(props.order.amount_cents / 100),
    business_name: props.order.business_name ?? '',
    customer_email: props.order.customer_email ?? '',
    domain: props.order.domain ?? '',
    status: props.order.status,
    notes: props.order.notes ?? '',
  }
  editMode.value = true
}

/** Generic guard to run an order action with busy state + error toast. */
async function runAction(fn: () => Promise<Order>, successMsg: string): Promise<void> {
  if (!props.order) return
  isBusy.value = true
  try {
    const updated: Order = await fn()
    emit('updated', updated)
    toast.success(successMsg)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Une erreur est survenue')
  } finally {
    isBusy.value = false
  }
}

/**
 * Suggest a .fr domain from the prospect (logical name + AI, availability-checked).
 * Pre-fills the domain field with the best free candidate and lists the alternatives.
 * @returns A promise resolved once the suggestions are loaded.
 */
async function suggestDomain(): Promise<void> {
  if (isSuggestingDomain.value) return
  const prospectId: number | null = props.order?.prospect_id ?? null
  const businessName: string = props.order?.business_name?.trim() ?? ''
  if (prospectId === null && !businessName) return
  isSuggestingDomain.value = true
  try {
    const result: DomainSuggestions =
      prospectId !== null
        ? await DomainsService.suggestForProspect(prospectId)
        : await DomainsService.suggestForName(businessName)
    domainCandidates.value = result.candidates
    if (result.suggested) goLiveDomain.value = result.suggested
    else toast.info('Aucun domaine suggéré')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Suggestion impossible')
  } finally {
    isSuggestingDomain.value = false
  }
}

/**
 * Live-check the typed go-live domain's availability + price (debounced), so « disponible / déjà pris » shows.
 * @returns {void}
 */
function scheduleDomainCheck(): void {
  if (domainCheckTimer.value) clearTimeout(domainCheckTimer.value)
  const value: string = goLiveDomain.value.trim()
  domainStatus.value = null
  if (!value) {
    domainCandidates.value = []
    return
  }
  domainCheckTimer.value = setTimeout((): void => {
    // A full domain (has a dot) → check that exact one; a bare label → suggest domains from it.
    if (value.includes('.')) {
      domainCandidates.value = []
      void runDomainCheck(value)
    } else {
      void suggestFromLabel(value)
    }
  }, 450)
}

/**
 * Query the availability + real price for one domain and keep it only if it is still the typed one.
 * @param domain - The full domain to check.
 * @returns A promise resolved once the check runs.
 */
async function runDomainCheck(domain: string): Promise<void> {
  isCheckingDomain.value = true
  try {
    const result: DomainCandidate = await DomainsService.checkAvailability(domain)
    if (goLiveDomain.value.trim() === domain) domainStatus.value = result
  } catch {
    if (goLiveDomain.value.trim() === domain) domainStatus.value = null
  } finally {
    isCheckingDomain.value = false
  }
}

/**
 * As-you-type suggestions: build .fr candidates from a bare label (no AI, snappy).
 * @param label - The bare name typed (no dot).
 * @returns A promise resolved once the suggestions load.
 */
async function suggestFromLabel(label: string): Promise<void> {
  isCheckingDomain.value = true
  try {
    const result: DomainSuggestions = await DomainsService.suggestForName(label, false)
    if (goLiveDomain.value.trim() === label) domainCandidates.value = result.candidates
  } catch {
    // best-effort: keep whatever chips are shown
  } finally {
    isCheckingDomain.value = false
  }
}

/**
 * Buy the domain and deploy the paid sale's linked site onto it — one REAL purchase (~6 €).
 * @returns A promise resolved once the order is placed.
 */
async function provisionDomain(): Promise<void> {
  const domain: string = goLiveDomain.value.trim()
  if (!domain || isProvisioning.value || domainStatus.value?.available === false) return
  isProvisioning.value = true
  try {
    const result: DomainRegisterResult = await DomainsService.provisionDomain(domain, props.order?.id ?? null)
    if (props.order) emit('updated', { ...props.order, domain: result.domain, status: 'deploying' })
    toast.success(`Domaine commandé — ${result.domain}. Le site du client se met en ligne (quelques minutes).`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Réservation impossible')
  } finally {
    isProvisioning.value = false
  }
}

/** Persist edited fields, or create a new sale when the drawer is in create mode. */
async function handleSave(): Promise<void> {
  if (isCreateMode.value) {
    await handleCreate()
    return
  }
  if (!props.order) return
  const orderId: number = props.order.id
  await runAction(
    () =>
      OrdersService.updateOrder(orderId, {
        amount_cents: Math.round(editForm.value.amount_euros * 100),
        business_name: editForm.value.business_name || null,
        customer_email: editForm.value.customer_email || null,
        domain: editForm.value.domain || null,
        status: editForm.value.status,
        notes: editForm.value.notes || null,
      }),
    'Vente mise à jour',
  )
  editMode.value = false
}

/**
 * Create a new draft sale from the form, then hand it to the host for display.
 * @returns A promise resolved once the sale is created.
 */
async function handleCreate(): Promise<void> {
  if (editForm.value.amount_euros <= 0) {
    toast.error('Renseignez un montant')
    return
  }
  isBusy.value = true
  try {
    const created: Order = await OrdersService.createOrder({
      product_type: 'website',
      amount_cents: Math.round(editForm.value.amount_euros * 100),
      business_name: editForm.value.business_name.trim() || null,
      customer_email: editForm.value.customer_email.trim() || null,
      domain: editForm.value.domain.trim() || null,
      notes: editForm.value.notes.trim() || null,
    })
    emit('created', created)
    toast.success('Vente créée')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la création')
  } finally {
    isBusy.value = false
  }
}

/** Mark the order as paid manually. */
async function handleMarkPaid(): Promise<void> {
  if (!props.order) return
  await runAction(() => OrdersService.markOrderPaid(props.order!.id), 'Vente marquée comme payée')
}

/** Ask the provider whether the invoice has been paid, and mark it paid if so. */
async function handleCheckPayment(): Promise<void> {
  if (!props.order) return
  isBusy.value = true
  try {
    const result: OrderPaymentCheckResult = await OrdersService.checkOrderPayment(props.order.id)
    emit('updated', result.order)
    if (result.newly_paid) {
      toast.success('Paiement confirmé — vente marquée payée')
    } else {
      toast.info('Facture encore impayée côté banque')
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Vérification impossible')
  } finally {
    isBusy.value = false
  }
}

/** Put the sold site online (Vercel + domain) + hand over CMS access. */
async function handleDeploy(): Promise<void> {
  if (!props.order) return
  await runAction(() => OrdersService.deployOrder(props.order!.id), 'Mise en ligne lancée')
}

/** Refund the paid order through its provider, then mark it refunded. */
async function handleRefund(): Promise<void> {
  if (!props.order) return
  await runAction(() => OrdersService.refundOrder(props.order!.id), 'Paiement remboursé')
}

/** Delete (cancel) the order. */
async function handleDelete(): Promise<void> {
  if (!props.order) return
  isBusy.value = true
  try {
    await OrdersService.deleteOrder(props.order.id)
    emit('deleted', props.order.id)
    emit('close')
    toast.success('Vente supprimée')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la suppression')
  } finally {
    isBusy.value = false
  }
}
</script>

<style scoped>
.drawer-backdrop-enter-active,
.drawer-backdrop-leave-active {
  transition: opacity 0.2s ease;
}
.drawer-backdrop-enter-from,
.drawer-backdrop-leave-to {
  opacity: 0;
}
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
