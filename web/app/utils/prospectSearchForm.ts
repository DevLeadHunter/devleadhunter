import type {
  ProspectSearchChannelOption,
  ProspectSearchCreatePayload,
  ProspectSearchValidationOption,
} from '~/types/ProspectSearch'
import type { ProspectSearchFormState } from '~/types/ProspectSearchCreatePage'
import {
  PROSPECT_SEARCH_BASE_REQUEST_COUNT,
  PROSPECT_SEARCH_CHANNEL_OPTIONS,
  PROSPECT_SEARCH_DEFAULT_COUNT_PER_TRADE,
  PROSPECT_SEARCH_DEFAULT_VALIDATION_MODE,
  PROSPECT_SEARCH_MAXIMUM_CITIES,
  PROSPECT_SEARCH_MAXIMUM_COUNT_PER_TRADE,
  PROSPECT_SEARCH_MAXIMUM_TRADES,
  PROSPECT_SEARCH_REQUESTS_PER_WANTED_PROSPECT,
  PROSPECT_SEARCH_VALIDATION_OPTIONS,
} from '~/constants/prospectSearch'
import { ProspectCountries } from '~/utils/prospectCountries'

const FORM_STORAGE_KEY: string = 'devleadhunter-prospect-search-form'

/** The objective form of a prospect search: its defaults, what is remembered of it, what it costs. */
export class ProspectSearchForm {
  private constructor() {}

  /**
   * Build a fresh form: the Réceptionniste IA takes pros with or without a site, the site module only those without.
   * @param isForAssistantModule - Whether the form is opened from the Réceptionniste IA module.
   * @returns The default objective.
   */
  static defaults(isForAssistantModule: boolean): ProspectSearchFormState {
    return {
      trades: [],
      country: ProspectCountries.france.code,
      cities: [],
      countPerTrade: PROSPECT_SEARCH_DEFAULT_COUNT_PER_TRADE,
      channel: 'email',
      onlyWithoutWebsite: !isForAssistantModule,
      validationMode: PROSPECT_SEARCH_DEFAULT_VALIDATION_MODE,
    }
  }

  /**
   * Storage key of the remembered form: one per module, so each keeps its own defaults.
   * @param isForAssistantModule - Whether the form belongs to the Réceptionniste IA module.
   * @returns The localStorage key.
   */
  static storageKey(isForAssistantModule: boolean): string {
    return isForAssistantModule ? `${FORM_STORAGE_KEY}:ai-assistant` : FORM_STORAGE_KEY
  }

  /**
   * Rebuild the form from what was remembered, field by field: a stale or damaged entry falls back to the default.
   * @param raw - Serialized form read from the storage.
   * @param isForAssistantModule - Whether the form belongs to the Réceptionniste IA module.
   * @returns A valid form.
   */
  static fromStorage(raw: string | null, isForAssistantModule: boolean): ProspectSearchFormState {
    const fallback: ProspectSearchFormState = ProspectSearchForm.defaults(isForAssistantModule)
    if (!raw) return fallback
    try {
      const saved: Partial<Record<keyof ProspectSearchFormState, unknown>> = JSON.parse(raw)
      const savedCount: unknown = saved.countPerTrade
      return {
        trades: ProspectSearchForm.readSavedLabels(saved.trades, PROSPECT_SEARCH_MAXIMUM_TRADES),
        country: typeof saved.country === 'string' ? ProspectCountries.option(saved.country).code : fallback.country,
        cities: ProspectSearchForm.readSavedLabels(saved.cities, PROSPECT_SEARCH_MAXIMUM_CITIES),
        countPerTrade:
          typeof savedCount === 'number' ? ProspectSearchForm.clampCountPerTrade(savedCount) : fallback.countPerTrade,
        channel:
          PROSPECT_SEARCH_CHANNEL_OPTIONS.find(
            (option: ProspectSearchChannelOption): boolean => option.value === saved.channel,
          )?.value ?? fallback.channel,
        onlyWithoutWebsite:
          typeof saved.onlyWithoutWebsite === 'boolean' ? saved.onlyWithoutWebsite : fallback.onlyWithoutWebsite,
        validationMode:
          PROSPECT_SEARCH_VALIDATION_OPTIONS.find(
            (option: ProspectSearchValidationOption): boolean => option.value === saved.validationMode,
          )?.value ?? fallback.validationMode,
      }
    } catch {
      return fallback
    }
  }

  /**
   * Bring a typed count back into what the search accepts.
   * @param count - Count as typed or remembered.
   * @returns A whole number between 1 and the maximum.
   */
  static clampCountPerTrade(count: number): number {
    if (!Number.isFinite(count)) return PROSPECT_SEARCH_DEFAULT_COUNT_PER_TRADE
    return Math.min(PROSPECT_SEARCH_MAXIMUM_COUNT_PER_TRADE, Math.max(1, Math.round(count)))
  }

  /**
   * The most requests a search may spend before it stops by itself.
   * @param form - The objective.
   * @returns The request budget.
   */
  static maximumRequestCount(form: ProspectSearchFormState): number {
    return (
      PROSPECT_SEARCH_BASE_REQUEST_COUNT +
      PROSPECT_SEARCH_REQUESTS_PER_WANTED_PROSPECT *
        ProspectSearchForm.clampCountPerTrade(form.countPerTrade) *
        form.trades.length
    )
  }

  /**
   * The objective as the API expects it; the Google rating no longer filters anyone out.
   * @param form - The objective as written in the tunnel.
   * @returns The body of the search creation.
   */
  static toPayload(form: ProspectSearchFormState): ProspectSearchCreatePayload {
    return {
      trades: form.trades,
      country: form.country,
      cities: form.cities,
      count_per_trade: ProspectSearchForm.clampCountPerTrade(form.countPerTrade),
      channel: form.channel,
      only_without_website: form.onlyWithoutWebsite,
      minimum_rating: null,
      validation_mode: form.validationMode,
    }
  }

  /**
   * Keep the usable labels of a remembered list.
   * @param saved - Value read from the storage, of unknown shape.
   * @param maximumCount - How many entries the search accepts.
   * @returns The non-empty strings, capped.
   */
  private static readSavedLabels(saved: unknown, maximumCount: number): string[] {
    if (!Array.isArray(saved)) return []
    return saved
      .filter((label: unknown): label is string => typeof label === 'string' && label.trim() !== '')
      .slice(0, maximumCount)
  }
}
