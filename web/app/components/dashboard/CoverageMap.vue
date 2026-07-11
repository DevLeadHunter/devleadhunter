<template>
  <div class="space-y-4">
    <!-- Scope selector (organization only) + headline -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <p class="text-muted max-w-md text-xs leading-relaxed">
        Votre territoire de prospection. Chaque ville prospectée colore sa région — l'objectif est d'en verdir un
        maximum.
      </p>
      <div v-if="members.length > 0" class="shrink-0">
        <select v-model="scope" class="input-field h-9 w-full text-xs sm:w-52" @change="onScopeChange">
          <option value="me">Mes prospects</option>
          <option value="org">Toute l'organisation</option>
          <option v-for="member in members" :key="member.user_id" :value="`member:${member.user_id}`">
            {{ member.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- Gamified counters -->
    <div class="grid grid-cols-3 gap-3">
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5 text-center">
        <p class="text-xl font-bold text-[var(--app-ink)] tabular-nums">{{ coveredCityCount }}</p>
        <p class="text-muted text-[10px] tracking-wide uppercase">Villes</p>
      </div>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5 text-center">
        <p class="text-xl font-bold text-[var(--app-green)] tabular-nums">
          {{ deptSet.size }}<span class="text-[var(--app-faint)]"> / 96</span>
        </p>
        <p class="text-muted text-[10px] tracking-wide uppercase">Départements</p>
      </div>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5 text-center">
        <p class="text-xl font-bold text-[var(--app-ink)] tabular-nums">
          {{ coveredRegionCount }}<span class="text-[var(--app-faint)]"> / 13</span>
        </p>
        <p class="text-muted text-[10px] tracking-wide uppercase">Régions</p>
      </div>
    </div>

    <!-- Territory progress -->
    <div>
      <div class="mb-1 flex items-center justify-between text-[11px]">
        <span class="text-muted">Territoire couvert</span>
        <span class="font-semibold text-[var(--app-green)] tabular-nums">{{ territoryPercent }} %</span>
      </div>
      <div class="h-1.5 overflow-hidden rounded-full bg-[var(--app-surface-2)]">
        <div
          class="h-full rounded-full bg-[var(--app-green)] transition-all duration-700"
          :style="{ width: `${territoryPercent}%` }"
        ></div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex h-72 items-center justify-center">
      <UIcon name="i-lucide-loader-circle" class="h-7 w-7 animate-spin text-[var(--app-ink-soft)]" />
    </div>

    <!-- Empty -->
    <div
      v-else-if="coverage && coverage.cities.length === 0"
      class="flex h-72 flex-col items-center justify-center gap-3 text-center"
    >
      <UIcon name="i-lucide-map" class="h-8 w-8 text-[var(--app-faint)]" />
      <p class="text-muted max-w-xs text-sm leading-relaxed">
        Aucune ville prospectée pour l'instant. Lancez une recherche pour commencer à colorer la carte.
      </p>
      <NuxtLink to="/dashboard/search-prospects" class="btn-secondary text-xs">Trouver des prospects</NuxtLink>
    </div>

    <!-- Map -->
    <div v-else-if="regions.length > 0" ref="mapWrap" class="relative">
      <svg :viewBox="`0 0 ${VB_W} ${VB_H}`" class="h-auto w-full" role="img" aria-label="Carte de couverture">
        <!-- Regions choropleth -->
        <path
          v-for="region in regionPaths"
          :key="region.code"
          :d="region.d"
          :fill="region.fill"
          stroke="var(--app-surface)"
          stroke-width="1"
          class="cursor-default transition-[fill] duration-300"
          @mousemove="showRegionTip($event, region)"
          @mouseleave="hideTip"
        />
        <!-- City dots -->
        <circle
          v-for="(dot, index) in dots"
          :key="index"
          :cx="dot.x"
          :cy="dot.y"
          :r="dot.r"
          fill="var(--app-ink)"
          fill-opacity="0.82"
          stroke="var(--app-surface)"
          stroke-width="1"
          class="cursor-pointer"
          @mousemove="showCityTip($event, dot)"
          @mouseleave="hideTip"
        />
      </svg>

      <!-- Tooltip -->
      <div
        v-if="tip.show"
        class="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-2.5 py-1.5 text-xs shadow-lg"
        :style="{ left: `${tip.x}px`, top: `${tip.y - 8}px` }"
      >
        <p class="font-semibold text-[var(--app-ink)]">{{ tip.title }}</p>
        <p class="text-muted tabular-nums">{{ tip.sub }}</p>
      </div>

      <!-- Legend -->
      <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5">
        <span class="text-muted text-[10px] tracking-wide uppercase">Intensité</span>
        <span v-for="bucket in LEGEND" :key="bucket.label" class="flex items-center gap-1.5">
          <span class="h-3 w-3 rounded-sm" :style="{ backgroundColor: bucket.color }"></span>
          <span class="text-[11px] text-[var(--app-ink-soft)]">{{ bucket.label }}</span>
        </span>
      </div>
    </div>

    <!-- Map unavailable (geo API down) — fall back to a ranked city list -->
    <div v-else class="space-y-2">
      <p class="text-muted text-xs">Carte indisponible — voici vos villes les plus prospectées :</p>
      <ul class="divide-y divide-[var(--app-line-soft)]">
        <li
          v-for="city in (coverage?.cities ?? []).slice(0, 12)"
          :key="city.city"
          class="flex items-center justify-between py-1.5 text-sm"
        >
          <span class="text-[var(--app-ink)]">{{ city.city }}</span>
          <span class="text-muted tabular-nums">{{ city.count }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import type { CoverageMember, CoverageResponse } from '~/services/dashboardService'
import { getCoverage } from '~/services/dashboardService'
import type { CityGeo, FranceRegion } from '~/composables/useFranceGeo'
import { geocodeCities, loadFranceRegions, lookupCity } from '~/composables/useFranceGeo'

const VB_W = 640
const VB_H = 620
const PAD = 18

/** A city dot projected onto the SVG. */
interface CityDot {
  x: number
  y: number
  r: number
  city: string
  count: number
}

/** A region path ready to render. */
interface RegionPath {
  code: string
  nom: string
  d: string
  fill: string
  total: number
}

/** Legend buckets (must match `fillForRatio`). */
const LEGEND: ReadonlyArray<{ label: string; color: string }> = [
  { label: 'Aucune', color: 'var(--app-surface-2)' },
  { label: 'Faible', color: 'color-mix(in srgb, var(--app-accent) 45%, var(--app-surface))' },
  { label: 'Moyenne', color: 'color-mix(in srgb, var(--app-accent) 80%, transparent)' },
  { label: 'Bonne', color: 'color-mix(in srgb, var(--app-green) 60%, var(--app-surface))' },
  { label: 'Forte', color: 'var(--app-green)' },
]

const isLoading: Ref<boolean> = ref<boolean>(true)
const scope: Ref<string> = ref<string>('me')
const coverage: Ref<CoverageResponse | null> = ref<CoverageResponse | null>(null)
const members: Ref<CoverageMember[]> = ref<CoverageMember[]>([])
const regions: Ref<FranceRegion[]> = ref<FranceRegion[]>([])
const cityGeo: Ref<Record<string, CityGeo | null>> = ref<Record<string, CityGeo | null>>({})

const tip: Ref<{ show: boolean; x: number; y: number; title: string; sub: string }> = ref({
  show: false,
  x: 0,
  y: 0,
  title: '',
  sub: '',
})
const mapWrap: Ref<HTMLElement | null> = ref<HTMLElement | null>(null)

// ─── Projection (built from the regions' bounding box) ─────────────────────────

/** Projects [lng, lat] → [x, y] in the SVG viewBox, or null before regions load. */
const project: ComputedRef<((lng: number, lat: number) => [number, number]) | null> = computed(() => {
  if (regions.value.length === 0) return null
  let minLng = Infinity
  let maxLng = -Infinity
  let minLat = Infinity
  let maxLat = -Infinity
  for (const region of regions.value) {
    for (const ring of region.rings) {
      for (const [lng, lat] of ring) {
        if (lng < minLng) minLng = lng
        if (lng > maxLng) maxLng = lng
        if (lat < minLat) minLat = lat
        if (lat > maxLat) maxLat = lat
      }
    }
  }
  const midLat: number = ((minLat + maxLat) / 2) * (Math.PI / 180)
  const kx: number = Math.cos(midLat)
  const geoW: number = (maxLng - minLng) * kx
  const geoH: number = maxLat - minLat
  const scaleFit: number = Math.min((VB_W - 2 * PAD) / geoW, (VB_H - 2 * PAD) / geoH)
  const offX: number = (VB_W - geoW * scaleFit) / 2
  const offY: number = (VB_H - geoH * scaleFit) / 2
  return (lng: number, lat: number): [number, number] => [
    offX + (lng - minLng) * kx * scaleFit,
    offY + (maxLat - lat) * scaleFit,
  ]
})

// ─── Aggregations ──────────────────────────────────────────────────────────────

/** Prospect total per region code (from geocoded cities). */
const regionTotals: ComputedRef<Record<string, number>> = computed((): Record<string, number> => {
  const totals: Record<string, number> = {}
  for (const city of coverage.value?.cities ?? []) {
    const geo: CityGeo | null = lookupCity(cityGeo.value, city.city)
    if (geo && geo.region) totals[geo.region] = (totals[geo.region] ?? 0) + city.count
  }
  return totals
})

/** Distinct department codes touched. */
const deptSet: ComputedRef<Set<string>> = computed((): Set<string> => {
  const set = new Set<string>()
  for (const city of coverage.value?.cities ?? []) {
    const geo: CityGeo | null = lookupCity(cityGeo.value, city.city)
    if (geo && geo.dept) set.add(geo.dept)
  }
  return set
})

/** Cities successfully placed on the map. */
const coveredCityCount: ComputedRef<number> = computed(
  (): number =>
    (coverage.value?.cities ?? []).filter((c): boolean => lookupCity(cityGeo.value, c.city) !== null).length,
)

/** Number of regions with at least one prospect. */
const coveredRegionCount: ComputedRef<number> = computed((): number => Object.keys(regionTotals.value).length)

/** Share of departments touched (gamified « territory »). */
const territoryPercent: ComputedRef<number> = computed((): number => Math.round((deptSet.value.size / 96) * 100))

/**
 * Fill colour for a coverage ratio (0 → 1), matching the LEGEND buckets.
 * @param ratio - region total / max region total.
 * @returns A CSS colour.
 */
function fillForRatio(ratio: number): string {
  if (ratio <= 0) return 'var(--app-surface-2)'
  if (ratio < 0.25) return 'color-mix(in srgb, var(--app-accent) 45%, var(--app-surface))'
  if (ratio < 0.5) return 'color-mix(in srgb, var(--app-accent) 80%, transparent)'
  if (ratio < 0.8) return 'color-mix(in srgb, var(--app-green) 60%, var(--app-surface))'
  return 'var(--app-green)'
}

/** Region paths with their coverage fill. */
const regionPaths: ComputedRef<RegionPath[]> = computed((): RegionPath[] => {
  const proj = project.value
  if (!proj) return []
  const max: number = Math.max(1, ...Object.values(regionTotals.value))
  return regions.value.map((region: FranceRegion): RegionPath => {
    let d = ''
    for (const ring of region.rings) {
      ring.forEach(([lng, lat], i: number): void => {
        const [x, y] = proj(lng, lat)
        d += `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)} `
      })
      d += 'Z '
    }
    const total: number = regionTotals.value[region.code] ?? 0
    return { code: region.code, nom: region.nom, d, fill: fillForRatio(total / max), total }
  })
})

/** City dots projected onto the SVG. */
const dots: ComputedRef<CityDot[]> = computed((): CityDot[] => {
  const proj = project.value
  if (!proj) return []
  const out: CityDot[] = []
  for (const city of coverage.value?.cities ?? []) {
    const geo: CityGeo | null = lookupCity(cityGeo.value, city.city)
    if (!geo) continue
    const [x, y] = proj(geo.lng, geo.lat)
    out.push({ x, y, r: Math.min(9, 2.5 + Math.sqrt(city.count) * 1.6), city: city.city, count: city.count })
  }
  return out
})

// ─── Tooltip ───────────────────────────────────────────────────────────────────

/**
 * Convert an SVG mouse event to container-relative pixel coordinates.
 * @param event - Mouse event on an SVG element.
 * @returns The [x, y] within the map wrapper.
 */
function localPoint(event: MouseEvent): [number, number] {
  const wrap = mapWrap.value
  if (!wrap) return [0, 0]
  const rect: DOMRect = wrap.getBoundingClientRect()
  return [event.clientX - rect.left, event.clientY - rect.top]
}

/**
 * Show the tooltip for a region.
 * @param event - Mouse event.
 * @param region - Hovered region path.
 */
function showRegionTip(event: MouseEvent, region: RegionPath): void {
  const [x, y] = localPoint(event)
  tip.value = {
    show: true,
    x,
    y,
    title: region.nom,
    sub: region.total > 0 ? `${region.total} prospect${region.total > 1 ? 's' : ''}` : 'Non prospectée',
  }
}

/**
 * Show the tooltip for a city dot.
 * @param event - Mouse event.
 * @param dot - Hovered city dot.
 */
function showCityTip(event: MouseEvent, dot: CityDot): void {
  const [x, y] = localPoint(event)
  tip.value = { show: true, x, y, title: dot.city, sub: `${dot.count} prospect${dot.count > 1 ? 's' : ''}` }
}

/** Hide the tooltip. */
function hideTip(): void {
  tip.value.show = false
}

// ─── Data loading ────────────────────────────────────────────────────────────

/**
 * Load coverage for the current scope then geocode its cities.
 * @returns A promise resolved once loaded.
 */
async function loadCoverage(): Promise<void> {
  isLoading.value = true
  try {
    const [scopeName, memberId] = parseScope(scope.value)
    const [data, loadedRegions] = await Promise.all([getCoverage(scopeName, memberId), loadFranceRegions()])
    coverage.value = data
    if (members.value.length === 0 && data.members.length > 0) members.value = data.members
    regions.value = loadedRegions
    cityGeo.value = await geocodeCities(data.cities.map((c): string => c.city))
  } catch {
    coverage.value = { scope: scope.value, cities: [], total_prospects: 0, members: members.value }
  } finally {
    isLoading.value = false
  }
}

/**
 * Split the scope select value into an API scope + optional member id.
 * @param value - 'me' | 'org' | 'member:{id}'.
 * @returns A [scope, memberId] tuple.
 */
function parseScope(value: string): [string, number | undefined] {
  if (value.startsWith('member:')) return ['member', Number(value.slice('member:'.length))]
  return [value, undefined]
}

/** Reload coverage when the scope changes. */
function onScopeChange(): void {
  void loadCoverage()
}

onMounted((): void => {
  void loadCoverage()
})
</script>
