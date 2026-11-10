import type { DashboardModuleDefinition, DlhModuleKey } from '~/types/UiSidebar'

const registeredModules: Map<DlhModuleKey, DashboardModuleDefinition> = new Map()

/** The product modules the layers plug into the dashboard (switcher, navigation, labels), in registration order. */
export class DashboardModuleRegistry {
  private constructor() {}

  /**
   * Register a module, or replace the one registered under its key.
   * @param definition - The module as the dashboard shows it.
   */
  static register(definition: DashboardModuleDefinition): void {
    registeredModules.set(definition.key, definition)
  }

  /**
   * The module registered under a key.
   * @param moduleKey - The module key, as the API stores it.
   * @returns The module, or null when no layer registered it.
   */
  static find(moduleKey: DlhModuleKey): DashboardModuleDefinition | null {
    return registeredModules.get(moduleKey) ?? null
  }

  /**
   * Every registered module, in registration order.
   * @returns The modules.
   */
  static list(): DashboardModuleDefinition[] {
    return [...registeredModules.values()]
  }

  /**
   * The label a module gives to one of its activity-log categories.
   * @param category - The raw category of the log entry.
   * @returns The label, or null when no module names it.
   */
  static activityCategoryLabel(category: string): string | null {
    for (const definition of registeredModules.values()) {
      const label: string | undefined = definition.activityCategoryLabels?.[category]

      if (label) {
        return label
      }
    }
    return null
  }

  /**
   * The label a module gives to an order product type it sells.
   * @param productType - The order's raw product type.
   * @returns The label, or null when no module names it.
   */
  static orderProductLabel(productType: string): string | null {
    for (const definition of registeredModules.values()) {
      const label: string | undefined = definition.orderProductLabels?.[productType]

      if (label) {
        return label
      }
    }
    return null
  }
}
