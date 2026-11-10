import type {
  CoreDrawerStackEntryKind,
  DrawerKindRegistration,
  DrawerStackEntry,
  ModuleDrawerEntry,
  ModuleDrawerKind,
  RegisteredDrawerKind,
} from '~/types/DrawerStack'

/** The drawers of the core, listed one by one (TypeScript fails when a new kind is left out). */
const CORE_DRAWER_KINDS: Record<CoreDrawerStackEntryKind, true> = {
  prospect: true,
  'prospect-settings': true,
  'send-email': true,
  'send-sms': true,
  'email-log': true,
  'sms-log': true,
  'email-resend': true,
  'email-template': true,
  'email-signatures': true,
  profile: true,
  organization: true,
  'campaign-form': true,
  'add-prospect': true,
  'prospect-search': true,
  'prospect-search-lead': true,
  'campaign-prospects-picker': true,
  'campaign-reply': true,
  'send-policy': true,
  'coverage-filters': true,
  'coverage-prospects': true,
  order: true,
  'finalize-sale': true,
  'user-form': true,
}

const registeredDrawerKinds: Map<string, RegisteredDrawerKind> = new Map()

/** The drawers the product modules add to the persistent drawer stack, which `UiDrawerStackHost` renders. */
export class DrawerKindRegistry {
  private constructor() {}

  /**
   * Register a module drawer, or replace the one registered under its kind.
   * @param registration - The drawer, its module and how to read its props from its entry.
   */
  static register<TKind extends ModuleDrawerKind, TUpdatedValue = never>(
    registration: DrawerKindRegistration<TKind, TUpdatedValue>,
  ): void {
    registeredDrawerKinds.set(registration.kind, registration)
  }

  /**
   * Every registered module drawer.
   * @returns The drawers, in registration order.
   */
  static list(): RegisteredDrawerKind[] {
    return [...registeredDrawerKinds.values()]
  }

  /**
   * The module drawer registered for a kind.
   * @param kind - The entry kind.
   * @returns The drawer, or null when the kind is the core's or nobody registered it.
   */
  static find(kind: string): RegisteredDrawerKind | null {
    return registeredDrawerKinds.get(kind) ?? null
  }

  /**
   * Whether an entry kind has a drawer: one of the core's, or a registered module's.
   * @param kind - The kind read from a stored entry.
   * @returns True when the stack can render it.
   */
  static isKnownKind(kind: string): boolean {
    return kind in CORE_DRAWER_KINDS || registeredDrawerKinds.has(kind)
  }

  /**
   * Whether an entry belongs to a module drawer.
   * @param entry - A stack entry.
   * @returns True when a module registered its kind.
   */
  static isModuleEntry(entry: DrawerStackEntry): entry is ModuleDrawerEntry {
    return registeredDrawerKinds.has(entry.kind)
  }
}
