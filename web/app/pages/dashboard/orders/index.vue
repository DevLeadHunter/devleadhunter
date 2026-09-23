<template>
  <div class="space-y-5">
    <div class="flex flex-col gap-4 @2xl:flex-row @2xl:items-end @2xl:justify-between">
      <div class="min-w-0">
        <p class="app-label flex items-center gap-2">
          <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
          Commercial
        </p>
        <h1 class="app-page-title mt-2">Ventes</h1>
        <p class="mt-1.5 max-w-2xl text-sm text-[var(--app-ink-soft)]">
          Suivi de vos ventes de sites web, du brouillon à la mise en ligne.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2 sm:gap-3 @2xl:justify-end">
        <button
          :disabled="isLoading"
          class="app-btn-secondary h-9 shrink-0 px-4 text-xs whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
          @click="loadAll"
        >
          <UIcon name="i-lucide-refresh-cw" :class="['h-3.5 w-3.5', isLoading && 'animate-spin']" />
          Actualiser
        </button>
        <button class="app-btn-primary h-9 shrink-0 px-4 text-xs whitespace-nowrap" @click="handleCreate">
          <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
          Nouvelle vente
        </button>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4 @4xl:grid-cols-4">
      <UiStatCard
        label="Chiffre d'affaires"
        :value="formatCents(stats?.revenue_cents ?? 0)"
        icon="i-lucide-euro"
        accent="emerald"
      />
      <UiStatCard label="Ventes gagnées" :value="stats?.won_count ?? 0" icon="i-lucide-circle-check" accent="emerald" />
      <UiStatCard
        label="En attente de paiement"
        :value="stats?.pending_count ?? 0"
        icon="i-lucide-hourglass"
        accent="sky"
      />
      <UiStatCard
        label="Pipeline"
        :value="formatCents(stats?.pipeline_cents ?? 0)"
        icon="i-lucide-trending-up"
        accent="neutral"
      />
    </div>

    <UiLoader v-if="isLoading" label="Chargement des ventes…" />

    <UiEmptyState
      v-else-if="orders.length === 0"
      title="Aucune vente"
      description="Marquez un prospect comme vendu, ou créez une vente manuellement."
    >
      <template #action>
        <button class="app-btn-primary" @click="handleCreate">
          <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
          Nouvelle vente
        </button>
      </template>
    </UiEmptyState>

    <div v-else class="app-card overflow-hidden">
      <BaseTable min-width="620px">
        <template #head>
          <BaseTableTh>Client</BaseTableTh>
          <BaseTableTh align="right">Montant</BaseTableTh>
          <BaseTableTh align="center">Statut</BaseTableTh>
          <BaseTableTh align="right">Date</BaseTableTh>
        </template>

        <BaseTableTr
          v-for="order in orders"
          :key="order.id"
          class="cursor-pointer"
          @click="openDrawer(order)"
          @keydown.enter="openDrawer(order)"
        >
          <BaseTableTd>
            <span class="block text-sm font-semibold text-[var(--app-ink)]">
              {{ order.business_name || order.customer_email || `Commande #${order.id}` }}
            </span>
            <span class="font-label text-xs text-[var(--app-ink-soft)]">
              {{ order.customer_email || 'Sans contact' }}
            </span>
          </BaseTableTd>

          <BaseTableTd label="Montant" align="right" class="text-sm font-semibold text-[var(--app-ink)] tabular-nums">
            {{ formatCents(order.amount_cents) }}
          </BaseTableTd>

          <BaseTableTd label="Statut" align="center">
            <span :class="['app-badge', STATUS_BADGE_CLASS[order.status] ?? '']">
              {{ statusLabel(order.status) }}
            </span>
          </BaseTableTd>

          <BaseTableTd label="Date" align="right" class="font-label text-xs text-[var(--app-ink-soft)]">
            {{ formatShortMonthDate(order.created_at) }}
          </BaseTableTd>
        </BaseTableTr>
      </BaseTable>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { formatShortMonthDate } from '~/utils/date'
import type { UseToastReturn } from '~/types/Composables'
import { onMounted, ref, watch } from 'vue'
import type { Ref } from 'vue'
import type { LocationQueryValue } from 'vue-router'
import type { OrderMutationNotice } from '~/types/DrawerStack'
import type { Order, OrderListResponse, OrderStats } from '~/services/ordersService'
import { OrdersService } from '~/services/ordersService'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const toast: UseToastReturn = useToast()

const orders: Ref<Order[]> = ref([])
const stats: Ref<OrderStats | null> = ref(null)
const isLoading: Ref<boolean> = ref(false)

const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

const STATUS_LABELS: Record<string, string> = {
  draft: 'Brouillon',
  payment_pending: 'Paiement en attente',
  paid: 'Payé',
  deploying: 'Mise en ligne',
  delivered: 'Livré',
  cancelled: 'Annulé',
  refunded: 'Remboursé',
}

const STATUS_BADGE_CLASS: Record<string, string> = {
  draft: '',
  payment_pending: 'app-badge--progress',
  paid: 'app-badge--success',
  deploying: 'app-badge--info',
  delivered: 'app-badge--success',
  cancelled: 'app-badge--danger',
  refunded: 'app-badge--danger',
}

/**
 * Format an amount in cents as euros.
 * @param cents - Amount in cents.
 * @returns Formatted euro string.
 */
function formatCents(cents: number): string {
  const euros: number = cents / 100
  const amount: string = euros % 1 === 0 ? euros.toFixed(0) : euros.toFixed(2).replace('.', ',')
  return `${amount} €`
}

/**
 * Human label for an order status.
 * @param status - Raw status value.
 * @returns Localized label.
 */
function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status
}

/** Load orders and stats. */
async function loadAll(): Promise<void> {
  isLoading.value = true
  try {
    const [list, s]: [OrderListResponse, OrderStats] = await Promise.all([
      OrdersService.listOrders(),
      OrdersService.getOrderStats(),
    ])
    orders.value = list.items
    stats.value = s
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors du chargement des ventes')
  } finally {
    isLoading.value = false
  }
}

/** Create a new draft order then open its detail drawer. */
function handleCreate(): void {
  drawerStack.push({ kind: 'order', order: null, mode: 'create' })
}

/**
 * Open the order drawer on the persistent stack.
 * @param order - The order to display.
 */
function openDrawer(order: Order): void {
  drawerStack.push({ kind: 'order', order, mode: 'view' })
}

/** Apply the latest order mutation broadcast by a drawer to the list. */
function applyOrderMutation(): void {
  const notice: OrderMutationNotice | null = drawerStack.lastOrderMutation
  if (!notice) return
  if (notice.type === 'deleted') {
    orders.value = orders.value.filter((order: Order): boolean => order.id !== notice.orderId)
  } else {
    const index: number = orders.value.findIndex((order: Order): boolean => order.id === notice.order.id)
    if (index !== -1) {
      orders.value.splice(index, 1, notice.order)
    } else {
      orders.value.unshift(notice.order)
    }
  }
  void refreshStats()
}

/** Refresh just the stats block. */
async function refreshStats(): Promise<void> {
  try {
    stats.value = await OrdersService.getOrderStats()
  } catch {
    // non-blocking
  }
}

watch((): number => drawerStack.orderMutationCounter, applyOrderMutation)

onMounted(async (): Promise<void> => {
  await loadAll()
  // Deep-link from a sale notification: ?open=<orderId> opens the order drawer.
  const openParam: LocationQueryValue | LocationQueryValue[] | undefined = useRoute().query.open
  const openId: number = Number(Array.isArray(openParam) ? openParam[0] : openParam)
  if (!Number.isNaN(openId) && openId > 0) {
    const target: Order | undefined = orders.value.find((order: Order): boolean => order.id === openId)
    if (target) openDrawer(target)
  }
})
</script>
