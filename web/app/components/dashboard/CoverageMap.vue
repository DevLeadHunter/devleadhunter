<template>
  <div class="flex h-full min-h-0 flex-col gap-4">
    <div v-if="availableCountries.length > 1" class="flex flex-wrap gap-1.5">
      <button
        v-for="option in availableCountries"
        :key="option.code"
        type="button"
        class="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors"
        :class="
          option.code === selectedCountry
            ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-bg)]'
            : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)]'
        "
        @click="selectCountry(option.code)"
      >
        <span>{{ option.flag }}</span>
        <span>{{ option.label }}</span>
      </button>
    </div>

    <div class="grid grid-cols-3 gap-3">
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5 text-center">
        <p class="text-xl font-bold text-[var(--app-ink)] tabular-nums">{{ selectedCountryCityCount }}</p>
        <p class="text-muted text-[10px] tracking-wide uppercase">Villes</p>
      </div>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5 text-center">
        <p class="text-xl font-bold text-[var(--app-green)] tabular-nums">
          {{ selectedCountryRegionsCovered
          }}<span class="text-[var(--app-faint)]"> / {{ selectedCountryRegionsTotal }}</span>
        </p>
        <p class="text-muted text-[10px] tracking-wide uppercase">{{ selectedCountryRegionLabel }}</p>
      </div>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5 text-center">
        <p class="text-xl font-bold text-[var(--app-ink)] tabular-nums">{{ selectedCountryProspectCount }}</p>
        <p class="text-muted text-[10px] tracking-wide uppercase">Prospects</p>
      </div>
    </div>

    <div>
      <div class="mb-1 flex items-center justify-between text-[11px]">
        <span class="text-muted">Territoire couvert</span>
        <span class="font-semibold text-[var(--app-green)] tabular-nums">{{ selectedCountryTerritoryPercent }} %</span>
      </div>
      <div class="h-1.5 overflow-hidden rounded-full bg-[var(--app-surface-2)]">
        <div
          class="h-full rounded-full bg-[var(--app-green)] transition-all duration-700"
          :style="{ width: `${selectedCountryTerritoryPercent}%` }"
        ></div>
      </div>
    </div>

    <div v-if="!store.hasLoaded" class="flex h-72 items-center justify-center">
      <UIcon name="i-lucide-loader-circle" class="h-7 w-7 animate-spin text-[var(--app-ink-soft)]" />
    </div>

    <div
      v-else-if="store.coverage && store.coverage.cities.length === 0"
      class="flex h-72 flex-col items-center justify-center gap-3 text-center"
    >
      <UIcon name="i-lucide-map" class="h-8 w-8 text-[var(--app-faint)]" />
      <p class="text-muted max-w-xs text-sm leading-relaxed">
        Aucune ville prospectée pour ces filtres. Lancez une recherche pour commencer à colorer la carte.
      </p>
      <button type="button" class="btn-secondary text-xs" @click="openSearchDrawer">Trouver des prospects</button>
    </div>

    <div v-else-if="!isMapFailed" ref="mapWrap" class="coverage-map relative flex min-h-0 flex-1 flex-col">
      <div
        ref="mapContainer"
        class="coverage-map__canvas min-h-[420px] w-full flex-1 overflow-hidden rounded-xl border border-[var(--app-line)] bg-[var(--app-surface-2)] transition-opacity duration-300"
        :class="store.isLoading ? 'opacity-60' : 'opacity-100'"
      ></div>

      <div
        v-if="tip.show"
        class="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[calc(100%+12px)] rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-2.5 py-1.5 text-xs shadow-lg"
        :style="{ left: `${tip.x}px`, top: `${tip.y}px` }"
      >
        <p class="font-semibold text-[var(--app-ink)]">{{ tip.title }}</p>
        <p class="text-muted tabular-nums">{{ tip.sub }}</p>
      </div>

      <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5">
        <span class="text-muted text-[10px] tracking-wide uppercase">Intensité</span>
        <span v-for="bucket in legend" :key="bucket.label" class="flex items-center gap-1.5">
          <span
            class="h-3 w-3 rounded-sm border border-[var(--app-line)]"
            :style="{ backgroundColor: bucket.color }"
          ></span>
          <span class="text-[11px] text-[var(--app-ink-soft)]">{{ bucket.label }}</span>
        </span>
        <span class="text-muted ml-auto hidden items-center gap-1.5 text-[11px] sm:flex">
          <UIcon name="i-lucide-mouse-pointer-click" class="h-3 w-3" />
          Cliquez une ville, une région ou un prospect pour agir
        </span>
      </div>
    </div>

    <div v-else class="space-y-2">
      <p class="text-muted text-xs">Carte indisponible — voici vos villes les plus prospectées :</p>
      <ul class="divide-y divide-[var(--app-line-soft)]">
        <li
          v-for="city in (store.coverage?.cities ?? []).slice(0, 12)"
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
import type { CoverageCity, CoverageCountry } from '~/services/dashboardService'
import type { CityFeatureProperties, CoverageTierColors, ProspectFeatureProperties } from '~/types/DashboardCoverageMap'
import type { Feature, FeatureCollection, Point } from 'geojson'
import type {
  ExpressionSpecification,
  GeoJSONSource,
  Map as MaplibreMap,
  MapGeoJSONFeature,
  MapMouseEvent,
} from 'maplibre-gl'
import type { ComputedRef, Ref } from 'vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { AddressGeo, CityGeo } from '~/composables/useFranceGeo'
import { addressKey, lookupCity, reverseGeocodeCommune } from '~/composables/useFranceGeo'
import { useAppTheme } from '~/composables/useAppTheme'
import type { Prospect, ProspectCountry } from '~/types'
import { ProspectsService } from '~/services/prospectsService'
import { useCoverageStore } from '~/stores/coverage'
import { useDrawerStackStore } from '~/stores/drawerStack'
import type { AppTheme } from '~/types/AppTheme'
import type { ForeignRegionCollection, ForeignRegionProperties } from '~/utils/foreignRegions'
import { countryBounds, countryRegionCount, fetchForeignRegions, foreignRegionAt } from '~/utils/foreignRegions'
import { FRANCE_MAJOR_CITIES, FRANCE_REGIONS } from '~/utils/franceTerritory'
import type { ProspectCountryOption } from '~/utils/prospectCountries'
import { ProspectCountries } from '~/utils/prospectCountries'

/**
 * Metropolitan region contours (simplified, ~220 KB) — the france-geojson reference
 * dataset. Loaded directly by MapLibre (its parser ignores the `text/plain`
 * content-type served by raw.githubusercontent.com, which breaks `$fetch`).
 */
const REGIONS_GEOJSON_URL: string =
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

const REGIONS_SOURCE_ID: string = 'dlh-regions'
const CITIES_SOURCE_ID: string = 'dlh-cities'
const REGIONS_FILL_LAYER_ID: string = 'dlh-regions-fill'
const REGIONS_LINE_LAYER_ID: string = 'dlh-regions-line'
const CITIES_LAYER_ID: string = 'dlh-cities-dots'
const PROSPECTS_SOURCE_ID: string = 'dlh-prospects'
const PROSPECTS_LAYER_ID: string = 'dlh-prospects-dots'
const FOREIGN_REGIONS_SOURCE_ID: string = 'dlh-foreign-regions'
const FOREIGN_REGIONS_FILL_LAYER_ID: string = 'dlh-foreign-regions-fill'
const FOREIGN_REGIONS_LINE_LAYER_ID: string = 'dlh-foreign-regions-line'

/** Placeholder source data until the foreign region contours have loaded. */
const EMPTY_COLLECTION: FeatureCollection = { type: 'FeatureCollection', features: [] }

/** Framing that fits France plus Belgium, Switzerland and Luxembourg. */
const EUROPE_BOUNDS: [[number, number], [number, number]] = [
  [-5.6, 41.2],
  [10.6, 51.6],
]

/** Label of the top administrative division per country (the coverage stat + choropleth level). */
const REGION_LABELS: Record<string, string> = { FR: 'Régions', CH: 'Cantons', BE: 'Provinces', LU: 'Districts' }

/** Zoom at which the city aggregate hands over to the per-prospect points. */
const PROSPECT_DETAIL_ZOOM: number = 11

/** Amber of the coverage palette, marking a prospect fallen back to its city centre. */
const APPROXIMATE_ADDRESS_DOT_COLOR: string = '#e8a33c'

const { theme }: { theme: Ref<AppTheme, AppTheme>; initTheme: () => void; toggleTheme: () => void } = useAppTheme()
const store: ReturnType<typeof useCoverageStore> = useCoverageStore()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

/** True when MapLibre could not start (WebGL unavailable, network down…). */
const isMapFailed: Ref<boolean> = ref(false)
/** True once the overlay sources/layers exist on the current basemap style. */
const isMapReady: Ref<boolean> = ref(false)

const tip: Ref<{ show: boolean; x: number; y: number; title: string; sub: string }> = ref({
  show: false,
  x: 0,
  y: 0,
  title: '',
  sub: '',
})
const mapWrap: Ref<HTMLElement | null> = ref(null)
const mapContainer: Ref<HTMLElement | null> = ref(null)

/** MapLibre instance — deliberately non-reactive (huge mutable object). */
let mapInstance: MaplibreMap | null = null

/** Prospect total per region code (from geocoded cities). */
const regionTotals: ComputedRef<Record<string, number>> = computed((): Record<string, number> => {
  const totals: Record<string, number> = {}
  for (const city of store.coverage?.cities ?? []) {
    const geo: CityGeo | null = lookupCity(store.cityGeo, city.city, city.country)
    if (geo && geo.region) totals[geo.region] = (totals[geo.region] ?? 0) + city.count
  }
  return totals
})

/** Belgium/Switzerland/Luxembourg region contours, loaded once for the choropleth + point-in-region totals. */
const foreignRegions: Ref<ForeignRegionCollection | null> = ref(null)

/** Country whose regions + stats the top cards currently show (driven by the selector). */
const selectedCountry: Ref<ProspectCountry> = ref('FR')

/** Countries with at least one prospect, as selectable options (API order = most prospected first). */
const availableCountries: ComputedRef<ProspectCountryOption[]> = computed((): ProspectCountryOption[] =>
  (store.coverage?.countries ?? [])
    .filter((entry: CoverageCountry): boolean => entry.count > 0)
    .map((entry: CoverageCountry): ProspectCountryOption => ProspectCountries.option(entry.country)),
)

/** True when there is at least one prospect outside France (drives the Europe framing). */
const hasForeignProspects: ComputedRef<boolean> = computed((): boolean =>
  (store.coverage?.countries ?? []).some(
    (entry: CoverageCountry): boolean => entry.country.toUpperCase() !== 'FR' && entry.count > 0,
  ),
)

/** Prospect total per foreign region (canton/province/district), from point-in-region on the geocoded cities. */
const foreignRegionTotals: ComputedRef<Record<string, number>> = computed((): Record<string, number> => {
  const totals: Record<string, number> = {}
  const regions: ForeignRegionCollection | null = foreignRegions.value
  if (!regions) return totals
  for (const city of store.coverage?.cities ?? []) {
    if (city.country.toUpperCase() === 'FR') continue
    const geo: CityGeo | null = lookupCity(store.cityGeo, city.city, city.country)
    if (!geo) continue
    const region: ForeignRegionProperties | null = foreignRegionAt(regions, geo.lng, geo.lat)
    if (region) totals[region.code] = (totals[region.code] ?? 0) + city.count
  }
  return totals
})

/** Cities successfully placed on the map for the selected country. */
const selectedCountryCityCount: ComputedRef<number> = computed(
  (): number =>
    (store.coverage?.cities ?? []).filter(
      (c: CoverageCity): boolean =>
        c.country.toUpperCase() === selectedCountry.value && lookupCity(store.cityGeo, c.city, c.country) !== null,
    ).length,
)

/** Total prospects of the selected country (from the coverage aggregation). */
const selectedCountryProspectCount: ComputedRef<number> = computed(
  (): number =>
    (store.coverage?.countries ?? []).find(
      (entry: CoverageCountry): boolean => entry.country.toUpperCase() === selectedCountry.value,
    )?.count ?? 0,
)

/** Label of the selected country's top administrative division (Régions/Cantons/Provinces/Districts). */
const selectedCountryRegionLabel: ComputedRef<string> = computed(
  (): string => REGION_LABELS[selectedCountry.value] ?? 'Régions',
)

/** Number of the selected country's regions holding at least one prospect. */
const selectedCountryRegionsCovered: ComputedRef<number> = computed((): number => {
  if (selectedCountry.value === 'FR') return Object.keys(regionTotals.value).length
  const prefix: string = `${selectedCountry.value}-`
  return Object.keys(foreignRegionTotals.value).filter((code: string): boolean => code.startsWith(prefix)).length
})

/** Total number of regions the selected country is divided into. */
const selectedCountryRegionsTotal: ComputedRef<number> = computed((): number => {
  if (selectedCountry.value === 'FR') return Object.keys(FRANCE_REGIONS).length
  const regions: ForeignRegionCollection | null = foreignRegions.value
  return regions ? countryRegionCount(regions, selectedCountry.value) : 0
})

/** Share of the selected country's regions touched (gamified « territory »). */
const selectedCountryTerritoryPercent: ComputedRef<number> = computed((): number => {
  const total: number = selectedCountryRegionsTotal.value
  return total > 0 ? Math.round((selectedCountryRegionsCovered.value / total) * 100) : 0
})

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
 * Build a data-driven `match` fill from a { region code → total } map: one colour per
 * covered region, shared by the French regions and the foreign cantons/provinces.
 * @param totals - Prospect total per region code.
 * @returns The MapLibre paint value (plain « none » colour when nothing is covered).
 */
function choroplethFillColor(totals: Record<string, number>): string | ExpressionSpecification {
  const codes: string[] = Object.keys(totals)
  const colors: CoverageTierColors = tierColors(theme.value)
  if (codes.length === 0) return colors.none
  const max: number = Math.max(1, ...Object.values(totals))
  const expression: unknown[] = ['match', ['get', 'code']]
  for (const code of codes) expression.push(code, colorForRatio((totals[code] ?? 0) / max, theme.value))
  expression.push(colors.none)
  return expression as unknown as ExpressionSpecification
}

/**
 * Build the GeoJSON collection of prospected cities (geocoded ones only).
 * @returns A point collection with count + precomputed radius per city.
 */
function buildCitiesCollection(): FeatureCollection<Point, CityFeatureProperties> {
  const features: Array<Feature<Point, CityFeatureProperties>> = []
  for (const city of store.coverage?.cities ?? []) {
    const geo: CityGeo | null = lookupCity(store.cityGeo, city.city, city.country)
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
 * Build the GeoJSON collection of individual prospects, placed at their street
 * address when the BAN could resolve it, at the city centre otherwise.
 * @returns A point collection, one feature per prospect.
 */
function buildProspectsCollection(): FeatureCollection<Point, ProspectFeatureProperties> {
  const features: Array<Feature<Point, ProspectFeatureProperties>> = []
  for (const point of store.coverage?.points ?? []) {
    const precise: AddressGeo | null = store.addressGeo[addressKey(point.address, point.city, point.country)] ?? null
    const fallback: CityGeo | null = lookupCity(store.cityGeo, point.city, point.country)
    const position: AddressGeo | CityGeo | null = precise ?? fallback
    if (!position) continue
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [position.lng, position.lat] },
      properties: {
        prospectId: point.id,
        name: point.name,
        city: point.city,
        isPreciseAddress: precise !== null,
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

  // Foreign cantons/provinces first, so France's detailed regions paint alongside them.
  map.addSource(FOREIGN_REGIONS_SOURCE_ID, { type: 'geojson', data: foreignRegions.value ?? EMPTY_COLLECTION })
  map.addLayer({
    id: FOREIGN_REGIONS_FILL_LAYER_ID,
    type: 'fill',
    source: FOREIGN_REGIONS_SOURCE_ID,
    paint: { 'fill-color': choroplethFillColor(foreignRegionTotals.value) },
  })
  map.addLayer({
    id: FOREIGN_REGIONS_LINE_LAYER_ID,
    type: 'line',
    source: FOREIGN_REGIONS_SOURCE_ID,
    paint: {
      'line-color': dark ? 'rgba(240, 239, 235, 0.18)' : 'rgba(29, 26, 20, 0.18)',
      'line-width': 1,
    },
  })

  map.addSource(REGIONS_SOURCE_ID, { type: 'geojson', data: REGIONS_GEOJSON_URL })
  map.addSource(CITIES_SOURCE_ID, { type: 'geojson', data: buildCitiesCollection() })

  map.addLayer({
    id: REGIONS_FILL_LAYER_ID,
    type: 'fill',
    source: REGIONS_SOURCE_ID,
    paint: { 'fill-color': choroplethFillColor(regionTotals.value) },
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
    maxzoom: PROSPECT_DETAIL_ZOOM,
    paint: {
      'circle-radius': ['get', 'radius'],
      'circle-color': dark ? '#f0efeb' : '#1d1a14',
      'circle-opacity': 0.85,
      'circle-stroke-color': dark ? '#131312' : '#fbf9f3',
      'circle-stroke-width': 1.5,
    },
  })

  map.addSource(PROSPECTS_SOURCE_ID, { type: 'geojson', data: buildProspectsCollection() })
  map.addLayer({
    id: PROSPECTS_LAYER_ID,
    type: 'circle',
    source: PROSPECTS_SOURCE_ID,
    minzoom: PROSPECT_DETAIL_ZOOM,
    paint: {
      'circle-radius': 6,
      'circle-color': [
        'case',
        ['get', 'isPreciseAddress'],
        dark ? '#f0efeb' : '#1d1a14',
        APPROXIMATE_ADDRESS_DOT_COLOR,
      ],
      'circle-opacity': 0.9,
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
  const prospectSource: GeoJSONSource | undefined = map.getSource(PROSPECTS_SOURCE_ID) as GeoJSONSource | undefined
  prospectSource?.setData(buildProspectsCollection())
  const foreignSource: GeoJSONSource | undefined = map.getSource(FOREIGN_REGIONS_SOURCE_ID) as GeoJSONSource | undefined
  if (foreignRegions.value) foreignSource?.setData(foreignRegions.value)
  map.setPaintProperty(REGIONS_FILL_LAYER_ID, 'fill-color', choroplethFillColor(regionTotals.value))
  map.setPaintProperty(FOREIGN_REGIONS_FILL_LAYER_ID, 'fill-color', choroplethFillColor(foreignRegionTotals.value))
}

/**
 * Create the MapLibre map in the container (client-only, lazy-loaded chunk),
 * framed on metropolitan France with zoom + fullscreen controls.
 * @returns A promise resolved once the map is created (or marked failed).
 */
async function initMap(): Promise<void> {
  const container: HTMLElement | null = mapContainer.value
  if (!container || mapInstance) return
  try {
    const maplibregl: typeof import('C:/Users/leogu/Desktop/Projects/devleadhunter/web/node_modules/maplibre-gl/dist/maplibre-gl') =
      (await import('maplibre-gl')).default
    const map: MaplibreMap = new maplibregl.Map({
      container,
      style: MAP_STYLES[theme.value],
      bounds: hasForeignProspects.value ? EUROPE_BOUNDS : FRANCE_BOUNDS,
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
    map.on('click', (event: MapMouseEvent): void => {
      void onMapClick(event)
    })
    mapInstance = map
  } catch {
    isMapFailed.value = true
  }
}

/**
 * Trade prefilled into search drawers when exactly one trade is selected.
 * @returns A prefill fragment ({} when 0 or several trades are selected).
 */
function categoryPrefill(): { category?: string } {
  return store.selectedCategories.length === 1 ? { category: store.selectedCategories[0] as string } : {}
}

/**
 * Open the detail drawer of a prospect clicked on the map.
 * @param prospectId - Identifier carried by the clicked feature.
 * @returns A promise resolved once the drawer is pushed.
 */
async function openProspectFromMap(prospectId: number): Promise<void> {
  if (!prospectId) return
  try {
    const prospect: Prospect = await ProspectsService.getProspect(prospectId)
    drawerStack.push({ kind: 'prospect', prospect })
  } catch {
    // Prospect supprimé entre le chargement de la carte et le clic : on ignore.
  }
}

/**
 * Route a map click to the right drawer:
 * - city dot → zone drawer listing that city's prospects;
 * - covered region → zone drawer listing the region's prospects;
 * - anything else → reverse geocode the click and prefill a new search there
 *   (fallback: the region's biggest city).
 * @param event - MapLibre click event.
 * @returns A promise resolved once the drawer is opened.
 */
async function onMapClick(event: MapMouseEvent): Promise<void> {
  const map: MaplibreMap | null = mapInstance
  if (!map || !isMapReady.value) return
  const features: MapGeoJSONFeature[] = map.queryRenderedFeatures(event.point, {
    layers: [PROSPECTS_LAYER_ID, CITIES_LAYER_ID, REGIONS_FILL_LAYER_ID, FOREIGN_REGIONS_FILL_LAYER_ID],
  })
  const feature: MapGeoJSONFeature | undefined = features[0]
  if (!feature) return

  // ── Prospect dot: open that prospect directly ──
  if (feature.layer.id === PROSPECTS_LAYER_ID) {
    await openProspectFromMap(Number(feature.properties?.prospectId ?? 0))
    return
  }

  // ── City dot: prospected city → its prospect list ──
  if (feature.layer.id === CITIES_LAYER_ID) {
    const city: string = String(feature.properties?.city ?? '')
    if (!city) return
    drawerStack.push({
      kind: 'coverage-prospects',
      zone: { kind: 'city', label: city, cities: [city], prefillCity: city },
    })
    return
  }

  // ── Foreign region (canton/province/district): launch a search in that country ──
  if (feature.layer.id === FOREIGN_REGIONS_FILL_LAYER_ID) {
    const countryCode: string = String(feature.properties?.country ?? '')
    drawerStack.push({
      kind: 'search-prospects',
      prefill: { ...(countryCode ? { country: countryCode as ProspectCountry } : {}), ...categoryPrefill() },
    })
    return
  }

  // ── Region fill ──
  const code: string = String(feature.properties?.code ?? '')
  const regionLabel: string = String(feature.properties?.nom ?? FRANCE_REGIONS[code] ?? '')
  const isCovered: boolean = (regionTotals.value[code] ?? 0) > 0

  if (isCovered) {
    drawerStack.push({
      kind: 'coverage-prospects',
      zone: {
        kind: 'region',
        label: regionLabel,
        cities: store.coveredCitiesOfRegion(code),
        prefillCity: FRANCE_MAJOR_CITIES.find((c: FranceMajorCity): boolean => c.region === code)?.name,
      },
    })
    return
  }

  // Falls back to the region's biggest city when the cursor is not over a commune.
  const commune: ReverseGeocodedCommune | null = await reverseGeocodeCommune(event.lngLat.lng, event.lngLat.lat)
  const fallback: string | undefined = FRANCE_MAJOR_CITIES.find(
    (c: FranceMajorCity): boolean => c.region === code,
  )?.name
  const city: string | undefined = commune?.name ?? fallback
  drawerStack.push({
    kind: 'search-prospects',
    prefill: { ...(city ? { city } : {}), ...categoryPrefill() },
  })
}

/** Open the search drawer from the empty state. */
function openSearchDrawer(): void {
  drawerStack.push({ kind: 'search-prospects', prefill: { ...categoryPrefill() } })
}

/**
 * Frame the map on a country from its region bounding box (France uses a fixed box).
 * @param code - The country to zoom onto.
 */
function frameCountry(code: ProspectCountry): void {
  const map: MaplibreMap | null = mapInstance
  if (!map || !isMapReady.value) return
  const bounds: [[number, number], [number, number]] | null =
    code === 'FR' ? FRANCE_BOUNDS : foreignRegions.value ? countryBounds(foreignRegions.value, code) : null
  if (bounds) map.fitBounds(bounds, { padding: 30, duration: 600 })
}

/**
 * Select a country: switch the stat cards to it and zoom the map onto it.
 * @param code - The country picked in the selector.
 */
function selectCountry(code: ProspectCountry): void {
  selectedCountry.value = code
  frameCountry(code)
}

/**
 * Show the tooltip for the topmost hovered feature (city dot, else region).
 * @param event - MapLibre mouse event (point is container-relative).
 */
function onMapMouseMove(event: MapMouseEvent): void {
  const map: MaplibreMap | null = mapInstance
  if (!map || !isMapReady.value) return
  const features: MapGeoJSONFeature[] = map.queryRenderedFeatures(event.point, {
    layers: [PROSPECTS_LAYER_ID, CITIES_LAYER_ID, REGIONS_FILL_LAYER_ID, FOREIGN_REGIONS_FILL_LAYER_ID],
  })
  const feature: MapGeoJSONFeature | undefined = features[0]
  map.getCanvas().style.cursor = feature ? 'pointer' : ''
  if (!feature) {
    hideTip()
    return
  }
  const { x, y }: { x: number; y: number } = event.point
  if (feature.layer.id === PROSPECTS_LAYER_ID) {
    const isPrecise: boolean = Boolean(feature.properties?.isPreciseAddress)
    tip.value = {
      show: true,
      x,
      y,
      title: String(feature.properties?.name ?? ''),
      sub: isPrecise
        ? `${String(feature.properties?.city ?? '')} — cliquer pour ouvrir`
        : `${String(feature.properties?.city ?? '')} — adresse approchée`,
    }
  } else if (feature.layer.id === CITIES_LAYER_ID) {
    const count: number = Number(feature.properties?.count ?? 0)
    tip.value = {
      show: true,
      x,
      y,
      title: String(feature.properties?.city ?? ''),
      sub: `${count} prospect${count > 1 ? 's' : ''} — cliquer pour voir`,
    }
  } else if (feature.layer.id === FOREIGN_REGIONS_FILL_LAYER_ID) {
    const code: string = String(feature.properties?.code ?? '')
    const total: number = foreignRegionTotals.value[code] ?? 0
    tip.value = {
      show: true,
      x,
      y,
      title: String(feature.properties?.name ?? ''),
      sub:
        total > 0
          ? `${total} prospect${total > 1 ? 's' : ''} — cliquer pour voir`
          : 'Non prospecté — cliquer pour attaquer',
    }
  } else {
    const code: string = String(feature.properties?.code ?? '')
    const total: number = regionTotals.value[code] ?? 0
    tip.value = {
      show: true,
      x,
      y,
      title: String(feature.properties?.nom ?? ''),
      sub:
        total > 0
          ? `${total} prospect${total > 1 ? 's' : ''} — cliquer pour voir`
          : 'Non prospectée — cliquer pour attaquer',
    }
  }
}

/** Hide the tooltip. */
function hideTip(): void {
  tip.value.show = false
}

// After the empty state tore the branch down, the old instance points at a dead container.
watch(mapContainer, (container: HTMLElement | null): void => {
  if (!container) return
  if (mapInstance && mapInstance.getContainer() !== container) {
    mapInstance.remove()
    mapInstance = null
    isMapReady.value = false
  }
  void initMap()
})

// Repaint whenever the store data changes (scope / trade filter reloads).
// Les adresses arrivent après les villes : sans elles ici, les points resteraient au centre-ville.
watch(
  (): [
    typeof store.coverage,
    Record<string, CityGeo | null>,
    Record<string, AddressGeo | null>,
    ForeignRegionCollection | null,
  ] => [store.coverage, store.cityGeo, store.addressGeo, foreignRegions.value],
  (): void => {
    refreshMapData()
  },
  { deep: false },
)

// Keep the selector on a country that actually has prospects (defaults to the most prospected).
watch(
  availableCountries,
  (options: ProspectCountryOption[]): void => {
    if (options.length === 0) return
    if (!options.some((option: ProspectCountryOption): boolean => option.code === selectedCountry.value)) {
      selectedCountry.value = options[0]?.code ?? 'FR'
    }
  },
  { immediate: true },
)

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

onMounted(async (): Promise<void> => {
  foreignRegions.value = await fetchForeignRegions()
})

onBeforeUnmount((): void => {
  mapInstance?.remove()
  mapInstance = null
})
</script>
