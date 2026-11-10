import type { DesktopVideoSubjectKind, DesktopVideoSubjectRelay } from '~/types/DesktopVideoRelay'

const registeredRelays: Map<DesktopVideoSubjectKind, DesktopVideoSubjectRelay> = new Map()

/** The kinds of demo, besides the demo sites, whose prospection video the desktop app builds on request. */
export class DesktopVideoSubjectRegistry {
  private constructor() {}

  /**
   * Register a module's kind of demo, or replace the one registered under its kind.
   * @param relay - How the desktop app finds and builds those videos.
   */
  static register(relay: DesktopVideoSubjectRelay): void {
    registeredRelays.set(relay.kind, relay)
  }

  /**
   * Every registered kind of demo.
   * @returns The relays, in registration order.
   */
  static list(): DesktopVideoSubjectRelay[] {
    return [...registeredRelays.values()]
  }
}
