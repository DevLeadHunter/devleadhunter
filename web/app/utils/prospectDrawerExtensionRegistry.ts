import type { ProductModuleKey } from '~/types/ProductModule'
import type {
  ProspectDrawerPrimaryActionRegistration,
  ProspectDrawerSectionRegistration,
} from '~/types/ProspectDrawerExtension'

const registeredSections: Map<string, ProspectDrawerSectionRegistration> = new Map()

const registeredPrimaryActions: Map<ProductModuleKey, ProspectDrawerPrimaryActionRegistration> = new Map()

/** What the product modules add to the prospect drawer: blocks under « Informations », and the main footer button. */
export class ProspectDrawerExtensionRegistry {
  private constructor() {}

  /**
   * Register a block, or replace the one registered under its key.
   * @param registration - The block, its module and when it shows.
   */
  static registerSection(registration: ProspectDrawerSectionRegistration): void {
    registeredSections.set(registration.key, registration)
  }

  /**
   * Register the main footer button of a module, or replace it.
   * @param registration - The button and its module.
   */
  static registerPrimaryAction(registration: ProspectDrawerPrimaryActionRegistration): void {
    registeredPrimaryActions.set(registration.moduleKey, registration)
  }

  /**
   * Every registered block.
   * @returns The blocks, in registration order.
   */
  static sections(): ProspectDrawerSectionRegistration[] {
    return [...registeredSections.values()]
  }

  /**
   * The main footer button of a module.
   * @param moduleKey - The active module.
   * @returns The button, or null when the module keeps the core's demo-site button.
   */
  static primaryActionOf(moduleKey: ProductModuleKey): ProspectDrawerPrimaryActionRegistration | null {
    return registeredPrimaryActions.get(moduleKey) ?? null
  }
}
