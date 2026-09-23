/**
 * Shared machinery for a DETACHED sidecar video build (site or assistant).
 *
 * The webview kills a single multi-minute HTTP response, so both desktop builds run detached: the app
 * POSTs to start, polls ``/video/build-progress`` until ``done``/``error``, then fetches the file from
 * ``/video/build-result``. That poll-and-fetch loop is identical for the site and the assistant — only
 * what each POSTs (and, for the site, the Storyblok ``needs_login`` handling) differs — so it lives here.
 *
 * @module services/sidecarVideoBuild
 */

/** Current phase of a local video build, as reported by the sidecar. */
export type VideoBuildProgress = {
  step: string
  message: string
  /** Machine-readable failure cause on step "error" (e.g. `needs_login`). */
  reason: string | null
  /** Unix seconds of the last phase change — lets pollers ignore a previous build's entry. */
  updatedAt: number
}

/** Outcome of polling a detached build to completion. */
export type SidecarBuildOutcome =
  | { kind: 'done'; blob: Blob }
  | { kind: 'error'; message: string; reason: string | null }
  | { kind: 'timeout' }

/** Ceiling for a detached local build — capture + montage can take several minutes. */
const BUILD_WAIT_LIMIT_MS: number = 20 * 60 * 1000

/**
 * Current phase of a local build for a slug (polled by the progress modal). Keyed by slug.
 * @param port - The sidecar port.
 * @param token - The one-shot sidecar token.
 * @param slug - Slug of the site/assistant being rendered.
 * @returns The reported phase, or null when unreachable.
 */
export async function fetchBuildProgress(
  port: number,
  token: string,
  slug: string,
): Promise<VideoBuildProgress | null> {
  try {
    const response: Response = await fetch(
      `http://127.0.0.1:${port}/video/build-progress?slug=${encodeURIComponent(slug)}`,
      { headers: { 'X-Sidecar-Token': token } },
    )
    if (!response.ok) return null
    const body: { step?: string; message?: string; reason?: string | null; updated_at?: number } = await response.json()
    return {
      step: body.step ?? 'unknown',
      message: body.message ?? '',
      reason: body.reason ?? null,
      updatedAt: body.updated_at ?? 0,
    }
  } catch {
    return null
  }
}

/**
 * Poll a detached build until done/error/timeout, then fetch the produced file.
 * @param port - The sidecar port.
 * @param token - The one-shot sidecar token.
 * @param slug - Slug of the build to follow.
 * @param startedAtMs - When the POST was sent (ignores a previous build's stale progress entry).
 * @returns The produced blob, or the error/timeout outcome (the caller maps `reason`).
 */
export async function pollAndFetchBuild(
  port: number,
  token: string,
  slug: string,
  startedAtMs: number,
): Promise<SidecarBuildOutcome> {
  const deadlineMs: number = startedAtMs + BUILD_WAIT_LIMIT_MS
  while (Date.now() < deadlineMs) {
    await new Promise<void>((resolve: () => void): void => {
      window.setTimeout(resolve, 2000)
    })
    const progress: VideoBuildProgress | null = await fetchBuildProgress(port, token, slug)
    if (!progress || progress.updatedAt * 1000 < startedAtMs - 2000) continue
    if (progress.step === 'error') {
      return { kind: 'error', message: progress.message || 'Échec de la génération locale.', reason: progress.reason }
    }
    if (progress.step === 'done') {
      let resultResponse: Response
      try {
        resultResponse = await fetch(`http://127.0.0.1:${port}/video/build-result?slug=${encodeURIComponent(slug)}`, {
          headers: { 'X-Sidecar-Token': token },
        })
      } catch {
        return { kind: 'error', message: 'Résultat de la génération inaccessible.', reason: null }
      }
      if (!resultResponse.ok) {
        return { kind: 'error', message: await readSidecarError(resultResponse), reason: null }
      }
      try {
        return { kind: 'done', blob: await resultResponse.blob() }
      } catch (error) {
        return {
          kind: 'error',
          message: error instanceof Error ? error.message : 'Lecture du résultat impossible.',
          reason: null,
        }
      }
    }
  }
  return { kind: 'timeout' }
}

/**
 * Extract the most precise message a failed sidecar response offers.
 * @param response - The failed response.
 * @returns The sidecar `detail` field, or the raw body / status text.
 */
export async function readSidecarError(response: Response): Promise<string> {
  const raw: string = await response.text().catch((): string => '')
  if (!raw) return `Génération locale : erreur ${response.status}`
  try {
    return (JSON.parse(raw).detail as string) || raw
  } catch {
    return raw
  }
}
