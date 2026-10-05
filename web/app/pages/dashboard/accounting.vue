<template>
  <div class="space-y-6">
    <UiPageHeader
      eyebrow="Paramètres"
      title="Comptabilité"
      description="Vue d'ensemble des paiements Stripe et des achats de crédits sur la plateforme."
    />

    <UiLoader v-if="isLoading" label="Chargement de la comptabilité…" />

    <template v-else>
      <div class="grid grid-cols-2 gap-4 @4xl:grid-cols-4">
        <UiStatCard
          label="Total reçu"
          :value="`€${formatCurrency(accountingData?.summary?.total_paid || 0)}`"
          icon="i-lucide-euro"
          accent="emerald"
        />
        <UiStatCard
          label="Net (après frais)"
          :value="`€${formatCurrency(accountingData?.summary?.net_total || 0)}`"
          icon="i-lucide-wallet"
          accent="sky"
        />
        <UiStatCard
          label="Frais Stripe"
          :value="`-€${formatCurrency(accountingData?.summary?.total_stripe_fees || 0)}`"
          icon="i-lucide-credit-card"
          accent="danger"
        />
        <UiStatCard label="Solde disponible" :value="availableBalanceLabel" icon="i-lucide-landmark" accent="neutral" />
      </div>

      <div class="grid grid-cols-1 gap-4 @sm:grid-cols-3">
        <UiStatCard
          label="Total remboursé"
          :value="`€${formatCurrency(accountingData?.summary?.total_refunded || 0)}`"
          icon="i-lucide-undo-2"
          accent="neutral"
        />
        <UiStatCard
          label="Transactions (brut)"
          :value="accountingData?.summary?.total_transactions || 0"
          icon="i-lucide-list"
          accent="neutral"
        />
        <UiStatCard
          label="Transactions affichées"
          :value="displayedTransactions.length"
          icon="i-lucide-filter"
          accent="neutral"
        />
      </div>

      <div class="app-card overflow-hidden p-0">
        <div class="space-y-4 border-b border-[var(--app-line)] px-4 py-4 sm:px-6">
          <div>
            <h2 class="text-sm font-semibold text-[var(--app-ink)]">Transactions crédits</h2>
            <p class="mt-0.5 text-xs text-[var(--app-ink-soft)]">Paiements synchronisés depuis Stripe</p>
          </div>

          <div class="grid grid-cols-2 gap-x-3 gap-y-4 @4xl:grid-cols-4 @4xl:gap-4">
            <div class="col-span-2">
              <label class="app-label mb-1.5 block">Rechercher</label>
              <div class="relative">
                <UIcon
                  name="i-lucide-search"
                  class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
                />
                <input
                  v-model="searchQuery"
                  type="search"
                  class="app-input pl-9"
                  placeholder="Nom, email, ID Stripe, description…"
                />
              </div>
            </div>
            <div>
              <label class="app-label mb-1.5 block">Statut</label>
              <UiSelectField v-model="statusFilter" :options="statusFilterOptions" />
            </div>
            <!-- Conteneur : le sens du tri n'affiche son libellé que si la cellule a la place, sinon l'icône seule. -->
            <div class="@container">
              <label class="app-label mb-1.5 block">Tri</label>
              <div class="flex items-center gap-2">
                <UiSelectField v-model="sortKey" :options="sortOptions" class="min-w-0 flex-1" />
                <button
                  type="button"
                  class="app-btn-secondary h-9 w-9 shrink-0 px-0 text-xs whitespace-nowrap @min-[15rem]:w-auto @min-[15rem]:px-3"
                  :title="sortDirection === 'asc' ? 'Ordre croissant' : 'Ordre décroissant'"
                  :aria-label="sortDirection === 'asc' ? 'Ordre croissant' : 'Ordre décroissant'"
                  @click="toggleSortDirection"
                >
                  <UIcon
                    :name="
                      sortDirection === 'asc' ? 'i-lucide-arrow-up-narrow-wide' : 'i-lucide-arrow-down-wide-narrow'
                    "
                    class="h-3.5 w-3.5"
                  />
                  <span class="hidden @min-[15rem]:inline">
                    {{ sortDirection === 'asc' ? 'Croissant' : 'Décroissant' }}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="displayedTransactions.length === 0" class="px-6 py-12 text-center">
          <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />
          <h3 class="font-display mt-5 text-xl font-semibold text-[var(--app-ink)]">Aucune transaction</h3>
          <p class="mx-auto mt-2 max-w-sm text-sm text-[var(--app-ink-soft)]">
            Aucune transaction ne correspond à vos filtres.
          </p>
        </div>

        <template v-else>
          <div class="md:overflow-x-auto">
            <table class="dlh-card-table w-full min-w-[960px] border-collapse">
              <thead>
                <tr class="bg-[var(--app-surface-2)]">
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">Statut</th>
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">Client</th>
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">Date</th>
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">Crédits</th>
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">Montant</th>
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">Frais Stripe</th>
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">Net</th>
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">Dispo. fonds</th>
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">Paiement</th>
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">Pays</th>
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">IP</th>
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">Appareil</th>
                  <th class="app-label border-b border-[var(--app-line)] px-4 py-2.5 text-left">Détails</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="transaction in displayedTransactions" :key="getTransactionKey(transaction)">
                  <tr
                    class="border-b border-[var(--app-line-soft)] transition-colors last:border-b-0 hover:bg-[var(--app-surface-2)]/60"
                  >
                    <td data-label="Statut" class="px-4 py-3">
                      <span :class="['app-badge', getStatusClass(transaction.payment_info?.status || 'unknown')]">
                        {{ getStatusLabel(transaction.payment_info?.status || 'unknown') }}
                      </span>
                    </td>

                    <td class="px-4 py-3">
                      <div class="text-sm font-semibold text-[var(--app-ink)]">{{ transaction.user_name }}</div>
                      <div class="text-xs text-[var(--app-ink-soft)]">{{ transaction.user_email }}</div>
                    </td>

                    <td data-label="Date" class="font-label px-4 py-3 text-xs text-[var(--app-ink)]">
                      {{ formatNumericDate(transaction.credits_available_date) }}
                    </td>

                    <td data-label="Crédits" class="px-4 py-3 text-sm font-medium text-[var(--app-ink)] tabular-nums">
                      {{ transaction.credits_amount }}
                    </td>

                    <td data-label="Montant" class="px-4 py-3 text-sm font-medium text-[var(--app-ink)] tabular-nums">
                      <span v-if="transaction.payment_info"
                        >€{{ formatCurrency(transaction.payment_info.amount) }}</span
                      >
                      <span v-else class="text-[var(--app-faint)]">—</span>
                    </td>

                    <td data-label="Frais Stripe" class="px-4 py-3 text-sm text-[var(--app-red)] tabular-nums">
                      <span v-if="transaction.payment_info?.application_fee_amount">
                        -€{{ formatCurrency(transaction.payment_info.application_fee_amount) }}
                      </span>
                      <span v-else class="text-[var(--app-faint)]">—</span>
                    </td>

                    <td data-label="Net" class="px-4 py-3 text-sm font-medium text-[var(--app-ink)] tabular-nums">
                      <span v-if="transaction.payment_info?.net_amount">
                        €{{ formatCurrency(transaction.payment_info.net_amount) }}
                      </span>
                      <span v-else class="text-[var(--app-faint)]">—</span>
                    </td>

                    <td data-label="Dispo. fonds" class="px-4 py-3 text-xs text-[var(--app-ink-soft)]">
                      {{ formatAvailability(transaction.payment_info) }}
                    </td>

                    <td data-label="Paiement" class="px-4 py-3 text-xs text-[var(--app-ink)]">
                      <div class="font-medium">
                        {{ transaction.payment_info?.payment_method_type?.toUpperCase() || '—' }}
                      </div>
                      <div class="text-[var(--app-ink-soft)]">{{ formatPaymentDetails(transaction.payment_info) }}</div>
                    </td>

                    <td data-label="Pays" class="px-4 py-3 text-sm text-[var(--app-ink)]">
                      <span
                        v-if="transaction.payment_info?.customer_country"
                        :title="getCountryName(transaction.payment_info.customer_country)"
                        class="cursor-default"
                      >
                        {{ getCountryFlag(transaction.payment_info.customer_country) }}
                        {{ transaction.payment_info.customer_country.toUpperCase() }}
                      </span>
                      <span v-else class="text-[var(--app-faint)]">—</span>
                    </td>

                    <td data-label="IP" class="font-label px-4 py-3 text-xs text-[var(--app-ink-soft)]">
                      {{ transaction.payment_info?.ip_address || '—' }}
                    </td>

                    <td data-label="Appareil" class="px-4 py-3 text-xs text-[var(--app-ink-soft)]">
                      {{ parseUserAgent(transaction.payment_info?.user_agent) }}
                    </td>

                    <td class="px-4 py-3">
                      <button
                        type="button"
                        class="cursor-pointer text-xs font-medium text-[var(--app-accent-ink)] underline-offset-2 hover:underline"
                        @click="toggleTransactionDetails(getTransactionKey(transaction))"
                      >
                        {{ expandedTransactions.has(getTransactionKey(transaction)) ? 'Masquer' : 'Afficher' }}
                      </button>
                    </td>
                  </tr>

                  <tr v-if="expandedTransactions.has(getTransactionKey(transaction))">
                    <td
                      colspan="13"
                      class="border-b border-[var(--app-line-soft)] bg-[var(--app-surface-2)]/40 px-4 py-4 sm:px-6"
                    >
                      <div class="grid grid-cols-1 gap-6 @2xl:grid-cols-2 @4xl:grid-cols-3">
                        <div v-if="transaction.payment_info">
                          <h3 class="app-label mb-3">Informations de paiement</h3>
                          <dl class="space-y-2 text-sm">
                            <div class="flex justify-between gap-4">
                              <dt class="text-[var(--app-ink-soft)]">Moyen</dt>
                              <dd class="font-medium text-[var(--app-ink)]">
                                {{ transaction.payment_info.payment_method_type?.toUpperCase() || '—' }}
                              </dd>
                            </div>
                            <div class="flex justify-between gap-4">
                              <dt class="text-[var(--app-ink-soft)]">Devise</dt>
                              <dd class="font-medium text-[var(--app-ink)] uppercase">
                                {{ transaction.payment_info.currency }}
                              </dd>
                            </div>
                            <div class="flex justify-between gap-4">
                              <dt class="text-[var(--app-ink-soft)]">Date de paiement</dt>
                              <dd class="font-medium text-[var(--app-ink)]">
                                {{ formatNumericDateTime(transaction.payment_info.payment_date) }}
                              </dd>
                            </div>
                            <div v-if="transaction.payment_info.customer_country" class="flex justify-between gap-4">
                              <dt class="text-[var(--app-ink-soft)]">Pays</dt>
                              <dd class="font-medium text-[var(--app-ink)]">
                                {{ getCountryName(transaction.payment_info.customer_country) }}
                              </dd>
                            </div>
                            <div v-if="transaction.payment_info.ip_address" class="flex justify-between gap-4">
                              <dt class="text-[var(--app-ink-soft)]">IP</dt>
                              <dd class="font-label text-xs font-medium text-[var(--app-ink)]">
                                {{ transaction.payment_info.ip_address }}
                              </dd>
                            </div>
                            <div v-if="transaction.payment_info.user_agent" class="flex justify-between gap-4">
                              <dt class="shrink-0 text-[var(--app-ink-soft)]">Appareil</dt>
                              <dd class="truncate text-xs font-medium text-[var(--app-ink)]">
                                {{ parseUserAgent(transaction.payment_info.user_agent) }}
                              </dd>
                            </div>
                          </dl>
                        </div>

                        <div v-if="transaction.payment_info">
                          <h3 class="app-label mb-3">Détails financiers</h3>
                          <dl class="space-y-2 text-sm">
                            <div class="flex justify-between gap-4">
                              <dt class="text-[var(--app-ink-soft)]">Montant payé</dt>
                              <dd class="font-medium text-[var(--app-ink)] tabular-nums">
                                €{{ formatCurrency(transaction.payment_info.amount) }}
                              </dd>
                            </div>
                            <div v-if="transaction.payment_info.amount_received" class="flex justify-between gap-4">
                              <dt class="text-[var(--app-ink-soft)]">Montant reçu</dt>
                              <dd class="font-medium text-[var(--app-ink)] tabular-nums">
                                €{{ formatCurrency(transaction.payment_info.amount_received) }}
                              </dd>
                            </div>
                            <div
                              v-if="transaction.payment_info.application_fee_amount"
                              class="flex justify-between gap-4"
                            >
                              <dt class="text-[var(--app-ink-soft)]">Frais Stripe</dt>
                              <dd class="font-medium text-[var(--app-red)] tabular-nums">
                                -€{{ formatCurrency(transaction.payment_info.application_fee_amount) }}
                              </dd>
                            </div>
                            <div
                              v-if="transaction.payment_info.net_amount"
                              class="flex justify-between gap-4 border-t border-[var(--app-line-soft)] pt-2"
                            >
                              <dt class="font-medium text-[var(--app-ink-soft)]">Montant net</dt>
                              <dd class="font-bold text-[var(--app-green)] tabular-nums">
                                €{{ formatCurrency(transaction.payment_info.net_amount) }}
                              </dd>
                            </div>
                            <div v-if="transaction.payment_info.refund_amount" class="flex justify-between gap-4">
                              <dt class="text-[var(--app-ink-soft)]">Remboursement</dt>
                              <dd class="font-medium text-[var(--app-red)] tabular-nums">
                                -€{{ formatCurrency(transaction.payment_info.refund_amount) }}
                              </dd>
                            </div>
                            <div v-if="transaction.payment_info.refund_date" class="flex justify-between gap-4">
                              <dt class="text-[var(--app-ink-soft)]">Date de remboursement</dt>
                              <dd class="font-medium text-[var(--app-ink)]">
                                {{ formatNumericDateTime(transaction.payment_info.refund_date) }}
                              </dd>
                            </div>
                          </dl>
                        </div>

                        <div>
                          <h3 class="app-label mb-3">Transaction</h3>
                          <dl class="space-y-2 text-sm">
                            <div class="flex justify-between gap-4">
                              <dt class="text-[var(--app-ink-soft)]">ID transaction</dt>
                              <dd class="font-label text-xs font-medium text-[var(--app-ink)]">
                                #{{ transaction.transaction_id }}
                              </dd>
                            </div>
                            <div v-if="transaction.payment_info?.session_id" class="flex justify-between gap-4">
                              <dt class="shrink-0 text-[var(--app-ink-soft)]">Session</dt>
                              <dd class="font-label truncate text-xs font-medium text-[var(--app-ink)]">
                                {{ transaction.payment_info.session_id }}
                              </dd>
                            </div>
                            <div v-if="transaction.payment_info?.payment_intent_id" class="flex justify-between gap-4">
                              <dt class="shrink-0 text-[var(--app-ink-soft)]">Payment Intent</dt>
                              <dd class="font-label truncate text-xs font-medium text-[var(--app-ink)]">
                                {{ transaction.payment_info.payment_intent_id }}
                              </dd>
                            </div>
                            <div class="flex justify-between gap-4">
                              <dt class="text-[var(--app-ink-soft)]">Crédits disponibles le</dt>
                              <dd class="font-medium text-[var(--app-ink)]">
                                {{ formatNumericDateTime(transaction.credits_available_date) }}
                              </dd>
                            </div>
                            <div class="flex justify-between gap-4">
                              <dt class="shrink-0 text-[var(--app-ink-soft)]">Description</dt>
                              <dd class="max-w-xs truncate text-right text-xs font-medium text-[var(--app-ink)]">
                                {{ transaction.description }}
                              </dd>
                            </div>
                          </dl>
                        </div>
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>

          <div
            v-if="showPagination"
            class="flex flex-col gap-3 border-t border-[var(--app-line)] bg-[var(--app-surface-2)]/50 px-4 py-3.5 sm:px-6 @2xl:flex-row @2xl:items-center @2xl:justify-between"
          >
            <div class="font-label text-xs text-[var(--app-ink-soft)]">
              Affichage
              <span class="font-medium text-[var(--app-ink)]">{{ pageStart }}–{{ pageEnd }}</span>
              sur
              <span class="font-medium text-[var(--app-ink)]">{{ totalTransactions }}</span>
            </div>
            <div class="flex flex-wrap items-center gap-3">
              <div class="flex items-center gap-2">
                <span class="app-label">Par page</span>
                <div class="w-20">
                  <UiSelectField v-model="pageSizeModel" :options="pageSizeOptions" />
                </div>
              </div>
              <div class="flex items-center gap-2">
                <button
                  class="app-btn-secondary h-8 min-h-8 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="page <= 1"
                  @click="goToPrevPage"
                >
                  Précédent
                </button>
                <span class="font-label px-1 text-xs text-[var(--app-ink-soft)]">
                  Page {{ page }} / {{ totalPages }}
                </span>
                <button
                  class="app-btn-secondary h-8 min-h-8 px-3 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="page >= totalPages"
                  @click="goToNextPage"
                >
                  Suivant
                </button>
              </div>
            </div>
          </div>
        </template>
      </div>
    </template>

    <div v-if="error && !isLoading" class="app-card border-[var(--app-red)]/40 bg-[var(--app-red-soft)] p-5">
      <div class="flex items-center gap-2 text-[var(--app-red)]">
        <UIcon name="i-lucide-triangle-alert" class="h-4 w-4 shrink-0" />
        <p class="text-sm font-medium">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { formatNumericDate, formatNumericDateTime } from '~/utils/date'
import type { AccountingResponse, CreditPurchaseTransaction, StripePayment } from '~/types'
import type { SelectFieldOption } from '~/types/SelectField'
import type { ComputedRef, Ref } from 'vue'
import { ref, computed, onMounted, watch } from 'vue'
import { AccountingService } from '~/services/accountingService'

/** Dashboard accounting page — admin financial data (admin only). */
definePageMeta({
  layout: 'dashboard',
  middleware: ['auth', 'super-admin'],
})

type SortKey = 'date' | 'amount' | 'net' | 'fees' | 'credits' | 'country' | 'payment_method' | 'availability'

const isLoading: Ref<boolean> = ref(true)
const error: Ref<string | null> = ref(null)
const accountingData: Ref<AccountingResponse | null> = ref(null)
const expandedTransactions: Ref<Set<string>> = ref(new Set())

const searchQuery: Ref<string> = ref('')
const statusFilter: Ref<string> = ref('all')
const sortKey: Ref<SortKey> = ref('date')
const sortDirection: Ref<'asc' | 'desc'> = ref('desc')

const sortOptions: SelectFieldOption[] = [
  { value: 'date', label: 'Date' },
  { value: 'amount', label: 'Montant' },
  { value: 'net', label: 'Net' },
  { value: 'fees', label: 'Frais' },
  { value: 'credits', label: 'Crédits' },
  { value: 'country', label: 'Pays' },
  { value: 'payment_method', label: 'Moyen de paiement' },
  { value: 'availability', label: 'Disponibilité des fonds' },
]

const pageSizeOptions: SelectFieldOption[] = [
  { value: '10', label: '10' },
  { value: '20', label: '20' },
  { value: '50', label: '50' },
  { value: '100', label: '100' },
]

const rawTransactions: ComputedRef<CreditPurchaseTransaction[]> = computed(
  (): CreditPurchaseTransaction[] => accountingData.value?.transactions || [],
)

/** Available balance label for the summary card. */
const availableBalanceLabel: ComputedRef<string> = computed((): string => {
  const balance: number | null | undefined = accountingData.value?.summary?.available_balance
  if (balance === null || balance === undefined) return '—'
  return `€${formatCurrency(balance)}`
})

const statusOptions: ComputedRef<string[]> = computed((): string[] => {
  const statuses: Set<string> = new Set<string>()
  rawTransactions.value.forEach((transaction: CreditPurchaseTransaction) => {
    const status: string | undefined = transaction.payment_info?.status
    if (status) statuses.add(status.toLowerCase())
  })
  return Array.from(statuses).sort()
})

const statusFilterOptions: ComputedRef<SelectFieldOption[]> = computed((): SelectFieldOption[] => [
  { value: 'all', label: 'Tous' },
  ...statusOptions.value.map((status: string): SelectFieldOption => ({ value: status, label: getStatusLabel(status) })),
])

const filteredTransactions: ComputedRef<CreditPurchaseTransaction[]> = computed((): CreditPurchaseTransaction[] => {
  const query: string = searchQuery.value.trim().toLowerCase()
  const status: string = statusFilter.value

  return rawTransactions.value.filter((transaction: CreditPurchaseTransaction): boolean => {
    const paymentInfo: StripePayment | null | undefined = transaction.payment_info
    const transactionStatus: string = paymentInfo?.status?.toLowerCase() || 'unknown'

    const matchesStatus: boolean = status === 'all' || transactionStatus === status
    if (!matchesStatus) return false

    if (!query) return true

    const haystack: string = [
      transaction.user_name,
      transaction.user_email,
      transaction.description,
      paymentInfo?.payment_intent_id,
      paymentInfo?.session_id,
      transactionStatus,
      paymentInfo?.amount?.toString(),
      paymentInfo?.net_amount?.toString(),
      paymentInfo?.application_fee_amount?.toString(),
      paymentInfo?.customer_country,
      getCountryName(paymentInfo?.customer_country || ''),
      getCountryFlag(paymentInfo?.customer_country),
      formatPaymentDetails(paymentInfo),
      formatAvailability(paymentInfo),
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()

    return haystack.includes(query)
  })
})

const displayedTransactions: ComputedRef<CreditPurchaseTransaction[]> = computed((): CreditPurchaseTransaction[] => {
  const direction: number = sortDirection.value === 'asc' ? 1 : -1

  const getAmount: (transaction: CreditPurchaseTransaction, key: 'amount' | 'net' | 'fees') => number = (
    transaction: CreditPurchaseTransaction,
    key: 'amount' | 'net' | 'fees',
  ): number => {
    const info: StripePayment | null | undefined = transaction.payment_info
    if (!info) return 0
    switch (key) {
      case 'amount':
        return toNumeric(info.amount)
      case 'net':
        return toNumeric(info.net_amount)
      case 'fees':
        return toNumeric(info.application_fee_amount)
    }
  }

  const items: CreditPurchaseTransaction[] = [...filteredTransactions.value]
  items.sort((a: CreditPurchaseTransaction, b: CreditPurchaseTransaction): number => {
    let compare: number = 0

    switch (sortKey.value) {
      case 'date':
        compare = new Date(a.credits_available_date).getTime() - new Date(b.credits_available_date).getTime()
        break
      case 'amount':
        compare = getAmount(a, 'amount') - getAmount(b, 'amount')
        break
      case 'net':
        compare = getAmount(a, 'net') - getAmount(b, 'net')
        break
      case 'fees':
        compare = getAmount(a, 'fees') - getAmount(b, 'fees')
        break
      case 'credits':
        compare = toNumeric(a.credits_amount) - toNumeric(b.credits_amount)
        break
      case 'country':
        compare = getCountryName(a.payment_info?.customer_country || '').localeCompare(
          getCountryName(b.payment_info?.customer_country || ''),
          'fr',
        )
        break
      case 'payment_method':
        compare = formatPaymentDetails(a.payment_info).localeCompare(formatPaymentDetails(b.payment_info), 'fr')
        break
      case 'availability': {
        const aTime: number = a.payment_info?.available_at
          ? new Date(a.payment_info.available_at).getTime()
          : Number.MAX_SAFE_INTEGER
        const bTime: number = b.payment_info?.available_at
          ? new Date(b.payment_info.available_at).getTime()
          : Number.MAX_SAFE_INTEGER
        compare = aTime - bTime
        break
      }
      default:
        compare = 0
    }

    if (compare < 0) return -1 * direction
    if (compare > 0) return 1 * direction
    return 0
  })

  return items
})

const page: Ref<number> = ref(1)
const pageSize: Ref<number> = ref(20)

const pageSizeModel: ComputedRef<string> = computed({
  get: (): string => String(pageSize.value),
  set: (value: string): void => {
    pageSize.value = Number(value)
  },
})

const totalTransactions: ComputedRef<number> = computed(
  (): number => accountingData.value?.summary?.total_transactions || 0,
)
const totalPages: ComputedRef<number> = computed((): number =>
  Math.max(1, Math.ceil(totalTransactions.value / pageSize.value)),
)
const showPagination: ComputedRef<boolean> = computed((): boolean => totalTransactions.value > pageSize.value)
const pageStart: ComputedRef<number> = computed((): number =>
  totalTransactions.value === 0 ? 0 : (page.value - 1) * pageSize.value + 1,
)
const pageEnd: ComputedRef<number> = computed((): number =>
  Math.min(page.value * pageSize.value, totalTransactions.value),
)

/**
 * Coerce a value to a number for sorting and display.
 * @param value - Raw numeric value from the API.
 * @returns A finite number, or 0 when missing/invalid.
 */
function toNumeric(value: number | string | null | undefined): number {
  if (value === null || value === undefined) return 0
  if (typeof value === 'number') return value
  const parsed: number = parseFloat(value)
  return Number.isFinite(parsed) ? parsed : 0
}

/**
 * Format a currency amount for display (EUR, fr-FR).
 * @param amount - Amount to format.
 * @returns Formatted decimal string without the currency symbol.
 */
function formatCurrency(amount: number | string | null | undefined): string {
  const numericAmount: number = toNumeric(amount)
  return new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numericAmount)
}

const regionDisplayNames: Intl.DisplayNames = new Intl.DisplayNames(['fr'], { type: 'region' })

/**
 * Resolve a country code to a French display name.
 * @param code - ISO 3166-1 alpha-2 country code.
 * @returns Localized country name or the uppercased code.
 */
function getCountryName(code?: string | null): string {
  if (!code) return 'Pays inconnu'
  try {
    return regionDisplayNames.of(code.toUpperCase()) || code.toUpperCase()
  } catch {
    return code.toUpperCase()
  }
}

/**
 * Return a flag emoji for a country code (fallback: uppercased code).
 * @param code - ISO 3166-1 alpha-2 country code.
 * @returns Flag emoji or code string.
 */
function getCountryFlag(code?: string | null): string {
  if (!code) return ''
  const upper: string = code.toUpperCase()
  if (upper.length !== 2) return upper
  const OFFSET: number = 127397
  return String.fromCodePoint(...upper.split('').map((char: string) => char.charCodeAt(0) + OFFSET))
}

/**
 * Human-readable payment method summary for a Stripe payment row.
 * @param info - Stripe payment metadata attached to the transaction.
 * @returns Short label such as "CARD VISA •••• 4242".
 */
function formatPaymentDetails(info?: CreditPurchaseTransaction['payment_info']): string {
  if (!info) return '—'
  const type: string = info.payment_method_type ? info.payment_method_type.toUpperCase() : ''
  const brand: string = info.payment_method_brand ? info.payment_method_brand.toUpperCase() : ''
  const last4: string = info.payment_method_last4 ? `•••• ${info.payment_method_last4}` : ''
  const parts: string[] = [type, brand, last4].filter(Boolean)
  return parts.length ? parts.join(' ') : '—'
}

/**
 * CSS classes for a Stripe payment status badge.
 * @param status - Raw Stripe status string.
 * @returns Tailwind utility classes for the badge variant.
 */
function getStatusClass(status: string): string {
  const normalized: string = status.toLowerCase()
  if (['paid', 'complete', 'succeeded', 'processing', 'requires_capture'].includes(normalized)) {
    return 'app-badge--success'
  }
  if (['pending', 'requires_confirmation', 'requires_action'].includes(normalized)) {
    return 'app-badge--progress'
  }
  if (
    ['failed', 'canceled', 'requires_payment_method', 'expired', 'refunded', 'partially_refunded'].includes(normalized)
  ) {
    return 'app-badge--danger'
  }
  return ''
}

/**
 * French label for a Stripe payment status.
 * @param status - Raw Stripe status string.
 * @returns Localized status label.
 */
function getStatusLabel(status: string): string {
  const labelMap: Record<string, string> = {
    paid: 'Payé',
    complete: 'Terminé',
    succeeded: 'Réussi',
    processing: 'En cours',
    requires_capture: 'Capture requise',
    pending: 'En attente',
    requires_confirmation: 'Confirmation requise',
    requires_action: 'Action requise',
    requires_payment_method: 'Moyen de paiement requis',
    failed: 'Échoué',
    canceled: 'Annulé',
    unpaid: 'Impayé',
    open: 'Ouvert',
    expired: 'Expiré',
    refunded: 'Remboursé',
    partially_refunded: 'Partiellement remboursé',
  }
  return labelMap[status.toLowerCase()] || status
}

/**
 * Format funds availability for a Stripe payment.
 * @param info - Stripe payment metadata attached to the transaction.
 * @returns Availability date or pending state label.
 */
function formatAvailability(info?: CreditPurchaseTransaction['payment_info']): string {
  if (!info) return '—'
  if (info.available_at) return formatNumericDateTime(info.available_at)
  const status: string = info.status?.toLowerCase() || 'unknown'
  if (['succeeded', 'paid', 'complete', 'processing', 'requires_capture', 'pending'].includes(status)) {
    return 'En attente'
  }
  if (['requires_confirmation', 'requires_action'].includes(status)) {
    return 'En attente client'
  }
  return '—'
}

/**
 * Parse a user agent string into a short device/browser label.
 * @param userAgent - Raw HTTP user agent header.
 * @returns Short device or browser label.
 */
function parseUserAgent(userAgent: string | null | undefined): string {
  if (!userAgent) return '—'
  if (userAgent.includes('Mobile')) return 'Mobile'
  if (userAgent.includes('Tablet')) return 'Tablette'
  if (userAgent.includes('Chrome')) return 'Chrome'
  if (userAgent.includes('Firefox')) return 'Firefox'
  if (userAgent.includes('Safari')) return 'Safari'
  if (userAgent.includes('Edge')) return 'Edge'
  return 'Navigateur'
}

/**
 * Stable key for a transaction row (expand/collapse + v-for).
 * @param transaction - Credit purchase transaction row.
 * @returns Unique string key for the row.
 */
function getTransactionKey(transaction: CreditPurchaseTransaction): string {
  return (
    transaction.payment_info?.payment_intent_id ||
    transaction.payment_info?.session_id ||
    `tx-${transaction.transaction_id}-${transaction.credits_available_date}`
  )
}

/**
 * Toggle expanded detail panel for a transaction row.
 * @param transactionKey - Stable row key from {@link getTransactionKey}.
 */
function toggleTransactionDetails(transactionKey: string): void {
  if (expandedTransactions.value.has(transactionKey)) expandedTransactions.value.delete(transactionKey)
  else expandedTransactions.value.add(transactionKey)
}

/** Flip sort direction between ascending and descending. */
function toggleSortDirection(): void {
  sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
}

/** Fetch accounting summary and transactions from the API. */
async function loadAccountingData(): Promise<void> {
  try {
    isLoading.value = true
    error.value = null
    const skip: number = (page.value - 1) * pageSize.value
    const limit: number = pageSize.value
    accountingData.value = await AccountingService.getAccountingData(skip, limit)
    expandedTransactions.value.clear()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Échec du chargement des données comptables'
    console.error('Failed to load accounting data:', err)
  } finally {
    isLoading.value = false
  }
}

/** Go to the previous results page when possible. */
function goToPrevPage(): void {
  if (page.value > 1) page.value -= 1
}

/** Go to the next results page when possible. */
function goToNextPage(): void {
  if (page.value < totalPages.value) page.value += 1
}

onMounted(async (): Promise<void> => {
  await loadAccountingData()
})

watch([page, pageSize], async (): Promise<void> => {
  if (page.value > totalPages.value) page.value = 1
  await loadAccountingData()
})

watch([rawTransactions, searchQuery, statusFilter, sortKey, sortDirection], (): void => {
  expandedTransactions.value.clear()
})

watch([searchQuery, statusFilter], (): void => {
  page.value = 1
})
</script>
