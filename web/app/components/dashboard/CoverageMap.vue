<template>
  <div class="space-y-4">
    <!-- Scope selector (organization only) + headline -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <p class="text-muted max-w-md text-xs leading-relaxed">
        Votre territoire de prospection. Chaque ville prospectée colore sa région — l'objectif est d'en verdir un
        maximum.
      </p>
      <div v-if="members.length > 0" class="shrink-0">
        <select
          v-model="scope"
          class="input-field h-9 w-full text-xs sm:w-52"
          :disabled="isLoading"
          @change="onScopeChange"
        >
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

    <!-- Initial loading -->
    <div v-if="isLoading && !coverage" class="flex h-72 items-center justify-center">
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

    <!-- Map (MapLibre GL + OpenFreeMap — free, key-less, unlimited) -->
    <div v-else-if="!isMapFailed" ref="mapWrap" class="coverage-map relative">
      <div
        ref="mapContainer"
        class="coverage-map__canvas h-[420px] w-full overflow-hidden rounded-xl border border-[var(--app-line)] bg-[var(--app-surface-2)] transition-opacity duration-300 md:h-[480px]"
        :class="isLoading ? 'opacity-60' : 'opacity-100'"
      ></div>

      <!-- Tooltip -->
      <div
        v-if="tip.show"
        class="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[calc(100%+12px)] rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-2.5 py-1.5 text-xs shadow-lg"
        :style="{ left: `${tip.x}px`, top: `${tip.y}px` }"
      >
        <p class="font-semibold text-[var(--app-ink)]">{{ tip.title }}</p>
        <p class="text-muted tabular-nums">{{ tip.sub }}</p>
      </div>

      <!-- Legend -->
      <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5">
        <span class="text-muted text-[10px] tracking-wide uppercase">Intensité</span>
        <span v-for="bucket in legend" :key="bucket.label" class="flex items-center gap-1.5">
          <span
            class="h-3 w-3 rounded-sm border border-[var(--app-line)]"
            :style="{ backgroundColor: bucket.color }"
          ></span>
          <span class="text-[11px] text-[var(--app-ink-soft)]">{{ bucket.label }}</span>
        </span>
      </div>
    </div>

    <!-- Map unavailable (WebGL/network) — fall back to a ranked city list -->
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
import type { Feature, FeatureCollection, Point } from 'geojson'
import type { ExpressionSpecification, GeoJSONSource, Map as MaplibreMap, MapMouseEvent } from 'maplibre-gl'
import type { ComputedRef, Ref } from 'vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { CityGeo } from '~/composables/useFranceGeo'
import { geocodeCities, lookupCity } from '~/composables/useFranceGeo'
import { useAppTheme } from '~/composables/useAppTheme'
import type { CoverageMember, CoverageResponse } from '~/services/dashboardService'
import { getCoverage } from '~/services/dashboardService'
import type { AppTheme } from '~/types/AppTheme'

/**
 * Metropolitan region contours (simplified, ~220 KB) — the france-geojson reference
 * dataset. Loaded directly by MapLibre (its parser ignores the `text/plain`
 * content-type served by raw.githubusercontent.com, which breaks `$fetch`).
 */
const REGIONS_GEOJSON_URL =
  'https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions-version-simplifiee.geojson'

/** OpenFreeMap basemap styles (free, no API key, no usage limit) per app theme. */
const MAP_STYLES: Record<AppTheme, string> = {
  light: 'https://tiles.openfreemap.org/styles/positron',
  dark: 'https://tiles.openfreemap.org/styles/dark',
}

/** Metropolitan France framing (initial view). */
const FRANCE_BOUNDS: [[number, number], [number, number]] = [
  [-5.6, 41.2],
  [9.9, 51.4],
]

/** Panning limit — France + a comfortable margin. */
const MAP_MAX_BOUNDS: [[number, number], [number, number]] = [
  [-13.0, 37.0],
  [16.5, 55.5],
]

const REGIONS_SOURCE_ID = 'dlh-regions'
const CITIES_SOURCE_ID = 'dlh-cities'
const REGIONS_FILL_LAYER_ID = 'dlh-regions-fill'
const REGIONS_LINE_LAYER_ID = 'dlh-regions-line'
const CITIES_LAYER_ID = 'dlh-cities-dots'

/** Properties carried by each city point feature. */
interface CityFeatureProperties {
  city: string
  count: number
  /** Precomputed circle radius in px (sqrt scale on the prospect count). */
  radius: number
}

/** Choropleth washes drawn over the basemap (amber → green, Atelier palette). */
interface CoverageTierColors {
  none: string
  low: string
  medium: string
  good: string
  strong: string
}

const { theme } = useAppTheme()

const isLoading: Ref<boolean> = ref<boolean>(true)
const scope: Ref<string> = ref<string>('me')
const coverage: Ref<CoverageResponse | null> = ref<CoverageResponse | null>(null)
const members: Ref<CoverageMember[]> = ref<CoverageMember[]>([])
const cityGeo: Ref<Record<string, CityGeo | null>> = ref<Record<string, CityGeo | null>>({})

/** True when MapLibre could not start (WebGL unavailable, network down…). */
const isMapFailed: Ref<boolean> = ref<boolean>(false)
/** True once the overlay sources/layers exist on the current basemap style. */
const isMapReady: Ref<boolean> = ref<boolean>(false)

const tip: Ref<{ show: boolean; x: number; y: number; title: string; sub: string }> = ref({
  show: false,
  x: 0,
  y: 0,
  title: '',
  sub: '',
})
const mapWrap: Ref<HTMLElement | null> = ref<HTMLElement | null>(null)
const mapContainer: Ref<HTMLElement | null> = ref<HTMLElement | null>(null)

/** MapLibre instance — deliberately non-reactive (huge mutable object). */
let mapInstance: MaplibreMap | null = null

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

/** Legend buckets matching `colorForRatio` for the current theme. */
const legend: ComputedRef<Array<{ label: string; color: string }>> = computed(
  (): Array<{ label: string; color: string }> => {
    const colors: CoverageTierColors = tierColors(theme.value)
    return [
      { label: 'Aucune', color: 'var(--app-surface-2)' },
      { label: 'Faible', color: colors.low },
      { label: 'Moyenne', color: colors.medium },
      { label: 'Bonne', color: colors.good },
      { label: 'Forte', color: colors.strong },
    ]
  },
)

// ─── Choropleth colours ────────────────────────────────────────────────────────

/**
 * Choropleth washes for a theme (semi-transparent so the basemap shows through).
 * @param mode - Current app theme.
 * @returns The five tier colours.
 */
function tierColors(mode: AppTheme): CoverageTierColors {
  const green: string = mode === 'dark' ? '85, 168, 120' : '47, 125, 78'
  return {
    none: 'rgba(0, 0, 0, 0)',
    low: 'rgba(232, 163, 60, 0.28)',
    medium: 'rgba(232, 163, 60, 0.52)',
    good: `rgba(${green}, 0.42)`,
    strong: `rgba(${green}, 0.72)`,
  }
}

/**
 * Fill colour for a coverage ratio (0 → 1), matching the legend buckets.
 * @param ratio - Region total / max region total.
 * @param mode - Current app theme.
 * @returns A CSS colour.
 */
function colorForRatio(ratio: number, mode: AppTheme): string {
  const colors: CoverageTierColors = tierColors(mode)
  if (ratio <= 0) return colors.none
  if (ratio < 0.25) return colors.low
  if (ratio < 0.5) return colors.medium
  if (ratio < 0.8) return colors.good
  return colors.strong
}

/**
 * Build the data-driven fill colour for the regions layer: a `match` expression
 * on the region `code` property, one colour per covered region.
 * @returns The MapLibre paint value (plain colour when nothing is covered).
 */
function regionFillColor(): string | ExpressionSpecification {
  const totals: Record<string, number> = regionTotals.value
  const codes: string[] = Object.keys(totals)
  const colors: CoverageTierColors = tierColors(theme.value)
  if (codes.length === 0) return colors.none
  const max: number = Math.max(1, ...Object.values(totals))
  const expression: unknown[] = ['match', ['get', 'code']]
  for (const code of codes) {
    expression.push(code, colorForRatio((totals[code] ?? 0) / max, theme.value))
  }
  expression.push(colors.none)
  return expression as unknown as ExpressionSpecification
}

// ─── Map data ─────────────────────────────────────────────────────────────────

/**
 * Build the GeoJSON collection of prospected cities (geocoded ones only).
 * @returns A point collection with count + precomputed radius per city.
 */
function buildCitiesCollection(): FeatureCollection<Point, CityFeatureProperties> {
  const features: Array<Feature<Point, CityFeatureProperties>> = []
  for (const city of coverage.value?.cities ?? []) {
    const geo: CityGeo | null = lookupCity(cityGeo.value, city.city)
    if (!geo) continue
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [geo.lng, geo.lat] },
      properties: {
        city: city.city,
        count: city.count,
        radius: Math.min(16, 3.5 + Math.sqrt(city.count) * 2),
      },
    })
  }
  return { type: 'FeatureCollection', features }
}

/**
 * Add the coverage overlays (region choropleth + city dots) to the current
 * basemap style. Idempotent — skipped when the sources already exist.
 */
function addMapOverlays(): void {
  const map: MaplibreMap | null = mapInstance
  if (!map || map.getSource(REGIONS_SOURCE_ID)) return
  const dark: boolean = theme.value === 'dark'

  map.addSource(REGIONS_SOURCE_ID, { type: 'geojson', data: REGIONS_GEOJSON_URL })
  map.addSource(CITIES_SOURCE_ID, { type: 'geojson', data: buildCitiesCollection() })

  map.addLayer({
    id: REGIONS_FILL_LAYER_ID,
    type: 'fill',
    source: REGIONS_SOURCE_ID,
    paint: { 'fill-color': regionFillColor() },
  })
  map.addLayer({
    id: REGIONS_LINE_LAYER_ID,
    type: 'line',
    source: REGIONS_SOURCE_ID,
    paint: {
      'line-color': dark ? 'rgba(240, 239, 235, 0.18)' : 'rgba(29, 26, 20, 0.18)',
      'line-width': 1,
    },
  })
  map.addLayer({
    id: CITIES_LAYER_ID,
    type: 'circle',
    source: CITIES_SOURCE_ID,
    paint: {
      'circle-radius': ['get', 'radius'],
      'circle-color': dark ? '#f0efeb' : '#1d1a14',
      'circle-opacity': 0.85,
      'circle-stroke-color': dark ? '#131312' : '#fbf9f3',
      'circle-stroke-width': 1.5,
    },
  })
  isMapReady.value = true
}

/**
 * Push the latest coverage data into the map (city points + region fills).
 * No-op until the overlays exist.
 */
function refreshMapData(): void {
  const map: MaplibreMap | null = mapInstance
  if (!map || !isMapReady.value) return
  const source: GeoJSONSource | undefined = map.getSource(CITIES_SOURCE_ID) as GeoJSONSource | undefined
  source?.setData(buildCitiesCollection())
  map.setPaintProperty(REGIONS_FILL_LAYER_ID, 'fill-color', regionFillColor())
}

// ─── Map lifecycle ────────────────────────────────────────────────────────────

/**
 * Create the MapLibre map in the container (client-only, lazy-loaded chunk),
 * framed on metropolitan France with zoom + fullscreen controls.
 * @returns A promise resolved once the map is created (or marked failed).
 */
async function initMap(): Promise<void> {
  const container: HTMLElement | null = mapContainer.value
  if (!container || mapInstance) return
  try {
    const maplibregl = (await import('maplibre-gl')).default
    const map: MaplibreMap = new maplibregl.Map({
      container,
      style: MAP_STYLES[theme.value],
      bounds: FRANCE_BOUNDS,
      fitBoundsOptions: { padding: 24 },
      maxBounds: MAP_MAX_BOUNDS,
      minZoom: 4,
      maxZoom: 15,
      cooperativeGestures: true,
      attributionControl: { compact: true },
      locale: {
        'CooperativeGesturesHandler.WindowsHelpText': 'Ctrl + molette pour zoomer la carte',
        'CooperativeGesturesHandler.MacHelpText': '⌘ + molette pour zoomer la carte',
        'FullscreenControl.Enter': 'Plein écran',
        'FullscreenControl.Exit': 'Quitter le plein écran',
        'NavigationControl.ZoomIn': 'Zoomer',
        'NavigationControl.ZoomOut': 'Dézoomer',
      },
    })
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    // Fullscreen targets the wrapper so the tooltip + legend stay visible.
    map.addControl(new maplibregl.FullscreenControl({ container: mapWrap.value ?? container }), 'top-right')
    map.on('load', (): void => {
      addMapOverlays()
      refreshMapData()
    })
    map.on('mousemove', onMapMouseMove)
    map.on('mouseout', hideTip)
    mapInstance = map
  } catch {
    isMapFailed.value = true
  }
}

// ─── Tooltip ───────────────────────────────────────────────────────────────────

/**
 * Show the tooltip for the topmost hovered feature (city dot, else region).
 * @param event - MapLibre mouse event (point is container-relative).
 */
function onMapMouseMove(event: MapMouseEvent): void {
  const map: MaplibreMap | null = mapInstance
  if (!map || !isMapReady.value) return
  const features = map.queryRenderedFeatures(event.point, {
    layers: [CITIES_LAYER_ID, REGIONS_FILL_LAYER_ID],
  })
  const feature = features[0]
  map.getCanvas().style.cursor = feature ? 'pointer' : ''
  if (!feature) {
    hideTip()
    return
  }
  const { x, y } = event.point
  if (feature.layer.id === CITIES_LAYER_ID) {
    const count: number = Number(feature.properties?.count ?? 0)
    tip.value = {
      show: true,
      x,
      y,
      title: String(feature.properties?.city ?? ''),
      sub: `${count} prospect${count > 1 ? 's' : ''}`,
    }
  } else {
    const code: string = String(feature.properties?.code ?? '')
    const total: number = regionTotals.value[code] ?? 0
    tip.value = {
      show: true,
      x,
      y,
      title: String(feature.properties?.nom ?? ''),
      sub: total > 0 ? `${total} prospect${total > 1 ? 's' : ''}` : 'Non prospectée',
    }
  }
}

/** Hide the tooltip. */
function hideTip(): void {
  tip.value.show = false
}

// ─── Data loading ────────────────────────────────────────────────────────────

/**
 * Load coverage for the current scope, geocode its cities, then refresh the map.
 * @returns A promise resolved once loaded.
 */
async function loadCoverage(): Promise<void> {
  isLoading.value = true
  try {
    const [scopeName, memberId] = parseScope(scope.value)
    const data: CoverageResponse = await getCoverage(scopeName, memberId)
    coverage.value = data
    if (members.value.length === 0 && data.members.length > 0) members.value = data.members
    cityGeo.value = await geocodeCities(data.cities.map((c): string => c.city))
  } catch {
    coverage.value = { scope: scope.value, cities: [], total_prospects: 0, members: members.value }
  } finally {
    isLoading.value = false
    refreshMapData()
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

// The map branch renders only once data exists — init when its container appears.
watch(mapContainer, (container: HTMLElement | null): void => {
  if (container) void initMap()
})

// Basemap follows the app theme; overlays are re-added after the style swap.
watch(theme, (mode: AppTheme): void => {
  const map: MaplibreMap | null = mapInstance
  if (!map) return
  isMapReady.value = false
  hideTip()
  map.setStyle(MAP_STYLES[mode])
  map.once('style.load', (): void => {
    addMapOverlays()
    refreshMapData()
  })
})

onMounted((): void => {
  void loadCoverage()
})

onBeforeUnmount((): void => {
  mapInstance?.remove()
  mapInstance = null
})
</script>
