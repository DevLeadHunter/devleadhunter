<template>
  <div class="space-y-1">
    <template v-for="(row, index) in rows" :key="row.label">
      <!-- Conversion connector between stages -->
      <div v-if="index > 0" class="flex items-center gap-2 py-1 pl-1">
        <i class="fa-solid fa-arrow-down-long text-[10px] text-[var(--app-ink-soft)]"></i>
        <span
          class="rounded px-1.5 py-0.5 text-[11px] font-semibold tabular-nums"
          :style="{ color: row.conversionColor, backgroundColor: hexAlpha(row.conversionColor, 0.1) }"
        >
          {{ row.conversionPct }}%
        </span>
        <span class="text-[11px] text-[var(--app-ink-soft)]">
          de conversion depuis « {{ rows[index - 1]?.label }} »
        </span>
      </div>

      <!-- Stage bar -->
      <div class="group flex items-center gap-3">
        <div class="w-32 flex-shrink-0 text-right">
          <p class="truncate text-xs font-medium text-[var(--app-ink)]">{{ row.label }}</p>
        </div>
        <div class="relative h-9 flex-1 overflow-hidden rounded-md bg-[var(--app-surface)]">
          <div
            class="absolute inset-y-0 left-0 rounded-md transition-all duration-500 ease-out"
            :style="{
              width: `${row.widthPct}%`,
              background: `linear-gradient(90deg, ${hexAlpha(row.hex, 0.85)}, ${hexAlpha(row.hex, 0.5)})`,
              boxShadow: `inset 0 0 0 1px ${hexAlpha(row.hex, 0.5)}`,
            }"
          />
          <div class="absolute inset-0 flex items-center justify-between px-3">
            <span class="text-sm font-bold text-[var(--app-ink)] tabular-nums">{{ formatNumber(row.value) }}</span>
            <span class="text-[11px] font-medium text-[var(--app-ink-soft)] tabular-nums"
              >{{ row.sharePct }}% du sommet</span
            >
          </div>
        </div>
      </div>
    </template>

    <p v-if="!rows.length" class="text-muted py-6 text-center text-sm">Pas encore de données de conversion.</p>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import { computed } from 'vue'
import type { DashboardConversionFunnelProps, FunnelStage } from '~/types/DashboardConversionFunnel'
import { accentHex, hexAlpha } from '~/utils/dashboardTheme'

/**
 * Horizontal conversion funnel: each stage is a proportional bar with the
 * conversion rate from the previous stage shown between rows.
 */
const props: DashboardConversionFunnelProps = defineProps({
  stages: {
    type: Array as () => FunnelStage[],
    required: true,
  },
})

/** A computed funnel row enriched with widths, colors and conversion rates. */
interface FunnelRow {
  label: string
  value: number
  hex: string
  widthPct: number
  sharePct: number
  conversionPct: number
  conversionColor: string
}

/**
 * Format an integer with French thousands separators.
 * @param n - Number to format.
 * @returns Locale-formatted string.
 */
function formatNumber(n: number): string {
  return n.toLocaleString('fr-FR')
}

/** Funnel rows with derived geometry and conversion percentages. */
const rows: ComputedRef<FunnelRow[]> = computed((): FunnelRow[] => {
  const top: number = props.stages[0]?.value ?? 0
  const maxValue: number = Math.max(...props.stages.map((s: FunnelStage): number => s.value), 1)
  return props.stages.map((stage: FunnelStage, index: number): FunnelRow => {
    const prev: number = index > 0 ? (props.stages[index - 1]?.value ?? 0) : stage.value
    const conversionPct: number = prev > 0 ? Math.round((stage.value / prev) * 100) : 0
    const sharePct: number = top > 0 ? Math.round((stage.value / top) * 100) : 0
    const conversionColor: string =
      conversionPct >= 60 ? 'var(--app-green)' : conversionPct >= 25 ? 'var(--app-accent)' : 'var(--app-red)'
    return {
      label: stage.label,
      value: stage.value,
      hex: accentHex(stage.accent ?? 'blue'),
      widthPct: Math.max((stage.value / maxValue) * 100, stage.value > 0 ? 4 : 1.5),
      sharePct,
      conversionPct,
      conversionColor,
    }
  })
})
</script>
