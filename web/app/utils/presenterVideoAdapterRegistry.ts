import type { ProductModuleKey } from '~/types/ProductModule'
import type { PresenterVideoModuleAdapter, PresenterVideoModuleWording } from '~/types/PresenterVideoConfig'
import { WEBSITES_PRESENTER_VIDEO_WORDING } from '~/constants/presenterVideoWordings'

const registeredAdapters: Map<ProductModuleKey, PresenterVideoModuleAdapter> = new Map()

/** The presenter-video settings of each module: one webcam clip per module, montaged on its own demos. */
export class PresenterVideoAdapterRegistry {
  private constructor() {}

  /**
   * Register a module's adapter, or replace the one registered for it.
   * @param adapter - The module's words, montage and example demos.
   */
  static register(adapter: PresenterVideoModuleAdapter): void {
    registeredAdapters.set(adapter.moduleKey, adapter)
  }

  /**
   * The adapter of a module.
   * @param moduleKey - The module whose clip is shown.
   * @returns Its adapter, or null when the module has no presenter clip.
   */
  static of(moduleKey: ProductModuleKey): PresenterVideoModuleAdapter | null {
    return registeredAdapters.get(moduleKey) ?? null
  }

  /**
   * The words of a module's clip settings.
   * @param moduleKey - The module whose clip is shown.
   * @returns Its words, or the websites module's when it has no adapter.
   */
  static wordingOf(moduleKey: ProductModuleKey): PresenterVideoModuleWording {
    return registeredAdapters.get(moduleKey)?.wording ?? WEBSITES_PRESENTER_VIDEO_WORDING
  }

  /**
   * Every registered adapter.
   * @returns The adapters, in registration order.
   */
  static list(): PresenterVideoModuleAdapter[] {
    return [...registeredAdapters.values()]
  }
}
