/*
 * Dev orchestrator for the DevLeadHunter desktop app.
 *
 * Tauri's `beforeDevCommand` runs this so a single `npm run tauri:dev` boots
 * BOTH the web app (port 1420) and the local demo-host (port 3001) that powers
 * the template-preview iframe — no server to start by hand, local or prod.
 *
 * We call concurrently's programmatic API instead of an inline shell string in
 * tauri.conf.json on purpose: on Windows, cmd.exe mangles the nested quotes of
 * `concurrently "cmd a" "cmd b"`, splitting every word into its own command.
 */
import concurrently from 'concurrently'

// eslint-disable-next-line @typescript-eslint/typedef
const { result } = concurrently(
  [
    {
      command: 'cross-env NUXT_DESKTOP_BUILD=1 nuxt dev --port 1420',
      name: 'web',
      prefixColor: 'cyan',
    },
    {
      command: 'npm --prefix ../demo-host run dev',
      name: 'demo',
      prefixColor: 'magenta',
    },
  ],
  {
    prefix: 'name',
    restartTries: 0,
  },
)

// demo-host is best-effort: if it cannot start (e.g. port 3001 already in use)
// the web app must still launch, so swallow the rejection rather than crash.
result.catch(() => {})
