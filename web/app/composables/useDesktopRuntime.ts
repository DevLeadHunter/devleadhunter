import type { ComputedRef } from 'vue'

/**
 * Detect the DevLeadHunter runtime: Tauri desktop shell vs plain browser, and local
 * dev vs a built/packaged app. Client-only, SSR-safe. Also exposes the dev-only
 * prod → local database sync trigger.
 *
 * @returns Desktop + environment detection helpers and the DB-sync trigger.
 */
export function useDesktopRuntime() {
  const isDesktopApp: ComputedRef<boolean> = computed((): boolean => {
    if (!import.meta.client) {
      return false
    }
    const w = window as Window & {
      __TAURI__?: unknown
      __TAURI_INTERNALS__?: unknown
    }
    return Boolean(w.__TAURI__ || w.__TAURI_INTERNALS__)
  })

  // True under the Nuxt dev server (`npm run dev` OR `tauri:dev`), false in any
  // generated/packaged output (prod web, packaged desktop). Vite inlines this at
  // build time, so it reliably separates local development from production.
  const isLocalDev: boolean = import.meta.dev

  // "Local desktop dev only" — the canonical gate for dev-only desktop UI (e.g. the
  // DB-sync button), mirroring GoupixDex's `import.meta.dev && isDesktopApp`.
  const isDesktopDev: ComputedRef<boolean> = computed((): boolean => isLocalDev && isDesktopApp.value)

  // Only the packaged production desktop app should self-update (dev has no valid
  // updater endpoint/signature, so a check there just fails with a spurious panel).
  const isProdDesktop: ComputedRef<boolean> = computed((): boolean => isDesktopApp.value && !isLocalDev)

  /**
   * Pull the prod database into the local dev database via the Tauri
   * `sync_dev_database_from_prod` command (mysqldump → import). Desktop dev only.
   *
   * @returns The Rust command's success summary string.
   * @throws When not running in the desktop app in local dev, or when the sync fails.
   */
  async function syncDevDatabaseFromProd(): Promise<string> {
    if (!import.meta.client || !isDesktopDev.value) {
      throw new Error("La synchro DB n'est disponible que dans l'app desktop, en dev local.")
    }
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke<string>('sync_dev_database_from_prod')
  }

  return { isDesktopApp, isLocalDev, isDesktopDev, isProdDesktop, syncDevDatabaseFromProd }
}
