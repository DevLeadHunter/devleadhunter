import type { ProductModuleKey } from '~/types/ProductModule'
import type { ModuleSettingsNavEntry, SettingsNavGroup } from '~/types/SettingsNav'

const registeredEntries: Map<string, ModuleSettingsNavEntry> = new Map()

/**
 * The settings pages the product modules add to the « Paramètres » panel (a module's own prices, for instance).
 */
export class SettingsNavRegistry {
  private constructor() {}

  /**
   * Register a module's settings page, or replace the one registered under its path.
   * @param moduleEntry - The page, its module and the group it joins.
   */
  static register(moduleEntry: ModuleSettingsNavEntry): void {
    registeredEntries.set(moduleEntry.entry.to, moduleEntry)
  }

  /**
   * The panel's groups with the pages of the usable modules added at the end of their group.
   * @param groups - The core's groups.
   * @param isModuleUsable - Whether a module's pages show (a module switched off has none).
   * @returns New groups; the core's are left untouched.
   */
  static groupsWith(
    groups: SettingsNavGroup[],
    isModuleUsable: (moduleKey: ProductModuleKey) => boolean,
  ): SettingsNavGroup[] {
    const mergedGroups: SettingsNavGroup[] = groups.map(
      (group: SettingsNavGroup): SettingsNavGroup => ({ ...group, entries: [...group.entries] }),
    )
    for (const moduleEntry of registeredEntries.values()) {
      if (!isModuleUsable(moduleEntry.moduleKey)) {
        continue
      }
      const group: SettingsNavGroup | undefined = mergedGroups.find(
        (candidate: SettingsNavGroup): boolean => candidate.heading === moduleEntry.groupHeading,
      )

      if (group) {
        group.entries.push(moduleEntry.entry)
      } else {
        mergedGroups.push({ heading: moduleEntry.groupHeading, entries: [moduleEntry.entry] })
      }
    }
    return mergedGroups
  }
}
