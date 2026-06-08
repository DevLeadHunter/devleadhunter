<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-[#f9f9f9]">Ventes</h1>
        <p class="text-muted mt-2 text-sm">Suivi commercial de vos ventes de sites web</p>
      </div>
      <div class="flex items-center gap-3">
        <button :disabled="isLoading" class="btn-secondary disabled:opacity-50" @click="loadAll">
          <i class="fa-solid fa-rotate-right mr-2"></i>Actualiser
        </button>
        <button class="btn-primary" :disabled="isCreating" @click="handleCreate">
          <i class="fa-solid fa-plus mr-2"></i>Nouvelle vente
        </button>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 gap-6 md:grid-cols-4">
      <div class="card">
        <p class="text-muted text-sm font-medium">Chiffre d'affaires</p>
        <p class="mt-2 text-3xl font-bold text-[#3fb950]">{{ formatCents(stats?.revenue_cents ?? 0) }}</p>
      </div>
      <div class="card">
        <p class="text-muted text-sm font-medium">Ventes gagnées</p>
        <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ stats?.won_count ?? 0 }}</p>
      </div>
      <div class="card">
        <p class="text-muted text-sm font-medium">En attente de paiement</p>
        <p class="mt-2 text-3xl font-bold text-[#e3b341]">{{ stats?.pending_count ?? 0 }}</p>
      </div>
      <div class="card">
        <p class="text-muted text-sm font-medium">Pipeline</p>
        <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ formatCents(stats?.pipeline_cents ?? 0) }}</p>
      </div>
    </div>

    <!-- Loader / empty / table -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <i class="fa-solid fa-spinner fa-spin text-muted text-4xl"></i>
    </div>

    <div v-else-if="orders.length === 0" class="py-12 text-center">
      <i class="fa-solid fa-cart-shopping text-muted mb-4 text-6xl"></i>
      <h3 class="mt-4 text-lg font-medium text-[#f9f9f9]">Aucune vente</h3>
      <p class="text-muted mt-2 text-sm">Marquez un prospect comme vendu, ou créez une vente manuellement.</p>
    </div>

    <div v-else class="card overflow-hidden p-0">
      <table class="w-full border-collapse">
        <thead>
          <tr class="bg-[#050505]">
            <th class="text-muted border-b border-[#30363d] px-4 py-3 text-left text-xs font-semibold">Client</th>
            <th class="text-muted border-b border-[#30363d] px-4 py-3 text-left text-xs font-semibold">Montant</th>
            <th class="text-muted border-b border-[#30363d] px-4 py-3 text-left text-xs font-semibold">Statut</th>
            <th class="text-muted border-b border-[#30363d] px-4 py-3 text-left text-xs font-semibold">Date</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="order in orders"
            :key="order.id"
            class="cursor-pointer border-b border-[#1f1f1f] transition-colors last:border-b-0 hover:bg-[#222222]"
            @click="openDrawer(order)"
          >
            <td class="px-4 py-3">
              <p class="text-sm font-medium text-[#f9f9f9]">
                {{ order.business_name || order.customer_email || `#${order.id}` }}
              </p>
              <p v-if="order.customer_email" class="text-xs text-[#8b949e]">{{ order.customer_email }}</p>
            </td>
            <td class="px-4 py-3 text-sm text-[#f9f9f9]">{{ formatCents(order.amount_cents) }}</td>
            <td class="px-4 py-3">
              <span
                :class="[
                  'inline-flex items-center rounded px-2 py-0.5 text-[10px] font-medium',
                  statusClass(order.status),
                ]"
              >
                {{ statusLabel(order.status) }}
              </span>
            </td>
            <td class="px-4 py-3 text-xs text-[#8b949e]">{{ formatDate(order.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <UiOrderDrawer
      :open="drawerOpen"
      :order="drawerOrder"
      @close="drawerOpen = false"
      @updated="handleOrderUpdated"
      @deleted="handleOrderDeleted"
    />
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import type { Ref } from 'vue'
import type { Order, OrderStats } from '~/services/ordersService'
import { createOrder, getOrderStats, listOrders } from '~/services/ordersService'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const toast = useToast()

const orders: Ref<Order[]> = ref<Order[]>([])
const stats: Ref<OrderStats | null> = ref<OrderStats | null>(null)
const isLoading: Ref<boolean> = ref(false)
const isCreating: Ref<boolean> = ref(false)

const drawerOpen: Ref<boolean> = ref(false)
const drawerOrder: Ref<Order | null> = ref<Order | null>(null)

const STATUS_LABELS: Record<string, string> = {
  draft: 'Brouillon',
  payment_pending: 'Paiement en attente',
  paid: 'Payé',
  deploying: 'Mise en ligne',
  delivered: 'Livré',
  cancelled: 'Annulé',
  refunded: 'Remboursé',
}

/**
 * Format an amount in cents as euros.
 * @param cents - Amount in cents.
 * @returns Formatted euro string.
 */
function formatCents(cents: number): string {
  const euros = cents / 100
  return `${euros % 1 === 0 ? euros.toFixed(0) : euros.toFixed(2)} €`
}

/**
 * Format an ISO date string to a short French date.
 * @param dateStr - ISO date string.
 * @returns Human-readable date.
 */
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}

/**
 * Human label for an order status.
 * @param status - Raw status value.
 * @returns Localized label.
 */
function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status
}

/**
 * Tailwind classes for a status badge.
 * @param status - Raw status value.
 * @returns Class string.
 */
function statusClass(status: string): string {
  switch (status) {
    case 'paid':
    case 'delivered':
      return 'border border-[#3fb950]/40 bg-[#3fb950]/10 text-[#3fb950]'
    case 'payment_pending':
    case 'deploying':
      return 'border border-[#e3b341]/40 bg-[#e3b341]/10 text-[#e3b341]'
    case 'cancelled':
    case 'refunded':
      return 'border border-[#da3633]/40 bg-[#da3633]/10 text-[#da3633]'
    default:
      return 'border border-[#30363d] bg-[#1a1a1a] text-[#8b949e]'
  }
}

/** Load orders and stats. */
async function loadAll(): Promise<void> {
  isLoading.value = true
  try {
    const [list, s] = await Promise.all([listOrders(), getOrderStats()])
    orders.value = list.items
    stats.value = s
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors du chargement des ventes')
  } finally {
    isLoading.value = false
  }
}

/** Create a new draft order then open it for editing. */
async function handleCreate(): Promise<void> {
  isCreating.value = true
  try {
    const order = await createOrder({ product_type: 'website' })
    orders.value.unshift(order)
    openDrawer(order)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la création')
  } finally {
    isCreating.value = false
  }
}

/** Open the drawer for a given order. */
function openDrawer(order: Order): void {
  drawerOrder.value = order
  drawerOpen.value = true
}

/** Patch the local list when an order is updated. */
function handleOrderUpdated(updated: Order): void {
  const idx = orders.value.findIndex((o) => o.id === updated.id)
  if (idx !== -1) orders.value.splice(idx, 1, updated)
  drawerOrder.value = updated
  void refreshStats()
}

/** Remove a deleted order from the list. */
function handleOrderDeleted(orderId: number): void {
  orders.value = orders.value.filter((o) => o.id !== orderId)
  void refreshStats()
}

/** Refresh just the stats block. */
async function refreshStats(): Promise<void> {
  try {
    stats.value = await getOrderStats()
  } catch {
    // non-blocking
  }
}

onMounted((): void => {
  void loadAll()
})
</script>
