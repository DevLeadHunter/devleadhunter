<template>
  <div>
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-[var(--app-ink)]">Mes crédits</h1>
      <NuxtLink
        to="/dashboard/buy-credits"
        class="flex items-center gap-1.5 text-sm text-[var(--app-ink)] transition-colors hover:text-[var(--app-ink-soft)]"
      >
        Voir les tarifs
        <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
      </NuxtLink>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="space-y-6">
      <div class="card">
        <div class="animate-pulse space-y-4">
          <div class="h-6 w-1/4 rounded bg-[var(--app-surface-2)]"></div>
          <div class="h-32 rounded bg-[var(--app-surface-2)]"></div>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div v-else class="space-y-6">
      <!-- Credit Usage Progress Bar -->
      <div class="card">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-[var(--app-ink)]">Consommation de crédits</h2>
          <NuxtLink to="/dashboard/buy-credits" class="btn-primary h-auto px-4 py-2 text-xs">
            Acheter des crédits
          </NuxtLink>
        </div>

        <p class="mb-4 text-xs text-[var(--app-ink-soft)]">Mis à jour le {{ lastUpdated }}</p>

        <!-- Progress Bar Container -->
        <div ref="progressBarRef" class="relative">
          <div
            class="relative h-8 cursor-pointer overflow-hidden rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]"
            @mouseenter="handleTooltipEnter"
            @mouseleave="handleTooltipLeave"
          >
            <!-- Credits Used -->
            <div
              :style="{ width: `${usedPercentage}%` }"
              class="absolute top-0 left-0 h-full bg-[var(--app-accent-ink)] transition-all duration-300"
            ></div>

            <!-- Credits Remaining -->
            <div
              :style="{ width: `${remainingPercentage}%`, left: `${usedPercentage}%` }"
              class="absolute top-0 h-full bg-[var(--app-surface-2)] transition-all duration-300"
            ></div>

            <!-- Labels on Progress Bar -->
            <div class="relative flex h-full items-center px-3 text-xs font-medium">
              <span class="text-[var(--app-ink)]">{{ creditsUsed }}</span>
              <span class="ml-auto text-[var(--app-ink)]">
                {{ creditsRemaining === Infinity || creditsRemaining === -1 ? '∞' : creditsRemaining }}
              </span>
            </div>
          </div>

          <!-- Tooltip Qonto Style - Using Teleport to render in body -->
          <Teleport to="body">
            <div
              v-if="showProgressTooltip && usedPercentage > 0 && tooltipPosition"
              :style="{
                position: 'fixed',
                left: `${tooltipPosition.x}px`,
                top: `${tooltipPosition.y}px`,
                transform: 'translateX(-50%)',
              }"
              class="pointer-events-none z-[100] w-72 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-4 shadow-lg"
              style="box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3)"
            >
              <!-- Header -->
              <div class="mb-3 flex items-center justify-between border-b border-[var(--app-line)] pb-2">
                <span class="text-sm font-medium text-[var(--app-ink)]">Consommation</span>
                <span class="text-xs text-[var(--app-ink-soft)]">État actuel</span>
              </div>

              <!-- Data Rows -->
              <div class="mb-2.5 space-y-2.5">
                <!-- Credits Used -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <div class="h-3 w-3 flex-shrink-0 rounded bg-[var(--app-accent-ink)]"></div>
                    <span class="text-sm text-[var(--app-ink)]">Crédits utilisés</span>
                  </div>
                  <span class="text-sm font-medium text-[var(--app-ink)]">{{ creditsUsed }}</span>
                </div>

                <!-- Credits Remaining -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <div class="h-3 w-3 flex-shrink-0 rounded bg-[var(--app-surface-2)]"></div>
                    <span class="text-sm text-[var(--app-ink-soft)]">Crédits restants</span>
                  </div>
                  <span class="text-sm font-medium text-[var(--app-ink-soft)]">{{ creditsRemaining }}</span>
                </div>
              </div>

              <!-- Separator -->
              <div class="my-2.5 border-t border-[var(--app-line)]"></div>

              <!-- Total Variation -->
              <div class="flex items-center justify-between">
                <span class="text-sm text-[var(--app-ink-soft)]">Total des crédits</span>
                <span class="text-sm font-medium text-[var(--app-green)]">{{ totalCredits }}</span>
              </div>
            </div>
          </Teleport>

          <!-- Alternative tooltip when no credits used - Using Teleport -->
          <Teleport to="body">
            <div
              v-if="showProgressTooltip && usedPercentage === 0 && tooltipPosition"
              :style="{
                position: 'fixed',
                left: `${tooltipPosition.x}px`,
                top: `${tooltipPosition.y}px`,
                transform: 'translateX(-50%)',
              }"
              class="pointer-events-none z-[100] w-72 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-4 shadow-lg"
              style="box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3)"
            >
              <!-- Header -->
              <div class="mb-3 flex items-center justify-between border-b border-[var(--app-line)] pb-2">
                <span class="text-sm font-medium text-[var(--app-ink)]">Consommation</span>
                <span class="text-xs text-[var(--app-ink-soft)]">État actuel</span>
              </div>

              <!-- Data Rows -->
              <div class="mb-2.5 space-y-2.5">
                <!-- Credits Remaining -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <div class="h-3 w-3 flex-shrink-0 rounded bg-[var(--app-surface-2)]"></div>
                    <span class="text-sm text-[var(--app-ink-soft)]">Crédits restants</span>
                  </div>
                  <span class="text-sm font-medium text-[var(--app-ink-soft)]">{{ creditsRemaining }}</span>
                </div>

                <!-- Credits Used -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <div class="h-3 w-3 flex-shrink-0 rounded bg-[var(--app-accent-ink)] opacity-50"></div>
                    <span class="text-sm text-[var(--app-ink-soft)]">Crédits utilisés</span>
                  </div>
                  <span class="text-sm font-medium text-[var(--app-ink-soft)]">0</span>
                </div>
              </div>

              <!-- Separator -->
              <div class="my-2.5 border-t border-[var(--app-line)]"></div>

              <!-- Total Variation -->
              <div class="flex items-center justify-between">
                <span class="text-sm text-[var(--app-ink-soft)]">Total des crédits</span>
                <span class="text-sm font-medium text-[var(--app-green)]">{{ totalCredits }}</span>
              </div>
            </div>
          </Teleport>
        </div>
      </div>

      <!-- Daily Usage Chart -->
      <div class="card">
        <h2 class="mb-4 text-lg font-semibold text-[var(--app-ink)]">Consommation quotidienne</h2>
        <div v-if="chartData && chartData.labels && chartData.labels.length > 0" class="h-64">
          <canvas ref="chartCanvasRef"></canvas>
        </div>
        <div v-else class="flex h-64 items-center justify-center text-[var(--app-ink-soft)]">
          <p>Aucune donnée de consommation</p>
        </div>
      </div>

      <!-- Recent Credit Usage List -->
      <div class="card">
        <h2 class="mb-4 text-lg font-semibold text-[var(--app-ink)]">Activité récente</h2>
        <div v-if="recentTransactions.length > 0" class="space-y-0">
          <div
            v-for="transaction in recentTransactions"
            :key="transaction.id"
            class="flex items-center justify-between border-b border-[var(--app-line)] py-3 last:border-b-0"
          >
            <div class="flex-1">
              <p class="text-sm font-medium text-[var(--app-ink)]">
                {{ formatTransactionDescription(transaction) }}
              </p>
              <p class="mt-1 text-xs text-[var(--app-ink-soft)]">
                {{ formatTransactionDate(transaction.created_at) }}
              </p>
            </div>
            <div class="text-right">
              <p
                :class="[
                  'text-sm font-medium',
                  transaction.amount < 0 ? 'text-[var(--app-red)]' : 'text-[var(--app-green)]',
                ]"
              >
                {{ transaction.amount < 0 ? '-' : '+' }}{{ Math.abs(transaction.amount) }} crédits
              </p>
            </div>
          </div>
        </div>
        <div v-else class="py-12 text-center text-[var(--app-ink-soft)]">
          <p class="text-sm">Aucune transaction pour l'instant</p>
        </div>
      </div>

      <!-- CTA Section -->
      <div class="card border-[var(--app-line)] bg-gradient-to-r from-[var(--app-surface)] to-[var(--app-bg)]">
        <div class="flex flex-col items-center justify-between gap-4 md:flex-row">
          <div>
            <h3 class="mb-2 text-lg font-semibold text-[var(--app-ink)]">Besoin de plus de crédits ?</h3>
            <p class="text-sm text-[var(--app-ink-soft)]">
              Rechargez pour continuer à chercher des prospects et envoyer vos campagnes.
            </p>
          </div>
          <NuxtLink to="/dashboard/buy-credits" class="btn-primary whitespace-nowrap"> Acheter des crédits </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CreditTransaction } from '~/types'
import type { Ref } from 'vue'
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { Chart, type ChartConfiguration, type TooltipItem } from 'chart.js'
import * as creditTransactionService from '~/services/creditTransactionService'
import { useUserStore } from '~/stores/user'

/**
 * Dashboard credits page - Display credit usage, history and statistics
 */
definePageMeta({
  layout: 'dashboard',
  middleware: ['auth', 'admin'],
})

/**
 * Chart instance reference
 */
let chartInstance: Chart | null = null
const chartCanvasRef: Ref<HTMLCanvasElement | null> = ref(null)

/**
 * Progress bar container reference
 */
const progressBarRef: Ref<HTMLElement | null> = ref(null)

/**
 * Tooltip position state
 */
const tooltipPosition: Ref<{ x: number; y: number } | null> = ref(null)

/**
 * User store instance
 */
const userStore = useUserStore()

/**
 * Loading state
 */
const isLoading: Ref<boolean> = ref(true)

/**
 * Transactions state
 */
const transactions: Ref<CreditTransaction[]> = ref([])

/**
 * Progress tooltip visibility
 */
const showProgressTooltip: Ref<boolean> = ref(false)

/**
 * Update tooltip position based on progress bar position
 */
const updateTooltipPosition = (): void => {
  if (!progressBarRef.value || typeof window === 'undefined') {
    tooltipPosition.value = null
    return
  }

  const progressBar = progressBarRef.value.querySelector('.cursor-pointer')
  if (!progressBar) return

  const progressRect = progressBar.getBoundingClientRect()
  const tooltipWidth = 288 // w-72 = 18rem = 288px
  const margin = 8 // mt-2 = 8px

  // Calculate position based on used percentage
  // usedPercentage is 0-100, so divide by 100 to get fraction
  let tooltipX: number

  if (usedPercentage.value > 0) {
    // Position at the center of the blue bar (used portion)
    // Convert percentage to fraction (0-1) and calculate center of used portion
    const usedFraction = usedPercentage.value / 100
    tooltipX = progressRect.left + (progressRect.width * usedFraction) / 2
  } else {
    // Position at the center of the entire progress bar
    tooltipX = progressRect.left + progressRect.width / 2
  }

  // Ensure tooltip doesn't go off-screen
  // Check left boundary
  if (tooltipX - tooltipWidth / 2 < 0) {
    tooltipX = tooltipWidth / 2 + 16 // 16px padding from edge
  }

  // Check right boundary
  if (tooltipX + tooltipWidth / 2 > window.innerWidth) {
    tooltipX = window.innerWidth - tooltipWidth / 2 - 16 // 16px padding from edge
  }

  const tooltipY = progressRect.bottom + margin

  tooltipPosition.value = { x: tooltipX, y: tooltipY }
}

/**
 * Handle tooltip enter
 */
const handleTooltipEnter = (): void => {
  showProgressTooltip.value = true
  nextTick(() => {
    // Use requestAnimationFrame to ensure DOM is fully updated
    requestAnimationFrame(() => {
      updateTooltipPosition()
      window.addEventListener('scroll', updateTooltipPosition, true)
      window.addEventListener('resize', updateTooltipPosition)
    })
  })
}

/**
 * Handle tooltip leave
 */
const handleTooltipLeave = (): void => {
  showProgressTooltip.value = false
  tooltipPosition.value = null
  window.removeEventListener('scroll', updateTooltipPosition, true)
  window.removeEventListener('resize', updateTooltipPosition)
}

/**
 * Total credits (current balance + used)
 */
const totalCredits = computed(() => {
  const balance = creditsRemaining.value
  const used = creditsUsed.value

  if (balance === Infinity || balance === -1) {
    return balance
  }

  return balance + used
})

/**
 * Credits used (sum of negative amounts)
 */
const creditsUsed = computed(() => {
  const used = Math.abs(transactions.value.filter((t) => t.amount < 0).reduce((sum, t) => sum + t.amount, 0))
  return used
})

/**
 * Credits remaining
 */
const creditsRemaining = computed(() => {
  const balance = userStore.user?.credits_available ?? userStore.user?.credit_balance
  if (balance === null || balance === undefined) {
    return 0
  }
  if (balance === -1) {
    return Infinity
  }
  return balance
})

/**
 * Used percentage
 */
const usedPercentage = computed(() => {
  const total = totalCredits.value
  if (total === 0 || total === Infinity || total === -1) return 0
  const used = creditsUsed.value
  if (used === 0) return 0
  return Math.min((used / total) * 100, 100)
})

/**
 * Remaining percentage
 */
const remainingPercentage = computed(() => {
  const total = totalCredits.value
  if (total === Infinity || total === -1) return 100
  return Math.max(100 - usedPercentage.value, 0)
})

/**
 * Last updated timestamp
 */
const lastUpdated = computed(() => {
  if (transactions.value.length === 0) {
    return new Date().toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  const lastTransaction = transactions.value[0]
  return new Date(lastTransaction.created_at).toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
})

/**
 * Recent transactions (last 10)
 */
const recentTransactions = computed(() => {
  return transactions.value.slice(0, 10)
})

/**
 * Chart data - Group transactions by day
 */
const chartData = computed(() => {
  if (transactions.value.length === 0) return null

  // Group by date and sum negative amounts (usage)
  const dailyUsage: Record<string, { count: number; date: Date }> = {}

  transactions.value
    .filter((t) => t.amount < 0) // Only usage transactions
    .forEach((transaction) => {
      const dateObj = new Date(transaction.created_at)
      const dateKey = dateObj.toLocaleDateString('fr-FR', {
        month: 'short',
        day: 'numeric',
      })

      if (!dailyUsage[dateKey]) {
        dailyUsage[dateKey] = { count: 0, date: dateObj }
      }
      dailyUsage[dateKey].count += Math.abs(transaction.amount)
    })

  // Sort by date (chronological order)
  const sortedEntries = Object.entries(dailyUsage)
    .sort(([, a], [, b]) => a.date.getTime() - b.date.getTime())
    .slice(-30) // Last 30 days

  const labels = sortedEntries.map(([dateKey]) => dateKey)
  const data = sortedEntries.map(([, { count }]) => count)

  return {
    labels,
    datasets: [
      {
        label: 'Crédits utilisés',
        data,
        backgroundColor: '#8d7bb8',
        borderRadius: 4,
        maxBarThickness: 50,
      },
    ],
  }
})

/**
 * Chart options
 */
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 26, 0.95)',
      titleColor: '#f9f9f9',
      titleFont: {
        size: 13,
        weight: '500',
      },
      bodyColor: '#8f887b',
      bodyFont: {
        size: 12,
        weight: '400',
      },
      borderColor: 'rgba(140, 132, 118, 0.35)',
      borderWidth: 1,
      borderRadius: 8,
      padding: 16,
      displayColors: true,
      boxPadding: 6,
      boxWidth: 12,
      boxHeight: 12,
      usePointStyle: true,
      shadowOffsetX: 0,
      shadowOffsetY: 4,
      shadowBlur: 12,
      shadowColor: 'rgba(0, 0, 0, 0.3)',
      callbacks: {
        /**
         * Format the chart tooltip title from the hovered bar label.
         */
        title: function (context: TooltipItem<'bar'>[]) {
          return context[0]?.label ?? ''
        },
        /**
         * Format the chart tooltip value as a credits count.
         */
        label: function (context: TooltipItem<'bar'>) {
          return `${context.parsed.y} crédits utilisés`
        },
      },
    },
    interaction: {
      intersect: false,
      mode: 'index',
    },
  },
  scales: {
    x: {
      grid: {
        color: 'rgba(140, 132, 118, 0.22)',
        display: false,
      },
      ticks: {
        color: '#8f887b',
        font: {
          size: 11,
        },
      },
    },
    y: {
      grid: {
        color: 'rgba(140, 132, 118, 0.22)',
      },
      ticks: {
        color: '#8f887b',
        font: {
          size: 11,
        },
        /**
         * Format Y-axis tick labels for the credits chart.
         */
        callback: function (value: string | number) {
          return value
        },
      },
      beginAtZero: true,
    },
  },
}

/**
 * Format transaction description
 */
const formatTransactionDescription = (transaction: CreditTransaction): string => {
  if (transaction.transaction_type === 'USAGE') {
    // Try to extract action from description
    const desc = transaction.description.toLowerCase()
    if (desc.includes('search')) return 'Recherche de prospects'
    if (desc.includes('email') || desc.includes('campaign')) return 'Campagne email'
    if (desc.includes('prospect')) return 'Prospect trouvé'
    return transaction.description
  }
  if (transaction.transaction_type === 'PURCHASE') {
    return 'Achat de crédits'
  }
  if (transaction.transaction_type === 'FREE_GIFT') {
    return 'Crédits offerts'
  }
  if (transaction.transaction_type === 'REFUND') {
    return 'Remboursement de crédits'
  }
  return transaction.description
}

/**
 * Format transaction date to relative time
 */
const formatTransactionDate = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    return "Aujourd'hui"
  } else if (diffDays === 1) {
    return 'Hier'
  } else if (diffDays < 7) {
    return `il y a ${diffDays} jours`
  } else if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7)
    return `il y a ${weeks} semaine${weeks > 1 ? 's' : ''}`
  } else {
    return date.toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }
}

/**
 * Load credit transactions
 */
const loadTransactions = async (): Promise<void> => {
  try {
    isLoading.value = true
    const data = await creditTransactionService.getMyTransactions(0, 1000)
    transactions.value = data
  } catch (error) {
    console.error('Failed to load transactions:', error)
    transactions.value = []
  } finally {
    isLoading.value = false
  }
}

/**
 * Initialize chart
 */
const initChart = (): void => {
  if (typeof window === 'undefined' || !chartCanvasRef.value || !chartData.value) return

  // Destroy existing chart if it exists
  if (chartInstance) {
    try {
      chartInstance.destroy()
    } catch (error) {
      console.warn('Error destroying chart:', error)
    }
    chartInstance = null
  }

  const config: ChartConfiguration<'bar'> = {
    type: 'bar',
    data: chartData.value,
    options: chartOptions,
  }

  try {
    chartInstance = new Chart(chartCanvasRef.value, config)
  } catch (error) {
    console.error('Error creating chart:', error)
  }
}

/**
 * Watch for chart data changes
 */
watch(
  chartData,
  async () => {
    await nextTick()
    initChart()
  },
  { deep: true },
)

/**
 * Initialize component
 */
onMounted(async () => {
  await loadTransactions()
  // Wait for next tick to ensure DOM is ready
  await nextTick()
  await new Promise((resolve) => setTimeout(resolve, 100))
  initChart()
})

/**
 * Cleanup chart on unmount
 */
onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
  // Cleanup tooltip event listeners
  window.removeEventListener('scroll', updateTooltipPosition, true)
  window.removeEventListener('resize', updateTooltipPosition)
})
</script>
