import { existsSync, readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * The Nuxt layers of the optional product modules, as a `nuxt.config.ts` extends them.
 *
 * Each module is pinned by tag in `product-modules.json` and fetched from GitHub like the website templates. To
 * work on a module, clone its repository next to this one and set `DLH_PRODUCT_MODULES_DIR` to the folder that
 * holds the clones: the app then extends the local checkout instead. A local clone whose app folder holds no
 * `nuxt.config` has no layer for that app yet: the module is left out of it (a warning says so).
 *
 * `DLH_PRODUCT_MODULES_DISABLED` leaves modules out: `1` builds an app with no module layer at all, the core alone
 * (it checks that the core never depends on a module's files); a comma-separated list of module keys
 * (`apple-wallet`) leaves only those out, e.g. while another module's layer is half-built.
 */

const repositoryRoot = dirname(fileURLToPath(import.meta.url))

const NUXT_CONFIG_FILE_NAMES = ['nuxt.config.ts', 'nuxt.config.mjs', 'nuxt.config.js']

/**
 * Read the pinned modules.
 *
 * @returns The modules of `product-modules.json`.
 */
function readPinnedModules() {
  const manifest = JSON.parse(readFileSync(join(repositoryRoot, 'product-modules.json'), 'utf8'))
  return manifest.modules
}

/**
 * Whether a folder is a Nuxt layer, i.e. holds a `nuxt.config`.
 *
 * @param {string} folder - The folder to inspect.
 * @returns {boolean} True when one of the Nuxt config files is there.
 */
function isNuxtLayer(folder) {
  return NUXT_CONFIG_FILE_NAMES.some((fileName) => existsSync(join(folder, fileName)))
}

/**
 * The module keys `DLH_PRODUCT_MODULES_DISABLED` leaves out.
 *
 * @returns {{ isEveryModuleDisabled: boolean, disabledKeys: string[] }} Whether every module is left out, else
 *   the keys listed.
 */
function readDisabledModules() {
  const setting = (process.env.DLH_PRODUCT_MODULES_DISABLED ?? '').trim()
  if (setting === '1') return { isEveryModuleDisabled: true, disabledKeys: [] }
  const disabledKeys = setting
    .split(',')
    .map((key) => key.trim())
    .filter((key) => key !== '')
  return { isEveryModuleDisabled: false, disabledKeys }
}

/**
 * The layers of one app, in the order of `product-modules.json`.
 *
 * @param {'web' | 'demo-host'} app - The app whose layers to list.
 * @returns {string[]} A local path per module when `DLH_PRODUCT_MODULES_DIR` holds its clone, a `github:` source
 *   pinned by tag otherwise; the modules `DLH_PRODUCT_MODULES_DISABLED` names are left out (all of them for `1`).
 */
export function productModuleLayers(app) {
  const { isEveryModuleDisabled, disabledKeys } = readDisabledModules()
  if (isEveryModuleDisabled) return []
  const localModulesDirectory = process.env.DLH_PRODUCT_MODULES_DIR
  return readPinnedModules()
    .filter((module) => module.layers.includes(app) && !disabledKeys.includes(module.key))
    .flatMap((module) => {
      const repositoryName = module.repository.split('/')[1]
      if (localModulesDirectory) {
        const localLayer = resolve(localModulesDirectory, repositoryName, app)
        if (existsSync(localLayer)) {
          if (isNuxtLayer(localLayer)) return [localLayer]
          console.warn(`[product-modules] ${repositoryName}/${app} holds no nuxt.config: « ${module.key} » left out.`)
          return []
        }
      }
      return [`github:${module.repository}/${app}#${module.ref}`]
    })
}
