<template>
  <Teleport to="body">
    <Transition name="drawer-backdrop">
      <div v-if="open" class="fixed inset-0 z-40 bg-[var(--app-overlay)] backdrop-blur-sm" @click="$emit('close')" />
    </Transition>

    <Transition name="drawer-panel">
      <div
        v-if="open && order"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
      >
        <!-- Header -->
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)]"
          >
            <UIcon name="i-lucide-shopping-cart" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="mb-1 flex flex-wrap items-center gap-1.5">
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
              {{ order.business_name || order.customer_email || `Commande #${order.id}` }}
            </h2>
            <p class="mt-0.5 text-sm font-semibold text-[var(--app-accent-ink)]">{{ amountLabel }}</p>
          </div>
          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface)] hover:text-[var(--app-ink)]"
            @click="$emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto">
          <!-- VIEW MODE -->
          <template v-if="!editMode">
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

            <!-- Payment link -->
            <div class="space-y-2 px-5 py-4">
              <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Paiement</p>
              <div v-if="order.stripe_payment_url" class="flex items-center gap-2">
                <input :value="order.stripe_payment_url" readonly class="input-field flex-1 truncate text-xs" />
                <button
                  class="flex h-9 w-9 shrink-0 items-center justify-center rounded border border-[var(--app-line)] text-[var(--app-ink-soft)] hover:text-[var(--app-accent-ink)]"
                  title="Copier"
                  @click="copyLink"
                >
                  <UIcon name="i-lucide-copy" class="h-4 w-4" />
                </button>
              </div>
              <p v-else class="text-sm text-[var(--app-faint)]">Aucun lien de paiement généré.</p>
              <p v-if="order.payment_link_sent_at" class="text-[10px] text-[var(--app-ink-soft)]">
                Email envoyé le {{ formatDate(order.payment_link_sent_at) }}
              </p>
              <p v-if="order.paid_at" class="text-[10px] text-[var(--app-green)]">
                Payé le {{ formatDate(order.paid_at) }}
              </p>
            </div>

            <!-- Email preview -->
            <div v-if="emailPreview" class="border-t border-[var(--app-surface-2)] px-5 py-4">
              <p class="mb-2 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
                Aperçu de l'email
              </p>
              <p class="mb-2 text-xs text-[var(--app-ink-soft)]">
                <span class="font-medium text-[var(--app-ink)]">Objet :</span> {{ emailPreview.subject }}
              </p>
              <iframe
                :srcdoc="emailPreview.body_html"
                class="h-64 w-full rounded border border-[var(--app-line)] bg-white"
                sandbox=""
              ></iframe>
              <button class="btn-primary mt-3 w-full" :disabled="isSending" @click="handleSendEmail">
                <UIcon v-if="isSending" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
                Envoyer l'email au client
              </button>
            </div>

            <div v-if="order.notes" class="border-t border-[var(--app-surface-2)] px-5 py-4">
              <p class="mb-1 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Notes</p>
              <p class="text-sm whitespace-pre-line text-[var(--app-ink)]">{{ order.notes }}</p>
            </div>
          </template>

          <!-- EDIT MODE -->
          <form v-else id="order-edit-form" class="space-y-4 p-5" @submit.prevent="handleSave">
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                >Montant (€)</label
              >
              <input v-model.number="editForm.amount_euros" type="number" min="0" step="1" class="input-field" />
            </div>
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                >Nom de l'entreprise</label
              >
              <input v-model="editForm.business_name" type="text" class="input-field" />
            </div>
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                >Email client</label
              >
              <input v-model="editForm.customer_email" type="email" class="input-field" />
            </div>
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                >Domaine (mise en ligne)</label
              >
              <input v-model="editForm.domain" type="text" class="input-field" placeholder="monentreprise.fr" />
            </div>
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                >Statut</label
              >
              <select v-model="editForm.status" class="input-field">
                <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
              </select>
            </div>
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase"
                >Notes</label
              >
              <textarea v-model="editForm.notes" rows="3" class="input-field"></textarea>
            </div>
          </form>
        </div>

        <!-- Footer -->
        <div class="border-t border-[var(--app-line)] px-5 py-4">
          <div v-if="showDeleteConfirm" class="rounded-lg border border-[var(--app-red)]/40 bg-[var(--app-red)]/10 p-4">
            <p class="mb-0.5 text-sm font-medium text-[var(--app-ink)]">Supprimer cette vente ?</p>
            <p class="mb-3 text-xs text-[var(--app-ink-soft)]">Le lien de paiement Stripe sera désactivé.</p>
            <div class="flex gap-2">
              <button class="btn-secondary flex-1 text-xs" :disabled="isBusy" @click="showDeleteConfirm = false">
                Annuler
              </button>
              <button class="btn-danger flex-1 text-xs" :disabled="isBusy" @click="handleDelete">Confirmer</button>
            </div>
          </div>

          <div v-else-if="!editMode" class="space-y-2">
            <div class="flex gap-2">
              <button
                v-if="!order.stripe_payment_url"
                class="btn-primary flex-1"
                :disabled="isBusy"
                @click="handleGenerateLink"
              >
                <UIcon v-if="isBusy" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
                <UIcon v-else name="i-lucide-link" class="h-4 w-4" />
                Générer le lien de paiement
              </button>
              <button v-else class="btn-secondary flex-1" :disabled="isBusy" @click="loadEmailPreview">
                <UIcon name="i-lucide-eye" class="h-4 w-4" />Aperçu de l'email
              </button>
            </div>
            <div class="flex gap-2">
              <button v-if="!order.paid_at" class="btn-secondary flex-1" :disabled="isBusy" @click="handleMarkPaid">
                <UIcon name="i-lucide-circle-check" class="h-4 w-4" />Marquer payé
              </button>
              <button class="btn-secondary flex-1" :disabled="isBusy" @click="handleDeploy">
                <UIcon name="i-lucide-rocket" class="h-4 w-4" />Mettre en ligne
              </button>
            </div>
            <div class="flex gap-2">
              <button class="btn-secondary flex-1" @click="startEdit">
                <UIcon name="i-lucide-square-pen" class="h-4 w-4" />Modifier
              </button>
              <button class="btn-danger flex-1" @click="showDeleteConfirm = true">
                <UIcon name="i-lucide-trash-2" class="h-4 w-4" />Supprimer
              </button>
            </div>
          </div>

          <div v-else class="flex gap-2">
            <button type="button" class="btn-secondary flex-1" :disabled="isBusy" @click="editMode = false">
              Annuler
            </button>
            <button type="submit" form="order-edit-form" class="btn-primary flex-1" :disabled="isBusy">
              <UIcon v-if="isBusy" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />Enregistrer
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import { ref, computed, watch } from 'vue'
import type { Order, OrderPaymentEmailPreview } from '~/services/ordersService'
import type { UiOrderDrawerProps } from '~/types/UiOrderDrawer'
import {
  createOrderPaymentLink,
  deleteOrder as deleteOrderApi,
  deployOrder,
  markOrderPaid,
  previewOrderPaymentEmail,
  sendOrderPaymentEmail,
  updateOrder,
} from '~/services/ordersService'
import { useToast } from '~/composables/useToast'

/**
 * Définit les props du composant UiOrderDrawer.
 */
const props: UiOrderDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  order: {
    type: Object as PropType<Order | null>,
    default: null,
  },
})

const emit = defineEmits<{
  /** Close the drawer */
  close: []
  /** Order was updated (re-fetch in parent) */
  updated: [order: Order]
  /** Order was deleted */
  deleted: [orderId: number]
}>()

const toast = useToast()

const editMode: Ref<boolean> = ref(false)
const isBusy: Ref<boolean> = ref(false)
const isSending: Ref<boolean> = ref(false)
const showDeleteConfirm: Ref<boolean> = ref(false)
const emailPreview: Ref<OrderPaymentEmailPreview | null> = ref(null)

interface EditForm {
  amount_euros: number
  business_name: string
  customer_email: string
  domain: string
  status: string
  notes: string
}

const editForm: Ref<EditForm> = ref({
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

const STATUS_LABELS: Record<string, string> = Object.fromEntries(statusOptions.map((s) => [s.value, s.label]))
const PRODUCT_LABELS: Record<string, string> = {
  website: 'Site web',
  apple_wallet: 'Carte Apple Wallet',
}

const statusLabel: ComputedRef<string> = computed(
  (): string => STATUS_LABELS[props.order?.status ?? ''] ?? props.order?.status ?? '',
)
const productLabel: ComputedRef<string> = computed(
  (): string => PRODUCT_LABELS[props.order?.product_type ?? ''] ?? props.order?.product_type ?? '',
)

const amountLabel: ComputedRef<string> = computed((): string => {
  if (!props.order) return ''
  const euros = props.order.amount_cents / 100
  return `${euros % 1 === 0 ? euros.toFixed(0) : euros.toFixed(2)} €`
})

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
  () => [props.open, props.order?.id],
  ([open]): void => {
    if (!open) {
      setTimeout((): void => {
        editMode.value = false
        showDeleteConfirm.value = false
        emailPreview.value = null
      }, 250)
    } else {
      emailPreview.value = null
    }
  },
)

/**
 * Format an ISO date string to a French locale date-time.
 * @param dateStr - ISO date string from the API.
 * @returns Human-readable date.
 */
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Copy the Stripe payment URL to the clipboard. */
async function copyLink(): Promise<void> {
  if (!props.order?.stripe_payment_url) return
  await navigator.clipboard.writeText(props.order.stripe_payment_url)
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
    const updated = await fn()
    emit('updated', updated)
    toast.success(successMsg)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Une erreur est survenue')
  } finally {
    isBusy.value = false
  }
}

/** Persist edited fields. */
async function handleSave(): Promise<void> {
  if (!props.order) return
  const orderId = props.order.id
  await runAction(
    () =>
      updateOrder(orderId, {
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

/** Generate the Stripe payment link. */
async function handleGenerateLink(): Promise<void> {
  if (!props.order) return
  await runAction(() => createOrderPaymentLink(props.order!.id), 'Lien de paiement généré')
}

/** Mark the order as paid manually. */
async function handleMarkPaid(): Promise<void> {
  if (!props.order) return
  await runAction(() => markOrderPaid(props.order!.id), 'Vente marquée comme payée')
}

/** Put the sold site online (Vercel + domain) + hand over CMS access. */
async function handleDeploy(): Promise<void> {
  if (!props.order) return
  await runAction(() => deployOrder(props.order!.id), 'Mise en ligne lancée')
}

/** Load the payment-link email preview. */
async function loadEmailPreview(): Promise<void> {
  if (!props.order) return
  isBusy.value = true
  try {
    emailPreview.value = await previewOrderPaymentEmail(props.order.id)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Impossible de charger l'aperçu")
  } finally {
    isBusy.value = false
  }
}

/** Send the payment-link email to the client. */
async function handleSendEmail(): Promise<void> {
  if (!props.order) return
  isSending.value = true
  try {
    const updated = await sendOrderPaymentEmail(props.order.id)
    emit('updated', updated)
    emailPreview.value = null
    toast.success('Email envoyé au client')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'envoi")
  } finally {
    isSending.value = false
  }
}

/** Delete (cancel) the order. */
async function handleDelete(): Promise<void> {
  if (!props.order) return
  isBusy.value = true
  try {
    await deleteOrderApi(props.order.id)
    emit('deleted', props.order.id)
    emit('close')
    toast.success('Vente supprimée')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la suppression')
  } finally {
    isBusy.value = false
    showDeleteConfirm.value = false
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
