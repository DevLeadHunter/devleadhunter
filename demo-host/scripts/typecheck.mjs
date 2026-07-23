import { spawnSync } from 'node:child_process'

/**
 * Type-checks demo-host without failing on its template layers.
 *
 * `vue-tsc --noEmit` silently checks nothing here: tsconfig.json holds `files: []` plus
 * project references, and only `--build` follows those references. Building, though, also
 * pulls in the template layers that Nuxt fetches into `node_modules/.c12` — they are
 * imported transitively through `#components`, so no tsconfig `exclude` can drop them.
 * Those layers live in their own repos and their `~/…` imports cannot resolve from here,
 * which would leave the gate permanently red on errors nobody can fix in this repo.
 * So the layer diagnostics are reported as a count, and only demo-host's own files fail.
 */

const LAYER_PATH_MARKER = 'node_modules/.c12/'

const result = spawnSync('vue-tsc', ['--build', '--force'], {
  encoding: 'utf8',
  shell: true,
})

const output = `${result.stdout ?? ''}${result.stderr ?? ''}`
const ownDiagnostics = []
let layerDiagnosticCount = 0
let currentDiagnosticIsFromLayer = false

for (const line of output.split(/\r?\n/)) {
  if (line.trim() === '') {
    continue
  }

  const isContinuationLine = /^\s/.test(line)
  if (!isContinuationLine) {
    currentDiagnosticIsFromLayer = line.replaceAll('\\', '/').includes(LAYER_PATH_MARKER)
    if (currentDiagnosticIsFromLayer) {
      layerDiagnosticCount += 1
    }
  }

  if (!currentDiagnosticIsFromLayer) {
    ownDiagnostics.push(line)
  }
}

if (layerDiagnosticCount > 0) {
  console.log(`Ignored ${layerDiagnosticCount} diagnostics from template layers (node_modules/.c12).`)
}

if (ownDiagnostics.length > 0) {
  console.error(ownDiagnostics.join('\n'))
  process.exit(1)
}
