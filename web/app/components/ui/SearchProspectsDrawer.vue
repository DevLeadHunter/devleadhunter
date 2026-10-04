<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="props.open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[460px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-2xl"
      >
        <UiDrawerHeader
          title="Trouver des prospects"
          icon="i-lucide-search"
          :show-back="props.showBack"
          @back="emit('back')"
          @close="emit('close')"
        >
          <template #subtitle>
            <p class="mt-0.5 text-[11px] leading-relaxed text-[var(--app-ink-soft)]">
              Donnez un objectif : l'app cherche, vérifie et garde.
            </p>
          </template>
        </UiDrawerHeader>

        <div class="flex-1 space-y-5 overflow-x-hidden overflow-y-auto px-5 py-4">
          <form id="search-prospects-form" class="space-y-5" @submit.prevent="submit">
            <div>
              <label for="sp-trade" class="app-label mb-1.5 block">
                Métiers recherchés <span class="text-[var(--app-accent)]">*</span>
              </label>
              <UiRemovableChipList
                v-if="form.trades.length > 0"
                :labels="form.trades"
                class="mb-2"
                @remove="removeTrade"
              />
              <div class="flex gap-2">
                <div class="relative min-w-0 flex-1">
                  <UIcon
                    name="i-lucide-hammer"
                    class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
                  />
                  <input
                    id="sp-trade"
                    v-model="tradeInput"
                    type="text"
                    autocomplete="off"
                    :placeholder="isAssistantModule ? 'Couvreur, carrosserie…' : 'Plombier, électricien…'"
                    :disabled="hasMaximumTrades"
                    class="app-input w-full pl-9 disabled:cursor-not-allowed disabled:opacity-50"
                    @keydown.enter.prevent="addTypedTrades"
                  />
                </div>
                <button
                  type="button"
                  class="app-btn-secondary shrink-0 px-3 text-xs"
                  :disabled="hasMaximumTrades || tradeInput.trim() === ''"
                  @click="addTypedTrades"
                >
                  Ajouter
                </button>
              </div>

              <div v-if="isAssistantModule && wavePresets.length > 0" class="mt-2 space-y-1.5">
                <div v-for="preset in wavePresets" :key="preset.wave" class="flex flex-wrap items-center gap-1.5">
                  <span
                    class="font-label w-14 shrink-0 text-[10px] tracking-wide text-[var(--app-faint)] uppercase"
                    :title="preset.labels.join(', ')"
                  >
                    Vague {{ preset.wave }}
                  </span>
                  <button
                    v-for="term in preset.searchTerms"
                    :key="term"
                    type="button"
                    class="cursor-pointer rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] px-2.5 py-1 text-xs text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-ink-soft)] hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-50"
                    :disabled="hasMaximumTrades || isTradeSelected(term)"
                    @click="addTrade(term)"
                  >
                    {{ term }}
                  </button>
                </div>
              </div>
              <div v-else-if="suggestedTrades.length > 0" class="mt-2 flex flex-wrap gap-1.5">
                <button
                  v-for="trade in suggestedTrades"
                  :key="trade.key"
                  type="button"
                  class="cursor-pointer rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] px-2.5 py-1 text-xs text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-ink-soft)] hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="hasMaximumTrades"
                  @click="addTrade(trade.label)"
                >
                  {{ trade.label }}
                </button>
              </div>
              <p class="text-muted mt-2 text-[10px] leading-relaxed">
                {{
                  hasMaximumTrades
                    ? `${PROSPECT_SEARCH_MAXIMUM_TRADES} métiers au maximum par recherche.`
                    : 'Plusieurs métiers possibles : chacun a son propre compte.'
                }}
              </p>
            </div>

            <div>
              <label for="sp-country" class="app-label mb-1.5 block">Pays</label>
              <select id="sp-country" v-model="form.country" class="app-input w-full">
                <option
                  v-for="countryOption in ProspectCountries.catalog"
                  :key="countryOption.code"
                  :value="countryOption.code"
                >
                  {{ countryOption.flag }} {{ countryOption.label }}
                </option>
              </select>
            </div>

            <div>
              <label for="sp-city" class="app-label mb-1.5 block">
                Villes <span class="tracking-normal normal-case">(facultatif)</span>
              </label>
              <UiRemovableChipList
                v-if="form.cities.length > 0"
                :labels="form.cities"
                class="mb-2"
                @remove="removeCity"
              />
              <div class="flex gap-2">
                <div class="min-w-0 flex-1" @keydown.enter.prevent="addTypedCity">
                  <UiCityAutocompleteInput
                    :key="cityInputRevision"
                    v-model="cityInput"
                    input-id="sp-city"
                    placeholder="Ajouter une ville"
                    show-icon
                    :disabled="hasMaximumCities"
                    @select="addSuggestedCity"
                  />
                </div>
                <button
                  type="button"
                  class="app-btn-secondary shrink-0 px-3 text-xs"
                  :disabled="hasMaximumCities || cityInput.trim() === ''"
                  @click="addTypedCity"
                >
                  Ajouter
                </button>
              </div>
              <p class="text-muted mt-2 text-[10px] leading-relaxed">
                Laissez vide : l'app choisit les villes et en change jusqu'au compte.
              </p>
            </div>

            <div>
              <label for="sp-count" class="app-label mb-1.5 block">Nombre par métier</label>
              <input
                id="sp-count"
                v-model.number="form.countPerTrade"
                type="number"
                inputmode="numeric"
                min="1"
                :max="PROSPECT_SEARCH_MAXIMUM_COUNT_PER_TRADE"
                step="1"
                required
                class="app-input w-full"
              />
            </div>

            <div>
              <p id="sp-channel-label" class="app-label mb-1.5">Comment les joindre</p>
              <div class="space-y-2" role="radiogroup" aria-labelledby="sp-channel-label">
                <button
                  v-for="option in PROSPECT_SEARCH_CHANNEL_OPTIONS"
                  :key="option.value"
                  type="button"
                  role="radio"
                  :aria-checked="form.channel === option.value"
                  class="flex w-full cursor-pointer items-start gap-3 rounded-xl border px-3.5 py-3 text-left transition-colors focus-visible:ring-2 focus-visible:ring-[var(--app-ink-soft)] focus-visible:outline-none"
                  :class="
                    form.channel === option.value
                      ? 'border-[var(--app-ink)] bg-[var(--app-surface-2)]'
                      : 'border-[var(--app-line)] hover:border-[var(--app-ink-soft)]'
                  "
                  @click="form.channel = option.value"
                >
                  <UIcon :name="option.icon" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-ink)]" />
                  <span class="min-w-0 flex-1">
                    <span class="block text-sm font-medium text-[var(--app-ink)]">{{ option.label }}</span>
                    <span class="mt-0.5 block text-xs leading-relaxed text-[var(--app-ink-soft)]">
                      {{ option.description }}
                    </span>
                  </span>
                  <span
                    class="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border"
                    :class="
                      form.channel === option.value
                        ? 'border-[var(--app-ink)] bg-[var(--app-ink)]'
                        : 'border-[var(--app-faint)]'
                    "
                  >
                    <UIcon
                      v-if="form.channel === option.value"
                      name="i-lucide-check"
                      class="h-3 w-3 text-[var(--app-bg)]"
                    />
                  </span>
                </button>
              </div>
            </div>

            <div>
              <p class="app-label mb-1.5">Note Google minimale</p>
              <UiSegmentedControl
                v-model="minimumRatingChoice"
                :options="PROSPECT_SEARCH_MINIMUM_RATING_OPTIONS"
                label="Note Google minimale"
              />
              <p class="text-muted mt-2 text-[10px] leading-relaxed">
                Une note lue sur moins de trois avis n'écarte personne.
              </p>
            </div>

            <div class="space-y-2 border-t border-[var(--app-line-soft)] pt-4">
              <UiCheckbox
                id="sp-only-without-website"
                v-model="form.onlyWithoutWebsite"
                label="Uniquement sans site web"
              />
              <p v-if="isAssistantModule && !form.onlyWithoutWebsite" class="text-muted text-[10px] leading-relaxed">
                La réceptionniste vit sur sa propre page : avec ou sans site, un pro qui reçoit des demandes est une
                cible.
              </p>
            </div>
          </form>

          <div
            v-if="store.currentSearch"
            class="rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-3.5"
            aria-live="polite"
          >
            <p class="app-label">Dernière recherche</p>
            <div class="mt-1.5 flex items-center justify-between gap-3">
              <span class="min-w-0 truncate text-xs font-medium text-[var(--app-ink)]">
                {{ ProspectSearches.tradesLabel(store.currentSearch) }}
              </span>
              <span :class="['app-badge shrink-0', currentSearchStatus.badgeClass]">
                {{ currentSearchStatus.label }}
              </span>
            </div>
            <div class="mt-2 h-2 w-full overflow-hidden rounded-full bg-[var(--app-surface-2)]">
              <div
                class="h-full rounded-full bg-[var(--app-ink)] transition-[width] duration-300"
                :style="{ width: `${currentSearchKeptPercentage}%` }"
              ></div>
            </div>
            <div class="mt-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5 text-[11px]">
              <span class="font-label text-[var(--app-ink-soft)] tabular-nums">
                {{ ProspectSearches.keptCount(store.currentSearch) }} /
                {{ ProspectSearches.wantedCount(store.currentSearch) }} gardés
              </span>
              <span class="flex items-center gap-3">
                <button
                  v-if="store.isCurrentSearchActive"
                  type="button"
                  class="inline-flex cursor-pointer items-center gap-1.5 font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="store.isCancelling"
                  @click="cancelSearch"
                >
                  <UIcon
                    :name="store.isCancelling ? 'i-lucide-loader-circle' : 'i-lucide-circle-stop'"
                    :class="['h-3.5 w-3.5', store.isCancelling && 'animate-spin']"
                  />
                  Arrêter
                </button>
                <NuxtLink
                  v-if="!isOnSearchPage"
                  :to="SEARCH_PAGE_PATH"
                  class="inline-flex items-center gap-1 font-medium text-[var(--app-ink)] hover:underline"
                  @click="emit('close')"
                >
                  Voir la recherche <UIcon name="i-lucide-arrow-right" class="h-3 w-3" />
                </NuxtLink>
              </span>
            </div>
          </div>

          <UiCollapsibleCard icon="i-lucide-info" title="Comment ça marche">
            <div class="px-4 py-4">
              <ol class="space-y-2.5">
                <li v-for="(step, index) in SEARCH_STEPS" :key="step" class="flex items-start gap-2.5">
                  <span
                    class="font-label flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--app-surface-2)] text-[0.6rem] font-semibold text-[var(--app-ink)]"
                  >
                    {{ index + 1 }}
                  </span>
                  <p class="text-[11px] leading-relaxed text-[var(--app-ink-soft)]">{{ step }}</p>
                </li>
              </ol>
            </div>
          </UiCollapsibleCard>
        </div>

        <div class="flex flex-col gap-2 border-t border-[var(--app-line)] px-5 py-4 sm:flex-row">
          <button type="button" class="app-btn-secondary w-full sm:flex-1" @click="emit('close')">Fermer</button>
          <button
            type="submit"
            form="search-prospects-form"
            class="app-btn-primary w-full sm:flex-1"
            :disabled="store.isStarting || isServerSearching"
          >
            <UIcon
              :name="store.isStarting || isServerSearching ? 'i-lucide-loader-circle' : 'i-lucide-search'"
              :class="['h-4 w-4', (store.isStarting || isServerSearching) && 'animate-spin']"
            />
            {{ isServerSearching ? 'Recherche en cours…' : 'Lancer la recherche' }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref, WritableComputedRef } from 'vue'
import type { ProspectCountry } from '~/types'
import type { CitySuggestion } from '~/types/CityAutocompleteInput'
import type { UseToastReturn } from '~/types/Composables'
import type { ProspectSearchChannelOption, ProspectSearchTradeOption } from '~/types/ProspectSearch'
import type { SelectFieldOption } from '~/types/SelectField'
import type { SourcingVertical, SourcingWavePreset } from '~/types/Sourcing'
import type { StatusPresentation } from '~/types/StatusPresentation'
import type {
  ProspectSearchFormState,
  SearchProspectsPrefill,
  UiSearchProspectsDrawerEmits,
  UiSearchProspectsDrawerProps,
} from '~/types/UiSearchProspectsDrawer'
import { computed, nextTick, ref, watch } from 'vue'
import { useToast } from '~/composables/useToast'
import {
  PROSPECT_SEARCH_CHANNEL_OPTIONS,
  PROSPECT_SEARCH_DEFAULT_COUNT_PER_TRADE,
  PROSPECT_SEARCH_DEFAULT_MINIMUM_RATING,
  PROSPECT_SEARCH_MAXIMUM_CITIES,
  PROSPECT_SEARCH_MAXIMUM_CITY_LENGTH,
  PROSPECT_SEARCH_MAXIMUM_COUNT_PER_TRADE,
  PROSPECT_SEARCH_MAXIMUM_TRADE_LENGTH,
  PROSPECT_SEARCH_MAXIMUM_TRADES,
  PROSPECT_SEARCH_MINIMUM_RATING_OPTIONS,
  PROSPECT_SEARCH_NO_MINIMUM_RATING,
  PROSPECT_SEARCH_STATUS_PRESENTATION,
} from '~/constants/prospectSearch'
import { SourcingService } from '~/services/sourcingService'
import { useModuleStore } from '~/stores/moduleStore'
import { useProspectSearchStore } from '~/stores/prospectSearch'
import { ProspectCountries } from '~/utils/prospectCountries'
import { ProspectSearches } from '~/utils/prospectSearches'

/** Drawer to configure and launch a prospect search. */
const props: UiSearchProspectsDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
  prefill: {
    type: Object as PropType<SearchProspectsPrefill | null>,
    default: null,
  },
})

const emit: EmitFn<UiSearchProspectsDrawerEmits> = defineEmits<UiSearchProspectsDrawerEmits>()

const store: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()
const moduleStore: ReturnType<typeof useModuleStore> = useModuleStore()
const route: ReturnType<typeof useRoute> = useRoute()
const toast: UseToastReturn = useToast()

const FORM_STORAGE_KEY: string = 'devleadhunter-prospect-search-form'
const SEARCH_PAGE_PATH: string = '/dashboard/search-prospects'
const CITY_INPUT_ID: string = 'sp-city'

const SEARCH_STEPS: string[] = [
  'Indiquez les métiers, le pays et le nombre de prospects voulu pour chacun.',
  "L'app cherche sur Google, Facebook et les registres professionnels, puis vérifie chaque entreprise.",
  'Chaque prospect gardé arrive avec ses preuves, chaque entreprise écartée avec sa raison.',
  'Les cas sans preuve franche attendent votre décision dans « À confirmer ».',
]

/** Target verticals of the Réceptionniste IA, fetched once when the drawer first opens. */
const verticals: Ref<SourcingVertical[]> = ref([])
const form: Ref<ProspectSearchFormState> = ref(defaultForm(moduleStore.activeKey === 'ai-assistant'))
const tradeInput: Ref<string> = ref('')
const cityInput: Ref<string> = ref('')
const cityInputRevision: Ref<number> = ref(0)

const isAssistantModule: ComputedRef<boolean> = computed((): boolean => moduleStore.activeKey === 'ai-assistant')

/** The verticals' search terms grouped by prospection wave, wave 1 first. */
const wavePresets: ComputedRef<SourcingWavePreset[]> = computed((): SourcingWavePreset[] => {
  const byWave: Map<number, SourcingWavePreset> = new Map()
  for (const vertical of verticals.value) {
    const preset: SourcingWavePreset = byWave.get(vertical.wave) ?? {
      wave: vertical.wave,
      labels: [],
      searchTerms: [],
    }
    preset.labels.push(vertical.label)
    preset.searchTerms.push(...vertical.search_terms)
    byWave.set(vertical.wave, preset)
  }
  return [...byWave.values()].sort(
    (left: SourcingWavePreset, right: SourcingWavePreset): number => left.wave - right.wave,
  )
})

const suggestedTrades: ComputedRef<ProspectSearchTradeOption[]> = computed((): ProspectSearchTradeOption[] =>
  store.tradeOptions.filter((trade: ProspectSearchTradeOption): boolean => !isTradeSelected(trade.label)),
)

const hasMaximumTrades: ComputedRef<boolean> = computed(
  (): boolean => form.value.trades.length >= PROSPECT_SEARCH_MAXIMUM_TRADES,
)

const hasMaximumCities: ComputedRef<boolean> = computed(
  (): boolean => form.value.cities.length >= PROSPECT_SEARCH_MAXIMUM_CITIES,
)

const minimumRatingChoice: WritableComputedRef<number> = computed({
  get: (): number => form.value.minimumRating ?? PROSPECT_SEARCH_NO_MINIMUM_RATING,
  set: (choice: number): void => {
    form.value.minimumRating = choice === PROSPECT_SEARCH_NO_MINIMUM_RATING ? null : choice
  },
})

const isOnSearchPage: ComputedRef<boolean> = computed((): boolean => route.path.endsWith(SEARCH_PAGE_PATH))

const isServerSearching: ComputedRef<boolean> = computed(
  (): boolean => store.currentSearch?.status === 'pending' || store.currentSearch?.status === 'running',
)

const currentSearchStatus: ComputedRef<StatusPresentation> = computed(
  (): StatusPresentation => PROSPECT_SEARCH_STATUS_PRESENTATION[store.currentSearch?.status ?? 'pending'],
)

const currentSearchKeptPercentage: ComputedRef<number> = computed((): number => {
  if (store.currentSearch === null) return 0
  const wantedCount: number = ProspectSearches.wantedCount(store.currentSearch)
  return wantedCount > 0 ? Math.min(100, (ProspectSearches.keptCount(store.currentSearch) / wantedCount) * 100) : 0
})

/**
 * Default form state. The Réceptionniste IA targets pros with or without a site, so its
 * searches keep both; the site module keeps looking for pros without one.
 * @param isForAssistantModule - Whether the form is opened from the Réceptionniste IA module.
 * @returns A fresh form.
 */
function defaultForm(isForAssistantModule: boolean): ProspectSearchFormState {
  return {
    trades: [],
    country: ProspectCountries.france.code,
    cities: [],
    countPerTrade: PROSPECT_SEARCH_DEFAULT_COUNT_PER_TRADE,
    channel: 'email',
    onlyWithoutWebsite: !isForAssistantModule,
    minimumRating: PROSPECT_SEARCH_DEFAULT_MINIMUM_RATING,
  }
}

/**
 * Storage key of the persisted form — one per module, so each keeps its own defaults.
 * @returns The key of the active module's form.
 */
function formStorageKey(): string {
  return isAssistantModule.value ? `${FORM_STORAGE_KEY}:ai-assistant` : FORM_STORAGE_KEY
}

/**
 * Keep the usable labels of a remembered list.
 * @param saved - Value read from the storage, of unknown shape.
 * @param maximumCount - How many entries the search accepts.
 * @returns The non-empty strings, capped.
 */
function readSavedLabels(saved: unknown, maximumCount: number): string[] {
  if (!Array.isArray(saved)) return []
  return saved
    .filter((label: unknown): label is string => typeof label === 'string' && label.trim() !== '')
    .slice(0, maximumCount)
}

/**
 * Rebuild the form from what was remembered, field by field: a stale or damaged entry falls back to the default.
 * @param raw - Serialized form read from the storage.
 * @returns A valid form.
 */
function readSavedForm(raw: string | null): ProspectSearchFormState {
  const fallback: ProspectSearchFormState = defaultForm(isAssistantModule.value)
  if (!raw) return fallback
  try {
    const saved: Partial<Record<keyof ProspectSearchFormState, unknown>> = JSON.parse(raw)
    const savedCount: unknown = saved.countPerTrade
    const savedRating: unknown = saved.minimumRating
    return {
      trades: readSavedLabels(saved.trades, PROSPECT_SEARCH_MAXIMUM_TRADES),
      country: typeof saved.country === 'string' ? ProspectCountries.option(saved.country).code : fallback.country,
      cities: readSavedLabels(saved.cities, PROSPECT_SEARCH_MAXIMUM_CITIES),
      countPerTrade: typeof savedCount === 'number' ? clampCountPerTrade(savedCount) : fallback.countPerTrade,
      channel:
        PROSPECT_SEARCH_CHANNEL_OPTIONS.find(
          (option: ProspectSearchChannelOption): boolean => option.value === saved.channel,
        )?.value ?? fallback.channel,
      onlyWithoutWebsite:
        typeof saved.onlyWithoutWebsite === 'boolean' ? saved.onlyWithoutWebsite : fallback.onlyWithoutWebsite,
      minimumRating:
        savedRating === null
          ? null
          : (PROSPECT_SEARCH_MINIMUM_RATING_OPTIONS.find(
              (option: SelectFieldOption<number>): boolean =>
                option.value === savedRating && option.value !== PROSPECT_SEARCH_NO_MINIMUM_RATING,
            )?.value ?? fallback.minimumRating),
    }
  } catch {
    return fallback
  }
}

/** Load the persisted form (client only). */
function loadForm(): void {
  if (import.meta.server) return
  let raw: string | null = null
  try {
    raw = localStorage.getItem(formStorageKey())
  } catch {
    raw = null
  }
  form.value = readSavedForm(raw)
  tradeInput.value = ''
  cityInput.value = ''
}

/** Remember the form for the next search (best-effort). */
function saveForm(): void {
  if (!import.meta.client) return
  try {
    localStorage.setItem(formStorageKey(), JSON.stringify(form.value))
  } catch {
    // Storage full or unavailable: the search still starts.
  }
}

/**
 * Fetch the target verticals once, in the Réceptionniste IA module only (best-effort:
 * the known trades stay offered when the list cannot be loaded).
 * @returns A promise resolved once the verticals are loaded or the attempt failed.
 */
async function loadVerticals(): Promise<void> {
  if (!isAssistantModule.value || verticals.value.length > 0) return
  try {
    verticals.value = await SourcingService.listVerticals()
  } catch {
    verticals.value = []
  }
}

/**
 * Bring a typed count back into what the search accepts.
 * @param count - Count as typed or remembered.
 * @returns A whole number between 1 and the maximum.
 */
function clampCountPerTrade(count: number): number {
  if (!Number.isFinite(count)) return PROSPECT_SEARCH_DEFAULT_COUNT_PER_TRADE
  return Math.min(PROSPECT_SEARCH_MAXIMUM_COUNT_PER_TRADE, Math.max(1, Math.round(count)))
}

/**
 * Whether a trade is already part of the objective, whatever its case or accents.
 * @param trade - Trade label to look for.
 * @returns True when the form already holds it.
 */
function isTradeSelected(trade: string): boolean {
  const folded: string = ProspectSearches.foldLabel(trade)
  return form.value.trades.some((selected: string): boolean => ProspectSearches.foldLabel(selected) === folded)
}

/**
 * Add a trade to the objective, unless it is already there or the search is full.
 * @param trade - Trade as typed or suggested.
 */
function addTrade(trade: string): void {
  const cleaned: string = trade.trim().slice(0, PROSPECT_SEARCH_MAXIMUM_TRADE_LENGTH)
  if (!cleaned || hasMaximumTrades.value || isTradeSelected(cleaned)) return
  form.value.trades = [...form.value.trades, cleaned]
}

/** Add what is typed in the trade field: several trades can be typed at once, separated by commas. */
function addTypedTrades(): void {
  tradeInput.value.split(',').forEach((trade: string): void => addTrade(trade))
  tradeInput.value = ''
}

/**
 * Take a trade out of the objective.
 * @param trade - The trade whose chip was closed.
 */
function removeTrade(trade: string): void {
  form.value.trades = form.value.trades.filter((selected: string): boolean => selected !== trade)
}

/**
 * Add a town to the objective, unless it is already there or the search is full.
 * @param city - Town as typed or suggested.
 */
function addCity(city: string): void {
  const cleaned: string = city.trim().slice(0, PROSPECT_SEARCH_MAXIMUM_CITY_LENGTH)
  const folded: string = ProspectSearches.foldLabel(cleaned)
  const isAlreadySelected: boolean = form.value.cities.some(
    (selected: string): boolean => ProspectSearches.foldLabel(selected) === folded,
  )
  if (!cleaned || hasMaximumCities.value || isAlreadySelected) return
  form.value.cities = [...form.value.cities, cleaned]
}

/**
 * Empty the town field for the next entry, keeping the keyboard in it.
 * @returns A promise resolved once the fresh field is focused.
 */
async function resetCityInput(): Promise<void> {
  cityInput.value = ''
  cityInputRevision.value += 1
  await nextTick()
  if (!hasMaximumCities.value) document.getElementById(CITY_INPUT_ID)?.focus()
}

/** Add the town typed in the field as it is (towns outside France have no suggestion). */
function addTypedCity(): void {
  if (cityInput.value.trim() === '') return
  addCity(cityInput.value)
  resetCityInput()
}

/**
 * Add the town picked in the suggestion list.
 * @param suggestion - The picked town.
 */
function addSuggestedCity(suggestion: CitySuggestion): void {
  addCity(suggestion.nom)
  resetCityInput()
}

/**
 * Take a town out of the objective.
 * @param city - The town whose chip was closed.
 */
function removeCity(city: string): void {
  form.value.cities = form.value.cities.filter((selected: string): boolean => selected !== city)
}

/**
 * Apply the values handed over by the screen that opened the drawer, over the remembered form.
 * @param prefill - Values to apply, if any.
 */
function applyPrefill(prefill: SearchProspectsPrefill | null): void {
  if (!prefill) return
  const country: ProspectCountry | undefined = prefill.country
  if (prefill.category) form.value.trades = [prefill.category]
  if (prefill.city) form.value.cities = [prefill.city]
  if (country) form.value.country = country
}

/**
 * Launch the search described by the form.
 * @returns A promise resolved once the search is created, or the refusal is reported.
 */
async function submit(): Promise<void> {
  addTypedTrades()
  if (cityInput.value.trim() !== '') {
    addCity(cityInput.value)
    cityInput.value = ''
  }
  if (form.value.trades.length === 0) {
    toast.error('Indiquez au moins un métier.')
    return
  }
  form.value.countPerTrade = clampCountPerTrade(Number(form.value.countPerTrade))
  saveForm()
  try {
    await store.startSearch({
      trades: form.value.trades,
      country: form.value.country,
      cities: form.value.cities,
      count_per_trade: form.value.countPerTrade,
      channel: form.value.channel,
      only_without_website: form.value.onlyWithoutWebsite,
      minimum_rating: form.value.minimumRating,
    })
    toast.success('Recherche lancée')
    if (isOnSearchPage.value) emit('close')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur au lancement de la recherche')
  }
}

/**
 * Stop the followed search from the drawer.
 * @returns A promise resolved once the search is stopped, or the failure is reported.
 */
async function cancelSearch(): Promise<void> {
  try {
    await store.cancelSearch()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Impossible d'arrêter la recherche")
  }
}

// Le préremplissage de l'hôte s'applique par-dessus le formulaire sauvegardé.
watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (!open || import.meta.server) return
    loadForm()
    loadVerticals()
    store.loadTradeOptions()
    applyPrefill(props.prefill ?? null)
  },
  { immediate: true },
)

// La pile remplace l'entrée sans fermer le drawer : le watcher `open` ne se redéclenche pas.
watch(
  (): SearchProspectsPrefill | null => props.prefill ?? null,
  (prefill: SearchProspectsPrefill | null): void => {
    if (props.open) applyPrefill(prefill)
  },
  { deep: true },
)
</script>

<style scoped>
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
