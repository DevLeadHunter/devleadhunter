<template>
  <div class="flex min-h-full flex-col">
    <div class="mb-5">
      <NuxtLink
        :to="MY_PROSPECTS_PAGE_PATH"
        class="inline-flex cursor-pointer items-center gap-1.5 text-xs font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
      >
        <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
        Mes prospects
      </NuxtLink>
      <h1 class="app-page-title mt-3">Nouvelle recherche</h1>
    </div>

    <UiWizardStepper :model-value="currentStep" :steps="steps" class="mb-6" @update:model-value="goToStep" />

    <div class="flex min-w-0 flex-1 flex-col">
      <div v-if="activeStepKey === 'target'" key="step-target" class="wizard-step space-y-5 pb-20">
        <div class="app-card space-y-5 p-5 @2xl:p-6">
          <div>
            <h2 id="search-trades-title" class="text-base font-semibold text-[var(--app-ink)]">Métiers recherchés</h2>
            <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
              Cochez un ou plusieurs métiers ({{ PROSPECT_SEARCH_MAXIMUM_TRADES }} au maximum) : chacun a son propre
              compte.
            </p>
          </div>

          <div v-if="wavePresets.length > 0" class="space-y-2.5">
            <div
              v-for="preset in wavePresets"
              :key="preset.wave"
              class="flex flex-col gap-1.5 @2xl:flex-row @2xl:items-start @2xl:gap-3"
            >
              <span class="app-label shrink-0 @2xl:w-16 @2xl:pt-1.5" :title="preset.labels.join(', ')">
                Vague {{ preset.wave }}
              </span>
              <UiChipToggleGroup
                v-model="selectedTrades"
                :options="preset.options"
                :label="`Métiers de la vague ${preset.wave}`"
                class="min-w-0 flex-1"
              />
            </div>
          </div>
          <UiChipToggleGroup
            v-else-if="knownTradeOptions.length > 0"
            v-model="selectedTrades"
            :options="knownTradeOptions"
            label="Métiers connus"
          />

          <div>
            <label for="search-trade" class="app-label mb-1.5 block">Autre métier</label>
            <div class="flex gap-2 @2xl:max-w-md">
              <div class="relative min-w-0 flex-1">
                <UIcon
                  name="i-lucide-hammer"
                  class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
                />
                <input
                  id="search-trade"
                  v-model="tradeInput"
                  type="text"
                  autocomplete="off"
                  :placeholder="isAssistantModule ? 'Couvreur, carrosserie…' : 'Serrurier, menuisier…'"
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
            <UiRemovableChipList
              v-if="customTrades.length > 0"
              :labels="customTrades"
              class="mt-2"
              @remove="removeTrade"
            />
          </div>

          <div class="border-t border-[var(--app-line-soft)] pt-5">
            <label for="search-count" class="app-label mb-1.5 block">Nombre par métier</label>
            <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
              <input
                id="search-count"
                v-model.number="form.countPerTrade"
                type="number"
                inputmode="numeric"
                min="1"
                :max="PROSPECT_SEARCH_MAXIMUM_COUNT_PER_TRADE"
                step="1"
                class="app-input w-28"
                @blur="clampCountPerTrade"
              />
              <p class="text-sm text-[var(--app-ink-soft)]">{{ wantedProspectsLabel }}</p>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="activeStepKey === 'zone'" key="step-zone" class="wizard-step space-y-5 pb-20">
        <div class="app-card space-y-5 p-5 @2xl:p-6">
          <div>
            <h2 id="search-country-title" class="text-base font-semibold text-[var(--app-ink)]">Pays</h2>
            <div class="mt-3 flex flex-wrap gap-1.5" role="radiogroup" aria-labelledby="search-country-title">
              <button
                v-for="countryOption in ProspectCountries.catalog"
                :key="countryOption.code"
                type="button"
                role="radio"
                :aria-checked="countryOption.code === form.country"
                class="flex cursor-pointer items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors pointer-coarse:min-h-10 pointer-coarse:px-3.5 pointer-coarse:text-sm"
                :class="
                  countryOption.code === form.country
                    ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-bg)]'
                    : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)]'
                "
                @click="form.country = countryOption.code"
              >
                <UiCountryFlag :code="countryOption.code" :hide-france="false" size="default" />
                <span>{{ countryOption.label }}</span>
              </button>
            </div>
          </div>

          <div class="border-t border-[var(--app-line-soft)] pt-5">
            <label :for="CITY_INPUT_ID" class="text-base font-semibold text-[var(--app-ink)]">
              Villes <span class="text-sm font-normal text-[var(--app-ink-soft)]">(facultatif)</span>
            </label>
            <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
              Laissez vide : l'app choisit les villes et en change jusqu'au compte.
            </p>
            <UiRemovableChipList
              v-if="form.cities.length > 0"
              :labels="form.cities"
              class="mt-3"
              @remove="removeCity"
            />
            <div class="mt-3 flex gap-2 @2xl:max-w-md">
              <div class="min-w-0 flex-1" @keydown.enter.prevent="addTypedCity">
                <UiCityAutocompleteInput
                  :key="cityInputRevision"
                  v-model="cityInput"
                  :input-id="CITY_INPUT_ID"
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
            <p v-if="form.country !== ProspectCountries.france.code" class="mt-2 text-xs text-[var(--app-ink-soft)]">
              Hors de France, tapez le nom de la ville puis « Ajouter » : les suggestions ne couvrent que les communes
              françaises.
            </p>
          </div>
        </div>
      </div>

      <div v-else-if="activeStepKey === 'criteria'" key="step-criteria" class="wizard-step space-y-5 pb-20">
        <div class="app-card space-y-5 p-5 @2xl:p-6">
          <div>
            <h2 id="search-channel-title" class="text-base font-semibold text-[var(--app-ink)]">Comment les joindre</h2>
            <UiRadioCardGroup
              v-model="form.channel"
              :options="PROSPECT_SEARCH_CHANNEL_OPTIONS"
              labelled-by="search-channel-title"
              class="mt-3 @3xl:grid-cols-3"
            />
          </div>

          <div class="border-t border-[var(--app-line-soft)] pt-5">
            <p class="app-label mb-2">Site web</p>
            <UiCheckbox
              id="search-only-without-website"
              v-model="form.onlyWithoutWebsite"
              label="Uniquement sans site web"
            />
            <p class="mt-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
              {{
                isAssistantModule && !form.onlyWithoutWebsite
                  ? 'La réceptionniste vit sur sa propre page : avec ou sans site, un pro qui reçoit des demandes est une cible.'
                  : 'Un site en panne ou un mini-site annuaire compte comme « sans site ».'
              }}
            </p>
          </div>
        </div>

        <div class="app-card p-5 @2xl:p-6">
          <h2 id="search-validation-title" class="text-base font-semibold text-[var(--app-ink)]">Validation</h2>
          <p class="mt-1 text-sm text-[var(--app-ink-soft)]">Qui décide qu'un lead entre dans vos prospects.</p>
          <UiRadioCardGroup
            v-model="form.validationMode"
            :options="PROSPECT_SEARCH_VALIDATION_OPTIONS"
            labelled-by="search-validation-title"
            class="mt-3 @2xl:grid-cols-2"
          />
        </div>
      </div>

      <div v-else key="step-launch" class="wizard-step space-y-5 pb-20">
        <div class="app-card grid gap-x-10 gap-y-6 p-5 @2xl:p-6 @4xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <section aria-labelledby="search-recap-title">
            <h2 id="search-recap-title" class="text-base font-semibold text-[var(--app-ink)]">Objectif</h2>
            <dl class="mt-2 divide-y divide-[var(--app-line-soft)]">
              <div
                v-for="row in recapRows"
                :key="row.label"
                class="flex flex-col gap-0.5 py-2.5 @2xl:flex-row @2xl:items-baseline @2xl:gap-6"
              >
                <dt class="app-label @2xl:w-36 @2xl:shrink-0">{{ row.label }}</dt>
                <dd class="min-w-0 text-sm break-words">
                  <span class="font-medium text-[var(--app-ink)]">{{ row.value }}</span>
                  <span v-if="row.detail" class="mt-0.5 block text-xs leading-relaxed text-[var(--app-ink-soft)]">
                    {{ row.detail }}
                  </span>
                </dd>
              </div>
            </dl>
          </section>

          <section aria-labelledby="search-estimate-title">
            <h2 id="search-estimate-title" class="text-base font-semibold text-[var(--app-ink)]">Estimation</h2>
            <dl class="mt-2 divide-y divide-[var(--app-line-soft)]">
              <div
                v-for="row in estimateRows"
                :key="row.label"
                class="flex items-baseline justify-between gap-6 py-2.5"
              >
                <dt class="app-label shrink-0">{{ row.label }}</dt>
                <dd class="font-label min-w-0 text-right text-sm text-[var(--app-ink)] tabular-nums">
                  {{ row.value }}
                </dd>
              </div>
            </dl>
            <ul class="mt-3 space-y-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
              <li class="flex items-start gap-2">
                <UIcon name="i-lucide-shield-check" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>Les prospects déjà connus ne sont jamais repris.</span>
              </li>
              <li v-if="store.isQueueFull" class="flex items-start gap-2 text-[var(--app-accent-ink)]">
                <UIcon name="i-lucide-circle-alert" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>
                  La file d'attente est pleine : {{ PROSPECT_SEARCH_MAXIMUM_QUEUED_SEARCHES }} recherches attendent
                  déjà. Retirez-en une ou attendez la fin de celle en cours.
                </span>
              </li>
              <li v-else-if="queueNotice" class="flex items-start gap-2">
                <UIcon name="i-lucide-list-ordered" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>{{ queueNotice }}</span>
              </li>
            </ul>
            <button
              v-if="store.isSearchRunningOnServer"
              type="button"
              class="app-btn-secondary mt-3 h-8 min-h-8 px-3 text-xs pointer-coarse:min-h-11 pointer-coarse:text-sm"
              @click="openSearchFollowUp"
            >
              <UIcon name="i-lucide-panel-right-open" class="h-3.5 w-3.5" />
              {{ store.queuedSearches.length > 0 ? 'Voir la file' : 'Suivre la recherche en cours' }}
            </button>
          </section>
        </div>
      </div>

      <!-- Collée au bas de la zone qui défile : le rembourrage du `main` la pose juste au-dessus de la barre d'onglets
           (ou de la zone sûre), sans recompter cette dernière ; sur téléphone « Continuer » prend la place de « Précédent ». -->
      <div
        class="sticky bottom-0 z-10 mt-auto flex items-center gap-2 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)]/90 p-1.5 shadow-lg backdrop-blur sm:justify-between sm:gap-3 sm:px-3 sm:py-2"
      >
        <button
          v-if="currentStep > 1"
          type="button"
          class="app-btn-secondary h-11 sm:h-9"
          :disabled="store.isStarting"
          @click="goToStep(currentStep - 1)"
        >
          <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />Précédent
        </button>
        <span v-else class="hidden sm:block" />
        <button
          v-if="currentStep < steps.length"
          type="button"
          class="app-btn-primary h-11 flex-1 sm:h-9 sm:flex-none"
          :disabled="!canContinue"
          @click="goToStep(currentStep + 1)"
        >
          Continuer<UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
        </button>
        <button
          v-else
          type="button"
          :class="['app-btn-primary h-11 flex-1 sm:h-9 sm:flex-none', canLaunch && 'app-btn-celebrate']"
          :disabled="!canLaunch"
          :title="store.isQueueFull ? 'La file d’attente est pleine' : undefined"
          @click="launch"
        >
          <UIcon
            :name="
              store.isStarting
                ? 'i-lucide-loader-circle'
                : store.isSearchRunningOnServer
                  ? 'i-lucide-list-plus'
                  : 'i-lucide-search'
            "
            :class="['h-3.5 w-3.5', store.isStarting && 'animate-spin']"
          />
          {{ launchLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref, WritableComputedRef } from 'vue'
import type { LocationQueryValue } from 'vue-router'
import type { ProspectCountryOption } from '~/utils/prospectCountries'
import type { CitySuggestion } from '~/types/CityAutocompleteInput'
import type { UseDashboardScrollReturn, UseToastReturn } from '~/types/Composables'
import type {
  ProspectSearchDetail,
  ProspectSearchSummary,
  ProspectSearchTradeOption,
  ProspectSearchValidationOption,
} from '~/types/ProspectSearch'
import type {
  ProspectSearchFormState,
  ProspectSearchRecapRow,
  ProspectSearchStepDefinition,
  ProspectSearchStepKey,
  ProspectSearchWaveOptions,
} from '~/types/ProspectSearchCreatePage'
import type { SelectFieldOption } from '~/types/SelectField'
import type { SourcingVertical } from '~/types/Sourcing'
import type { UiWizardStep } from '~/types/UiWizardStepper'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useDashboardScroll } from '~/composables/useDashboardScroll'
import { useToast } from '~/composables/useToast'
import {
  MY_PROSPECTS_PAGE_PATH,
  PROSPECT_SEARCH_CHANNEL_LABELS,
  PROSPECT_SEARCH_CHANNEL_OPTIONS,
  PROSPECT_SEARCH_DURATION_LABEL,
  PROSPECT_SEARCH_MAXIMUM_CITIES,
  PROSPECT_SEARCH_MAXIMUM_CITY_LENGTH,
  PROSPECT_SEARCH_MAXIMUM_COUNT_PER_TRADE,
  PROSPECT_SEARCH_MAXIMUM_QUEUED_SEARCHES,
  PROSPECT_SEARCH_MAXIMUM_TRADE_LENGTH,
  PROSPECT_SEARCH_MAXIMUM_TRADES,
  PROSPECT_SEARCH_TUNNEL_STEPS,
  PROSPECT_SEARCH_VALIDATION_OPTIONS,
} from '~/constants/prospectSearch'
import { SourcingService } from '~/services/sourcingService'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useModuleStore } from '~/stores/moduleStore'
import { useProspectSearchStore } from '~/stores/prospectSearch'
import { ProspectCountries } from '~/utils/prospectCountries'
import { ProspectSearchForm } from '~/utils/prospectSearchForm'
import { ProspectSearches } from '~/utils/prospectSearches'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const store: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()
const moduleStore: ReturnType<typeof useModuleStore> = useModuleStore()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
const route: ReturnType<typeof useRoute> = useRoute()
const toast: UseToastReturn = useToast()
const { scrollToTop }: UseDashboardScrollReturn = useDashboardScroll()

const CITY_INPUT_ID: string = 'search-city'

const steps: UiWizardStep[] = PROSPECT_SEARCH_TUNNEL_STEPS.map(
  (step: ProspectSearchStepDefinition, index: number): UiWizardStep => ({
    id: index + 1,
    label: step.label,
    hint: step.hint,
  }),
)

const currentStep: Ref<number> = ref(1)
const verticals: Ref<SourcingVertical[]> = ref([])
const form: Ref<ProspectSearchFormState> = ref(ProspectSearchForm.defaults(moduleStore.activeKey === 'ai-assistant'))
const tradeInput: Ref<string> = ref('')
const cityInput: Ref<string> = ref('')
const cityInputRevision: Ref<number> = ref(0)

const isAssistantModule: ComputedRef<boolean> = computed((): boolean => moduleStore.activeKey === 'ai-assistant')

const activeStepKey: ComputedRef<ProspectSearchStepKey> = computed(
  (): ProspectSearchStepKey => PROSPECT_SEARCH_TUNNEL_STEPS[currentStep.value - 1]?.key ?? 'target',
)

const knownTradeOptions: ComputedRef<SelectFieldOption[]> = computed((): SelectFieldOption[] =>
  store.tradeOptions.map(
    (trade: ProspectSearchTradeOption): SelectFieldOption => ({ value: trade.label, label: trade.label }),
  ),
)

const wavePresets: ComputedRef<ProspectSearchWaveOptions[]> = computed((): ProspectSearchWaveOptions[] => {
  if (!isAssistantModule.value) return []
  const presetsByWave: Map<number, ProspectSearchWaveOptions> = new Map()
  for (const vertical of verticals.value) {
    const preset: ProspectSearchWaveOptions = presetsByWave.get(vertical.wave) ?? {
      wave: vertical.wave,
      labels: [],
      options: [],
    }
    preset.labels.push(vertical.label)
    for (const searchTerm of vertical.search_terms) {
      preset.options.push({ value: searchTerm, label: searchTerm })
    }
    presetsByWave.set(vertical.wave, preset)
  }
  return [...presetsByWave.values()].sort(
    (firstPreset: ProspectSearchWaveOptions, secondPreset: ProspectSearchWaveOptions): number =>
      firstPreset.wave - secondPreset.wave,
  )
})

const tradesOfferedAsChips: ComputedRef<string[]> = computed((): string[] => {
  if (wavePresets.value.length === 0) {
    return knownTradeOptions.value.map((option: SelectFieldOption): string => option.value)
  }
  const waveTrades: string[] = []
  for (const preset of wavePresets.value) {
    for (const option of preset.options) waveTrades.push(option.value)
  }
  return waveTrades
})

const customTrades: ComputedRef<string[]> = computed((): string[] =>
  form.value.trades.filter((trade: string): boolean => !tradesOfferedAsChips.value.includes(trade)),
)

const hasMaximumTrades: ComputedRef<boolean> = computed(
  (): boolean => form.value.trades.length >= PROSPECT_SEARCH_MAXIMUM_TRADES,
)

const hasMaximumCities: ComputedRef<boolean> = computed(
  (): boolean => form.value.cities.length >= PROSPECT_SEARCH_MAXIMUM_CITIES,
)

const selectedTrades: WritableComputedRef<string[]> = computed({
  get: (): string[] => form.value.trades,
  set: (trades: string[]): void => {
    if (trades.length > PROSPECT_SEARCH_MAXIMUM_TRADES) {
      toast.info(`${PROSPECT_SEARCH_MAXIMUM_TRADES} métiers au maximum par recherche.`)
      return
    }
    form.value.trades = trades
  },
})

const countPerTrade: ComputedRef<number> = computed((): number =>
  ProspectSearchForm.clampCountPerTrade(Number(form.value.countPerTrade)),
)

const wantedProspectCount: ComputedRef<number> = computed((): number => countPerTrade.value * form.value.trades.length)

const wantedProspectsLabel: ComputedRef<string> = computed((): string => {
  const tradeCount: number = form.value.trades.length
  if (tradeCount === 0) return `De 1 à ${PROSPECT_SEARCH_MAXIMUM_COUNT_PER_TRADE} prospects pour chaque métier coché.`
  if (tradeCount > 1)
    return `${tradeCount} métiers × ${countPerTrade.value} = ${wantedProspectCount.value} prospects visés.`
  if (countPerTrade.value > 1) return `${countPerTrade.value} prospects visés.`
  return '1 prospect visé.'
})

const recapRows: ComputedRef<ProspectSearchRecapRow[]> = computed((): ProspectSearchRecapRow[] => {
  const hasSeveralTrades: boolean = form.value.trades.length > 1
  const hasChosenCities: boolean = form.value.cities.length > 0
  const validation: ProspectSearchValidationOption | undefined = PROSPECT_SEARCH_VALIDATION_OPTIONS.find(
    (option: ProspectSearchValidationOption): boolean => option.value === form.value.validationMode,
  )
  return [
    { label: 'Métiers', value: form.value.trades.join(', ') },
    {
      label: 'Nombre',
      value: `${countPerTrade.value} par métier`,
      detail: hasSeveralTrades ? `Soit ${wantedProspectCount.value} prospects visés au total.` : undefined,
    },
    {
      label: 'Zone',
      value: ProspectCountries.option(form.value.country).label,
      detail: hasChosenCities ? form.value.cities.join(', ') : "L'app choisit les villes et en change jusqu'au compte.",
    },
    { label: 'Contact', value: PROSPECT_SEARCH_CHANNEL_LABELS[form.value.channel] },
    { label: 'Site web', value: form.value.onlyWithoutWebsite ? 'Uniquement sans site web' : 'Avec ou sans site web' },
    { label: 'Validation', value: validation?.label ?? '', detail: validation?.description },
  ]
})

const queueNotice: ComputedRef<string | null> = computed((): string | null => {
  const runningSearch: ProspectSearchSummary | null = store.activeSearch
  if (!store.isSearchRunningOnServer || runningSearch === null) return null
  const runningTrades: string = ProspectSearches.tradesInWords(runningSearch)
  const queuedCount: number = store.queuedSearches.length
  if (queuedCount === 0) {
    return `Une recherche tourne déjà (${runningTrades}) : celle-ci démarrera toute seule juste après.`
  }
  const waitingSearches: string = queuedCount > 1 ? `${queuedCount} autres attendent` : '1 autre attend'
  return `Une recherche tourne déjà (${runningTrades}) et ${waitingSearches} : celle-ci démarrera toute seule à leur suite.`
})

const startLabel: ComputedRef<string> = computed((): string => {
  if (!store.isSearchRunningOnServer) return 'tout de suite'
  if (store.isQueueFull) return 'file pleine'
  const searchesAhead: number = store.queuedSearches.length + 1
  return searchesAhead > 1 ? `après ${searchesAhead} recherches` : 'après celle en cours'
})

const estimateRows: ComputedRef<ProspectSearchRecapRow[]> = computed((): ProspectSearchRecapRow[] => {
  const maximumRequestCount: number = ProspectSearchForm.maximumRequestCount(form.value)
  return [
    { label: 'Démarrage', value: startLabel.value },
    { label: 'Requêtes', value: `au plus ${maximumRequestCount.toLocaleString('fr-FR')}` },
    { label: 'Coût', value: `au plus env. ${ProspectSearches.dollarsLabel(maximumRequestCount)}` },
    { label: 'Durée', value: PROSPECT_SEARCH_DURATION_LABEL },
  ]
})

const canContinue: ComputedRef<boolean> = computed((): boolean => {
  if (activeStepKey.value !== 'target') return true
  return form.value.trades.length > 0 || tradeInput.value.trim() !== ''
})

const canLaunch: ComputedRef<boolean> = computed(
  (): boolean => form.value.trades.length > 0 && !store.isStarting && !store.isQueueFull,
)

const launchLabel: ComputedRef<string> = computed((): string => {
  if (store.isStarting) return 'Lancement…'
  return store.isSearchRunningOnServer ? 'Ajouter à la file' : 'Lancer la recherche'
})

/**
 * Write a trade the way its chip spells it, so a typed « plombier » ticks the « Plombier » chip.
 * @param trade - Trade as typed, remembered or handed over.
 * @returns The spelling of the matching chip, else the trade as given.
 */
function findChipSpelling(trade: string): string {
  const comparableTrade: string = ProspectSearches.foldLabel(trade)
  const matchingChip: string | undefined = tradesOfferedAsChips.value.find(
    (chipTrade: string): boolean => ProspectSearches.foldLabel(chipTrade) === comparableTrade,
  )
  return matchingChip ?? trade
}

/**
 * Whether a trade is already part of the objective, whatever its case or accents.
 * @param trade - Trade label to look for.
 * @returns True when the form already holds it.
 */
function isTradeSelected(trade: string): boolean {
  const comparableTrade: string = ProspectSearches.foldLabel(trade)
  return form.value.trades.some((selected: string): boolean => ProspectSearches.foldLabel(selected) === comparableTrade)
}

/**
 * Add a trade to the objective, unless it is already there or the search is full.
 * @param trade - Trade as typed or handed over.
 */
function addTrade(trade: string): void {
  const cleanedTrade: string = trade.trim().slice(0, PROSPECT_SEARCH_MAXIMUM_TRADE_LENGTH)
  if (!cleanedTrade || hasMaximumTrades.value || isTradeSelected(cleanedTrade)) return
  form.value.trades = [...form.value.trades, findChipSpelling(cleanedTrade)]
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

/** Bring the typed count back into what a search accepts. */
function clampCountPerTrade(): void {
  form.value.countPerTrade = countPerTrade.value
}

/**
 * Add a town to the objective, unless it is already there or the search is full.
 * @param city - Town as typed or suggested.
 */
function addCity(city: string): void {
  const cleanedCity: string = city.trim().slice(0, PROSPECT_SEARCH_MAXIMUM_CITY_LENGTH)
  const comparableCity: string = ProspectSearches.foldLabel(cleanedCity)
  const isAlreadySelected: boolean = form.value.cities.some(
    (selected: string): boolean => ProspectSearches.foldLabel(selected) === comparableCity,
  )
  if (!cleanedCity || hasMaximumCities.value || isAlreadySelected) return
  form.value.cities = [...form.value.cities, cleanedCity]
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

/** Take in what is still typed in the trade and town fields, so nothing is lost when the step changes. */
function addPendingEntries(): void {
  addTypedTrades()
  if (cityInput.value.trim() !== '') {
    addCity(cityInput.value)
    cityInput.value = ''
  }
  clampCountPerTrade()
}

/**
 * Show a step and bring the page back to its top.
 * @param step - Target step (1-based).
 */
function goToStep(step: number): void {
  addPendingEntries()
  currentStep.value = step
  scrollToTop()
}

/** Load the remembered form of the active module (client only). */
function loadForm(): void {
  if (import.meta.server) return
  let raw: string | null = null
  try {
    raw = localStorage.getItem(ProspectSearchForm.storageKey(isAssistantModule.value))
  } catch {
    raw = null
  }
  form.value = ProspectSearchForm.fromStorage(raw, isAssistantModule.value)
}

/** Remember the form for the next search (best-effort). */
function saveForm(): void {
  if (!import.meta.client) return
  try {
    localStorage.setItem(ProspectSearchForm.storageKey(isAssistantModule.value), JSON.stringify(form.value))
  } catch {
    // Storage full or unavailable: the search still starts.
  }
}

/**
 * Read one value of the page query.
 * @param value - Raw query value, possibly repeated.
 * @returns The first non-empty string, or null.
 */
function readQueryValue(value: LocationQueryValue | LocationQueryValue[] | undefined): string | null {
  const firstValue: LocationQueryValue | undefined = Array.isArray(value) ? value[0] : value
  if (typeof firstValue !== 'string') return null
  return firstValue.trim() === '' ? null : firstValue.trim()
}

/** Apply the trade, town and country another screen handed over through the URL, over the remembered form. */
function applyQueryPrefill(): void {
  const category: string | null = readQueryValue(route.query.category)
  const city: string | null = readQueryValue(route.query.city)
  const countryCode: string | null = readQueryValue(route.query.country)
  const country: ProspectCountryOption | undefined = ProspectCountries.catalog.find(
    (option: ProspectCountryOption): boolean => option.code === countryCode?.toUpperCase(),
  )
  if (category) form.value.trades = [findChipSpelling(category.slice(0, PROSPECT_SEARCH_MAXIMUM_TRADE_LENGTH))]
  if (city) form.value.cities = [city.slice(0, PROSPECT_SEARCH_MAXIMUM_CITY_LENGTH)]
  if (country) form.value.country = country.code
}

/** Give every chosen trade the spelling of its chip, once the chips are known. */
function alignTradesOnChipSpelling(): void {
  const alignedTrades: string[] = []
  for (const trade of form.value.trades) {
    const chipSpelling: string = findChipSpelling(trade)
    if (!alignedTrades.includes(chipSpelling)) alignedTrades.push(chipSpelling)
  }
  const hasSameTrades: boolean =
    alignedTrades.length === form.value.trades.length &&
    alignedTrades.every((trade: string, position: number): boolean => trade === form.value.trades[position])
  if (!hasSameTrades) form.value.trades = alignedTrades
}

/**
 * Fetch the target verticals once, in the Réceptionniste IA module only; the known trades stay offered on failure.
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

/** Open the follow-up drawer: the search at work, and the queue behind it. */
function openSearchFollowUp(): void {
  drawerStack.push({ kind: 'prospect-search' })
}

/**
 * Launch the search, or queue it behind the one at work, then hand over to the prospects page: its « À valider »
 * tab, with the search drawer open.
 * @returns A promise resolved once the search is created and followed, or the refusal is reported.
 */
async function launch(): Promise<void> {
  addPendingEntries()
  if (form.value.trades.length === 0) {
    toast.error('Indiquez au moins un métier.')
    goToStep(1)
    return
  }
  saveForm()
  let created: ProspectSearchDetail
  try {
    created = await store.startSearch(ProspectSearchForm.toPayload(form.value))
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur au lancement de la recherche')
    return
  }
  toast.success(
    created.status === 'queued'
      ? 'Recherche ajoutée à la file : elle démarrera toute seule après celle en cours'
      : 'Recherche lancée',
  )
  store.requestPendingTab()
  // The page first, the drawer after: opening a drawer adds a history entry that would cut the navigation short.
  await navigateTo(MY_PROSPECTS_PAGE_PATH)
  drawerStack.closeAll()
  drawerStack.push({ kind: 'prospect-search' })
}

watch(tradesOfferedAsChips, alignTradesOnChipSpelling)

watch(isAssistantModule, (): void => {
  loadForm()
  applyQueryPrefill()
  loadVerticals()
})

onMounted((): void => {
  loadForm()
  applyQueryPrefill()
  store.loadTradeOptions()
  loadVerticals()
})
</script>

<style scoped>
.wizard-step {
  animation: wizard-step-in 0.3s ease;
}
@keyframes wizard-step-in {
  from {
    opacity: 0;
    transform: translateX(18px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .wizard-step {
    animation: none;
  }
}
</style>
