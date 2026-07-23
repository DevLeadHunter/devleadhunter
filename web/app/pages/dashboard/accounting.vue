<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-[var(--app-ink)]">Accounting</h1>
    </div>

    <div v-if="isLoading" class="space-y-6">
      <div class="card">
        <div class="animate-pulse space-y-4">
          <div class="h-6 w-1/4 rounded bg-[var(--app-surface-2)]"></div>
          <div class="h-32 rounded bg-[var(--app-surface-2)]"></div>
        </div>
      </div>
    </div>

    <div v-else class="space-y-6">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div class="card">
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <p class="mb-1 text-xs text-[var(--app-ink-soft)]">Total received</p>
              <p class="text-lg font-bold text-[var(--app-ink)]">
                €{{ formatCurrency(accountingData?.summary?.total_paid || 0) }}
              </p>
            </div>
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--app-green)]/20">
              <UIcon name="i-lucide-euro" class="h-5 w-5 text-[var(--app-green)]" />
            </div>
          </div>
        </div>

        <div class="card">
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <p class="mb-1 text-xs text-[var(--app-ink-soft)]">Net (after fees)</p>
              <p class="text-lg font-bold text-[var(--app-ink)]">
                €{{ formatCurrency(accountingData?.summary?.net_total || 0) }}
              </p>
            </div>
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--app-accent-ink)]/20">
              <UIcon name="i-lucide-wallet" class="h-5 w-5 text-[var(--app-accent-ink)]" />
            </div>
          </div>
        </div>

        <div class="card">
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <p class="mb-1 text-xs text-[var(--app-ink-soft)]">Stripe fees</p>
              <p class="text-lg font-bold text-[var(--app-red)]">
                -€{{ formatCurrency(accountingData?.summary?.total_stripe_fees || 0) }}
              </p>
            </div>
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--app-red)]/20">
              <UIcon name="i-lucide-credit-card" class="h-5 w-5 text-[var(--app-red)]" />
            </div>
          </div>
        </div>

        <div class="card">
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <p class="mb-1 text-xs text-[var(--app-ink-soft)]">Available balance</p>
              <p class="text-lg font-bold text-[var(--app-ink)]">
                <span
                  v-if="
                    accountingData?.summary?.available_balance !== null &&
                    accountingData?.summary?.available_balance !== undefined
                  "
                >
                  €{{ formatCurrency(accountingData.summary.available_balance) }}
                </span>
                <span v-else class="text-[var(--app-ink-soft)]">N/A</span>
              </p>
            </div>
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--app-surface-2)]">
              <UIcon name="i-lucide-landmark" class="h-5 w-5 text-[var(--app-ink-soft)]" />
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div class="card">
          <p class="mb-1 text-xs text-[var(--app-ink-soft)]">Total refunded</p>
          <p class="text-base font-semibold text-[var(--app-ink)]">
            €{{ formatCurrency(accountingData?.summary?.total_refunded || 0) }}
          </p>
        </div>
        <div class="card">
          <p class="mb-1 text-xs text-[var(--app-ink-soft)]">Transactions (raw)</p>
          <p class="text-base font-semibold text-[var(--app-ink)]">
            {{ accountingData?.summary?.total_transactions || 0 }}
          </p>
        </div>
        <div class="card">
          <p class="mb-1 text-xs text-[var(--app-ink-soft)]">Transactions displayed</p>
          <p class="text-base font-semibold text-[var(--app-ink)]">
            {{ displayedTransactions.length }}
          </p>
        </div>
      </div>

      <div class="card overflow-hidden p-0">
        <div class="space-y-4 border-b border-[var(--app-line)] bg-[var(--app-bg)] px-2 py-4 sm:px-6">
          <div>
            <h2 class="text-base font-semibold text-[var(--app-ink)]">Credit transactions</h2>
            <p class="mt-1 text-xs text-[var(--app-ink-soft)]">Payments pulled directly from Stripe</p>
          </div>

          <div class="flex flex-col gap-3 lg:flex-row">
            <div class="relative flex-1">
              <UIcon
                name="i-lucide-search"
                class="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[var(--app-ink-soft)]"
              />
              <input
                v-model="searchQuery"
                type="search"
                class="w-full rounded border border-[var(--app-line)] bg-[var(--app-surface)] px-10 py-2 text-sm text-[var(--app-ink)] placeholder:text-[var(--app-ink-soft)] focus:border-[var(--app-ink)] focus:ring-1 focus:ring-[var(--app-ink)] focus:outline-none"
                placeholder="Search (name, email, Stripe ID, description...)"
              />
            </div>

            <div class="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-2">
              <select
                v-model="statusFilter"
                class="min-w-[160px] rounded border border-[var(--app-line)] bg-[var(--app-surface)] px-3 py-2 text-sm text-[var(--app-ink)]"
              >
                <option value="">All statuses</option>
                <option v-for="status in statusOptions" :key="status" :value="status">
                  {{ getStatusLabel(status) }}
                </option>
              </select>

              <div class="flex items-center gap-2">
                <select
                  v-model="sortKey"
                  class="rounded border border-[var(--app-line)] bg-[var(--app-surface)] px-3 py-2 text-sm text-[var(--app-ink)]"
                >
                  <option value="date">Date</option>
                  <option value="amount">Amount</option>
                  <option value="net">Net</option>
                  <option value="fees">Fees</option>
                  <option value="credits">Credits</option>
                  <option value="country">Country</option>
                  <option value="payment_method">Payment Method</option>
                  <option value="availability">Funds availability</option>
                </select>
                <button
                  type="button"
                  class="flex items-center gap-2 rounded border border-[var(--app-line)] bg-[var(--app-surface)] px-3 py-2 text-sm text-[var(--app-ink)] transition hover:border-[var(--app-ink)] hover:text-[var(--app-ink)]"
                  @click="toggleSortDirection"
                >
                  <UIcon
                    :name="
                      sortDirection === 'asc' ? 'i-lucide-arrow-up-narrow-wide' : 'i-lucide-arrow-down-wide-narrow'
                    "
                    class="h-4 w-4"
                  />
                  {{ sortDirection === 'asc' ? 'Ascending' : 'Descending' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="border-b border-[var(--app-line)] bg-[var(--app-bg)]">
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Status
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Customer
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Date
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Credits
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Amount
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Stripe fees
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Net
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Funds availability
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Payment method
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Country
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  IP
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Device
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Details
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="transaction in displayedTransactions"
                :key="getTransactionKey(transaction)"
                class="border-b border-[var(--app-line)] transition-colors last:border-b-0 hover:bg-[var(--app-surface-2)]"
              >
                <td class="px-4 py-3">
                  <span
                    :class="[
                      'inline-flex items-center rounded px-2 py-0.5 text-xs font-medium',
                      getStatusClass(transaction.payment_info?.status || 'unknown'),
                    ]"
                  >
                    {{ getStatusLabel(transaction.payment_info?.status || 'unknown') }}
                  </span>
                </td>

                <td class="px-4 py-3">
                  <div class="flex flex-col">
                    <span class="text-sm font-medium text-[var(--app-ink)]">{{ transaction.user_name }}</span>
                    <span class="text-xs text-[var(--app-ink-soft)]">{{ transaction.user_email }}</span>
                  </div>
                </td>

                <td class="px-4 py-3 text-sm text-[var(--app-ink)]">
                  {{ formatDate(transaction.credits_available_date) }}
                </td>

                <td class="px-4 py-3 text-sm font-medium text-[var(--app-ink)]">
                  {{ transaction.credits_amount }}
                </td>

                <td class="px-4 py-3 text-sm font-medium text-[var(--app-ink)]">
                  <span v-if="transaction.payment_info"> €{{ formatCurrency(transaction.payment_info.amount) }} </span>
                  <span v-else class="text-[var(--app-ink-soft)]">N/A</span>
                </td>

                <td class="px-4 py-3 text-sm text-[var(--app-red)]">
                  <span v-if="transaction.payment_info?.application_fee_amount">
                    -€{{ formatCurrency(transaction.payment_info.application_fee_amount) }}
                  </span>
                  <span v-else class="text-[var(--app-ink-soft)]">N/A</span>
                </td>

                <td class="px-4 py-3 text-sm font-medium text-[var(--app-ink)]">
                  <span v-if="transaction.payment_info?.net_amount">
                    €{{ formatCurrency(transaction.payment_info.net_amount) }}
                  </span>
                  <span v-else class="text-[var(--app-ink-soft)]">N/A</span>
                </td>

                <td class="px-4 py-3 text-sm text-[var(--app-ink)]">
                  {{ formatAvailability(transaction.payment_info) }}
                </td>

                <td class="px-4 py-3 text-sm text-[var(--app-ink)]">
                  <div class="flex flex-col">
                    <span class="font-medium text-[var(--app-ink)]">
                      {{ transaction.payment_info?.payment_method_type?.toUpperCase() || 'N/A' }}
                    </span>
                    <span class="text-xs text-[var(--app-ink-soft)]">
                      {{ formatPaymentDetails(transaction.payment_info) }}
                    </span>
                  </div>
                </td>

                <td class="px-4 py-3 text-sm text-[var(--app-ink)]">
                  <span
                    v-if="transaction.payment_info?.customer_country"
                    :title="getCountryName(transaction.payment_info.customer_country)"
                    class="cursor-default text-lg"
                  >
                    {{ getCountryFlag(transaction.payment_info.customer_country) }}
                  </span>
                  <span v-else>N/A</span>
                </td>

                <td class="px-4 py-3 font-mono text-sm text-[var(--app-ink-soft)]">
                  {{ transaction.payment_info?.ip_address || 'N/A' }}
                </td>

                <td class="px-4 py-3 text-sm text-[var(--app-ink-soft)]">
                  {{ parseUserAgent(transaction.payment_info?.user_agent) }}
                </td>

                <td class="px-4 py-3">
                  <button
                    class="text-xs font-medium text-[var(--app-accent-ink)] transition-colors hover:text-[var(--app-accent-ink)]"
                    @click="toggleTransactionDetails(getTransactionKey(transaction))"
                  >
                    {{ expandedTransactions.has(getTransactionKey(transaction)) ? 'Hide' : 'Show' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-for="transaction in displayedTransactions" :key="`details-${getTransactionKey(transaction)}`">
          <div
            v-if="expandedTransactions.has(getTransactionKey(transaction))"
            class="border-t border-[var(--app-line)] bg-[var(--app-bg)] px-6 py-4"
          >
            <div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              <div v-if="transaction.payment_info">
                <h3 class="mb-3 text-xs font-semibold text-[var(--app-ink-soft)] uppercase">Payment information</h3>
                <div class="space-y-2">
                  <div class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Method:</span>
                    <span class="font-medium text-[var(--app-ink)]">
                      {{ transaction.payment_info.payment_method_type?.toUpperCase() || 'N/A' }}
                    </span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Currency:</span>
                    <span class="font-medium text-[var(--app-ink)] uppercase">
                      {{ transaction.payment_info.currency }}
                    </span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Payment date:</span>
                    <span class="font-medium text-[var(--app-ink)]">
                      {{ formatDateTime(transaction.payment_info.payment_date) }}
                    </span>
                  </div>
                  <div v-if="transaction.payment_info.customer_country" class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Country:</span>
                    <span class="font-medium text-[var(--app-ink)]">
                      {{ transaction.payment_info.customer_country }}
                    </span>
                  </div>
                  <div v-if="transaction.payment_info.ip_address" class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">IP:</span>
                    <span class="font-mono text-xs font-medium text-[var(--app-ink)]">
                      {{ transaction.payment_info.ip_address }}
                    </span>
                  </div>
                  <div v-if="transaction.payment_info.user_agent" class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Device:</span>
                    <span class="truncate text-xs font-medium text-[var(--app-ink)]">
                      {{ parseUserAgent(transaction.payment_info.user_agent) }}
                    </span>
                  </div>
                </div>
              </div>

              <div v-if="transaction.payment_info">
                <h3 class="mb-3 text-xs font-semibold text-[var(--app-ink-soft)] uppercase">Financial details</h3>
                <div class="space-y-2">
                  <div class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Payment amount:</span>
                    <span class="font-medium text-[var(--app-ink)]">
                      €{{ formatCurrency(transaction.payment_info.amount) }}
                    </span>
                  </div>
                  <div v-if="transaction.payment_info.amount_received" class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Amount received:</span>
                    <span class="font-medium text-[var(--app-ink)]">
                      €{{ formatCurrency(transaction.payment_info.amount_received) }}
                    </span>
                  </div>
                  <div v-if="transaction.payment_info.application_fee_amount" class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Stripe fees:</span>
                    <span class="font-medium text-[var(--app-red)]">
                      -€{{ formatCurrency(transaction.payment_info.application_fee_amount) }}
                    </span>
                  </div>
                  <div
                    v-if="transaction.payment_info.net_amount"
                    class="flex justify-between border-t border-[var(--app-line)] pt-2 text-sm"
                  >
                    <span class="font-medium text-[var(--app-ink-soft)]">Net amount:</span>
                    <span class="font-bold text-[var(--app-green)]">
                      €{{ formatCurrency(transaction.payment_info.net_amount) }}
                    </span>
                  </div>
                  <div v-if="transaction.payment_info.refund_amount" class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Refund:</span>
                    <span class="font-medium text-[var(--app-red)]">
                      -€{{ formatCurrency(transaction.payment_info.refund_amount) }}
                    </span>
                  </div>
                  <div v-if="transaction.payment_info.refund_date" class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Refund date:</span>
                    <span class="font-medium text-[var(--app-ink)]">
                      {{ formatDateTime(transaction.payment_info.refund_date) }}
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <h3 class="mb-3 text-xs font-semibold text-[var(--app-ink-soft)] uppercase">Transaction</h3>
                <div class="space-y-2">
                  <div class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Transaction ID:</span>
                    <span class="font-mono text-xs font-medium text-[var(--app-ink)]">
                      #{{ transaction.transaction_id }}
                    </span>
                  </div>
                  <div v-if="transaction.payment_info?.session_id" class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Session ID:</span>
                    <span class="truncate font-mono text-xs font-medium text-[var(--app-ink)]">
                      {{ transaction.payment_info.session_id }}
                    </span>
                  </div>
                  <div v-if="transaction.payment_info?.payment_intent_id" class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Payment Intent:</span>
                    <span class="truncate font-mono text-xs font-medium text-[var(--app-ink)]">
                      {{ transaction.payment_info.payment_intent_id }}
                    </span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Credits available at:</span>
                    <span class="font-medium text-[var(--app-ink)]">
                      {{ formatDateTime(transaction.credits_available_date) }}
                    </span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-[var(--app-ink-soft)]">Description:</span>
                    <span class="max-w-xs truncate text-right text-xs font-medium text-[var(--app-ink)]">
                      {{ transaction.description }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="displayedTransactions.length === 0" class="px-6 py-12 text-center">
          <UIcon name="i-lucide-receipt" class="mb-3 h-12 w-12 text-[var(--app-ink-soft)]" />
          <p class="text-[var(--app-ink-soft)]">No transaction matches your filters</p>
        </div>

        <div
          v-if="showPagination"
          class="flex flex-col gap-3 border-t border-[var(--app-line)] bg-[var(--app-bg)] px-6 py-4 md:flex-row md:items-center md:justify-between"
        >
          <div class="text-xs text-[var(--app-ink-soft)]">
            Showing
            <span class="font-medium text-[var(--app-ink)]">{{ pageStart }}-{{ pageEnd }}</span>
            of
            <span class="font-medium text-[var(--app-ink)]">{{ totalTransactions }}</span>
          </div>
          <div class="flex items-center gap-3">
            <div class="flex items-center gap-2 text-xs">
              <span class="text-[var(--app-ink-soft)]">Per page</span>
              <select
                v-model.number="pageSize"
                class="rounded border border-[var(--app-line)] bg-[var(--app-surface)] px-2 py-1 text-xs text-[var(--app-ink)]"
              >
                <option :value="10">10</option>
                <option :value="20">20</option>
                <option :value="50">50</option>
                <option :value="100">100</option>
              </select>
            </div>
            <div class="flex items-center gap-2">
              <button class="btn-secondary px-3 py-1 text-xs" :disabled="page <= 1" @click="goToPrevPage">
                Previous
              </button>
              <span class="text-xs text-[var(--app-ink-soft)]"
                >Page <span class="text-[var(--app-ink)]">{{ page }}</span> / {{ totalPages }}</span
              >
              <button class="btn-secondary px-3 py-1 text-xs" :disabled="page >= totalPages" @click="goToNextPage">
                Next
              </button>
            </div>
          </div>
        </div>
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
import type { AccountingResponse, CreditPurchaseTransaction } from '~/types'
import type { ComputedRef, Ref } from 'vue'
import { ref, computed, onMounted, watch } from 'vue'
import { AccountingService } from '~/services/accountingService'

/**
 * Dashboard accounting page - Admin financial data (admin only)
 */
definePageMeta({
  layout: 'dashboard',
  middleware: ['auth', 'admin'],
})

/**
 * Loading state
 */
const isLoading: Ref<boolean> = ref(true)

/**
 * Error state
 */
const error: Ref<string | null> = ref(null)

/**
 * Accounting data
 */
const accountingData: Ref<AccountingResponse | null> = ref(null)

/**
 * Expanded transactions
 */
const expandedTransactions: Ref<Set<string>> = ref(new Set())

/**
 * Raw transactions (from API)
 */
const rawTransactions = computed<CreditPurchaseTransaction[]>(() => {
  return accountingData.value?.transactions || []
})

/**
 * Filters & sorting state
 */
const searchQuery: Ref<string> = ref('')
const statusFilter: Ref<string> = ref('')
const sortKey: Ref<'date' | 'amount' | 'net' | 'fees' | 'credits' | 'country' | 'payment_method' | 'availability'> =
  ref('date')
const sortDirection: Ref<'asc' | 'desc'> = ref('desc')

/**
 * Status options for filter dropdown
 */
const statusOptions: ComputedRef<string[]> = computed(() => {
  const statuses = new Set<string>()
  rawTransactions.value.forEach((transaction) => {
    const status = transaction.payment_info?.status
    if (status) {
      statuses.add(status.toLowerCase())
    }
  })
  return Array.from(statuses).sort()
})

/**
 * Filter transactions by status and search query
 */
const filteredTransactions = computed<CreditPurchaseTransaction[]>(() => {
  const query = searchQuery.value.trim().toLowerCase()
  const status = statusFilter.value

  return rawTransactions.value.filter((transaction) => {
    const paymentInfo = transaction.payment_info
    const transactionStatus = paymentInfo?.status?.toLowerCase() || 'unknown'

    const matchesStatus = !status || transactionStatus === status
    if (!matchesStatus) {
      return false
    }

    if (!query) {
      return true
    }

    const haystack = [
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

/**
 * Sort filtered transactions
 */
const displayedTransactions = computed<CreditPurchaseTransaction[]>(() => {
  const direction = sortDirection.value === 'asc' ? 1 : -1

  const getAmount = (transaction: CreditPurchaseTransaction, key: 'amount' | 'net' | 'fees'): number => {
    const info = transaction.payment_info
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

  const items = [...filteredTransactions.value]
  items.sort((a, b) => {
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
        )
        break
      case 'payment_method':
        compare = formatPaymentDetails(a.payment_info).localeCompare(formatPaymentDetails(b.payment_info))
        break
      case 'availability':
        {
          const aTime = a.payment_info?.available_at
            ? new Date(a.payment_info.available_at).getTime()
            : Number.MAX_SAFE_INTEGER
          const bTime = b.payment_info?.available_at
            ? new Date(b.payment_info.available_at).getTime()
            : Number.MAX_SAFE_INTEGER
          compare = aTime - bTime
        }
        break
      default:
        compare = 0
    }

    if (compare < 0) return -1 * direction
    if (compare > 0) return 1 * direction
    return 0
  })

  return items
})

/**
 * Pagination state
 */
const page: Ref<number> = ref(1)
const pageSize: Ref<number> = ref(20)

/**
 * Totals and derived pagination values
 */
const totalTransactions: ComputedRef<number> = computed(() => accountingData.value?.summary?.total_transactions || 0)
const totalPages: ComputedRef<number> = computed(() => Math.max(1, Math.ceil(totalTransactions.value / pageSize.value)))
const showPagination: ComputedRef<boolean> = computed(() => totalTransactions.value > pageSize.value)
const pageStart: ComputedRef<number> = computed(() =>
  totalTransactions.value === 0 ? 0 : (page.value - 1) * pageSize.value + 1,
)
const pageEnd: ComputedRef<number> = computed(() => Math.min(page.value * pageSize.value, totalTransactions.value))

/**
 * Utility: coerce value to number
 */
const toNumeric = (value: number | string | null | undefined): number => {
  if (value === null || value === undefined) return 0
  if (typeof value === 'number') return value
  const parsed = parseFloat(value)
  return Number.isFinite(parsed) ? parsed : 0
}

/**
 * Format currency
 */
const formatCurrency = (amount: number | string | null | undefined): string => {
  const numericAmount = toNumeric(amount)
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numericAmount)
}

const regionDisplayNames = new Intl.DisplayNames(['en'], { type: 'region' })

const getCountryName = (code?: string | null): string => {
  if (!code) return 'Unknown country'
  try {
    return regionDisplayNames.of(code.toUpperCase()) || code.toUpperCase()
  } catch {
    return code.toUpperCase()
  }
}

const getCountryFlag = (code?: string | null): string => {
  if (!code) return '🏳️'
  const upper = code.toUpperCase()
  if (upper.length !== 2) return upper
  const OFFSET: number = 127397
  return String.fromCodePoint(...upper.split('').map((char) => char.charCodeAt(0) + OFFSET))
}

const formatPaymentDetails = (info?: CreditPurchaseTransaction['payment_info']): string => {
  if (!info) return 'N/A'
  const type = info.payment_method_type ? info.payment_method_type.toUpperCase() : ''
  const brand = info.payment_method_brand ? info.payment_method_brand.toUpperCase() : ''
  const last4 = info.payment_method_last4 ? `•••• ${info.payment_method_last4}` : ''
  const parts = [type, brand, last4].filter(Boolean)
  return parts.length ? parts.join(' ') : 'N/A'
}

/**
 * Format date
 */
const formatDate = (dateString: string): string => {
  const date: Date = new Date(dateString)
  const day: string = String(date.getDate()).padStart(2, '0')
  const month: string = String(date.getMonth() + 1).padStart(2, '0')
  const year = date.getFullYear()
  return `${day}/${month}/${year}`
}

/**
 * Format date and time
 */
const formatDateTime = (dateString: string): string => {
  const date: Date = new Date(dateString)
  const day: string = String(date.getDate()).padStart(2, '0')
  const month: string = String(date.getMonth() + 1).padStart(2, '0')
  const year = date.getFullYear()
  const hours: string = String(date.getHours()).padStart(2, '0')
  const minutes: string = String(date.getMinutes()).padStart(2, '0')
  return `${day}/${month}/${year} ${hours}:${minutes}`
}

/**
 * Get status class
 */
const getStatusClass = (status: string): string => {
  const normalized = status.toLowerCase()
  if (['paid', 'complete', 'succeeded', 'processing', 'requires_capture'].includes(normalized)) {
    return 'bg-[var(--app-green)]/20 text-[var(--app-green)] border border-[var(--app-green)]/30'
  }
  if (['pending', 'requires_confirmation', 'requires_action'].includes(normalized)) {
    return 'bg-[var(--app-accent-ink)]/20 text-[var(--app-accent-ink)] border border-[var(--app-accent-ink)]/30'
  }
  if (['failed', 'canceled', 'requires_payment_method', 'expired'].includes(normalized)) {
    return 'bg-[var(--app-red)]/20 text-[var(--app-red)] border border-[var(--app-red)]/30'
  }
  if (['refunded', 'partially_refunded'].includes(normalized)) {
    return 'bg-[var(--app-red)]/20 text-[var(--app-red)] border border-[var(--app-red)]/30'
  }
  return 'bg-[var(--app-ink-soft)]/20 text-[var(--app-ink-soft)] border border-[var(--app-ink-soft)]/30'
}

/**
 * Get status label
 */
const getStatusLabel = (status: string): string => {
  const labelMap: Record<string, string> = {
    paid: 'Paid',
    complete: 'Complete',
    succeeded: 'Succeeded',
    processing: 'Processing',
    requires_capture: 'Requires capture',
    pending: 'Pending',
    requires_confirmation: 'Needs confirmation',
    requires_action: 'Needs action',
    requires_payment_method: 'Needs payment method',
    failed: 'Failed',
    canceled: 'Canceled',
    unpaid: 'Unpaid',
    open: 'Open',
    expired: 'Expired',
    refunded: 'Refunded',
    partially_refunded: 'Partially refunded',
  }
  return labelMap[status.toLowerCase()] || status
}

const formatAvailability = (info?: CreditPurchaseTransaction['payment_info']): string => {
  if (!info) return 'N/A'
  if (info.available_at) {
    return formatDateTime(info.available_at)
  }
  const status = info.status?.toLowerCase() || 'unknown'
  if (['succeeded', 'paid', 'complete', 'processing', 'requires_capture', 'pending'].includes(status)) {
    return 'Pending'
  }
  if (['requires_confirmation', 'requires_action'].includes(status)) {
    return 'Waiting for customer'
  }
  if (['requires_payment_method', 'unpaid', 'failed', 'canceled', 'expired'].includes(status)) {
    return 'N/A'
  }
  return 'N/A'
}

/**
 * Parse user agent to get device/browser info
 */
const parseUserAgent = (userAgent: string | null | undefined): string => {
  if (!userAgent) return 'N/A'

  // Simple parsing for common browsers/devices
  if (userAgent.includes('Mobile')) {
    return 'Mobile'
  }
  if (userAgent.includes('Tablet')) {
    return 'Tablet'
  }
  if (userAgent.includes('Chrome')) {
    return 'Chrome'
  }
  if (userAgent.includes('Firefox')) {
    return 'Firefox'
  }
  if (userAgent.includes('Safari')) {
    return 'Safari'
  }
  if (userAgent.includes('Edge')) {
    return 'Edge'
  }

  return 'Browser'
}

/**
 * Toggle transaction details
 */
const getTransactionKey = (transaction: CreditPurchaseTransaction): string => {
  return (
    transaction.payment_info?.payment_intent_id ||
    transaction.payment_info?.session_id ||
    `tx-${transaction.transaction_id}-${transaction.credits_available_date}`
  )
}

const toggleTransactionDetails = (transactionKey: string): void => {
  if (expandedTransactions.value.has(transactionKey)) {
    expandedTransactions.value.delete(transactionKey)
  } else {
    expandedTransactions.value.add(transactionKey)
  }
}

/**
 * Toggle sort direction
 */
const toggleSortDirection = (): void => {
  sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
}

/**
 * Load accounting data
 */
const loadAccountingData = async (): Promise<void> => {
  try {
    isLoading.value = true
    error.value = null
    const skip = (page.value - 1) * pageSize.value
    const limit = pageSize.value
    accountingData.value = await AccountingService.getAccountingData(skip, limit)
    expandedTransactions.value.clear()
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Failed to load accounting data'
    error.value = errorMessage
    console.error('Failed to load accounting data:', err)
  } finally {
    isLoading.value = false
  }
}

/**
 * Pagination handlers
 */
const goToPrevPage = (): void => {
  if (page.value > 1) {
    page.value -= 1
  }
}

const goToNextPage = (): void => {
  if (page.value < totalPages.value) {
    page.value += 1
  }
}

/**
 * Initialize component
 */
onMounted(async () => {
  await loadAccountingData()
})

/**
 * React to pagination changes
 */
watch([page, pageSize], async () => {
  // Reset to first page when page size changes beyond bounds
  if (page.value > totalPages.value) {
    page.value = 1
  }
  await loadAccountingData()
})

watch([rawTransactions, searchQuery, statusFilter, sortKey, sortDirection], () => {
  expandedTransactions.value.clear()
})

watch([searchQuery, statusFilter], () => {
  page.value = 1
})
</script>
