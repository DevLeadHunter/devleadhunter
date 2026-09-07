/**
 * Desktop-only orchestration of the Storyblok editor video background.
 *
 * The video *background* (linear site scroll + real Storyblok editor edit) can only
 * be produced on the user's machine, where their Storyblok session lives, so it runs
 * in the bundled sidecar. This service drives it: read the session state, open the
 * one-time login window, and produce + upload a site's background before the montage.
 *
 * Every call is a no-op (returns a neutral value) outside the desktop shell, so the
 * web build simply falls back to the site-only video.
 *
 * @module services/storyblokSidecarService
 */
import { DemoSiteService } from '~/services/demoSiteService'
import { ProfilePhotoService } from '~/services/profilePhotoService'
import { getScraperSidecarInfo } from '~/services/scraperSidecarService'

/** Connection state of the Storyblok owner session used for the editor sequence. */
export type StoryblokSessionState = 'ready' | 'needs_login' | 'busy' | 'unknown'

/** Session state as reported by the sidecar. */
export type StoryblokSessionInfo = {
  state: StoryblokSessionState
  source: string | null
  loginWindowOpen: boolean
}

/**
 * Outcome of preparing a site's video background before generation.
 * - `uploaded`: the editor background was produced and stored.
 * - `needs_login`: the Storyblok session is expired/absent — the caller must prompt a reconnect.
 * - `skipped`: no editor sequence this time (transient), montage proceeds site-only.
 * - `unavailable`: not the desktop shell — the web build uses the server-side fallback.
 */
export type BackgroundPreparation = 'uploaded' | 'needs_login' | 'skipped' | 'unavailable'

/**
 * Outcome of a full desktop video build.
 * - `done`: the whole video was rendered locally and stored.
 * - `needs_login`: the Storyblok session is expired/absent — prompt a reconnect.
 * - `unavailable`: not the desktop shell — the caller uses the server-side path.
 * - `failed`: something went wrong locally — the caller falls back to the server.
 */
export type FullVideoBuildStatus = 'done' | 'needs_login' | 'unavailable' | 'failed'

/** Result of a full desktop video build, with a message when it failed. */
export type FullVideoBuildResult = {
  status: FullVideoBuildStatus
  message?: string
}

/** Timing overrides a preview build applies, straight from the unsaved settings form. */
export type PreviewTimingOverrides = {
  presenter_intro: number
  presenter_outro: number
  site_seconds: number
  total_seconds: number
}

/** Result of a preview build: the rendered mp4 when it worked, nothing published. */
export type PreviewVideoResult = {
  status: FullVideoBuildStatus
  video?: Blob
  message?: string
}

/** Current phase of a local video build, as reported by the sidecar. */
export type VideoBuildProgress = {
  step: string
  message: string
  /** Machine-readable failure cause on step "error" (e.g. `needs_login`). */
  reason: string | null
  /** Unix seconds of the last phase change — lets pollers ignore a previous build's entry. */
  updatedAt: number
}

const UNKNOWN_SESSION: StoryblokSessionInfo = { state: 'unknown', source: null, loginWindowOpen: false }

/** Ceiling for a detached local build — capture + montage can take several minutes. */
const BUILD_WAIT_LIMIT_MS: number = 20 * 60 * 1000

export class StoryblokSidecarService {
  /**
   * Read the Storyblok session state from the sidecar.
   * @returns The state, or `unknown` outside the desktop app / when unreachable.
   */
  static async getSessionState(): Promise<StoryblokSessionInfo> {
    const info: Awaited<ReturnType<typeof getScraperSidecarInfo>> = await getScraperSidecarInfo()
    if (!info) return UNKNOWN_SESSION
    try {
      const response: Response = await fetch(`http://127.0.0.1:${info.port}/storyblok/session`, {
        headers: { 'X-Sidecar-Token': info.token },
      })
      if (!response.ok) return UNKNOWN_SESSION
      const body: { state?: StoryblokSessionState; source?: string | null; login_window_open?: boolean } =
        await response.json()
      return {
        state: body.state ?? 'unknown',
        source: body.source ?? null,
        loginWindowOpen: Boolean(body.login_window_open),
      }
    } catch {
      return UNKNOWN_SESSION
    }
  }

  /**
   * Open the one-time Storyblok sign-in window (dedicated profile fallback).
   * @returns True when a window was opened.
   */
  static async openLogin(): Promise<boolean> {
    const info: Awaited<ReturnType<typeof getScraperSidecarInfo>> = await getScraperSidecarInfo()
    if (!info) return false
    try {
      const response: Response = await fetch(`http://127.0.0.1:${info.port}/storyblok/open-login`, {
        method: 'POST',
        headers: { 'X-Sidecar-Token': info.token },
      })
      return response.ok
    } catch {
      return false
    }
  }

  /**
   * Forget the Storyblok session (wrong account?) so the user can reconnect.
   * @returns True when the session was cleared.
   */
  static async logout(): Promise<boolean> {
    const info: Awaited<ReturnType<typeof getScraperSidecarInfo>> = await getScraperSidecarInfo()
    if (!info) return false
    try {
      const response: Response = await fetch(`http://127.0.0.1:${info.port}/storyblok/logout`, {
        method: 'POST',
        headers: { 'X-Sidecar-Token': info.token },
      })
      return response.ok
    } catch {
      return false
    }
  }

  /**
   * Build the COMPLETE prospection video on the desktop (capture + montage).
   *
   * Fetches the context + presenter clip, has the sidecar render everything with its
   * bundled ffmpeg, then uploads the finished video — the VPS is never involved.
   * Returns `unavailable` off the desktop, `needs_login` when Storyblok is expired,
   * `failed` (with a message) on any local error so the caller can fall back.
   * @param demoSiteId - The demo site to generate.
   * @returns The build outcome.
   */
  static async buildFullVideo(demoSiteId: number): Promise<FullVideoBuildResult> {
    const build: { status: FullVideoBuildStatus; blob?: Blob; message?: string } =
      await StoryblokSidecarService.requestFullBuild(demoSiteId, {})
    if (build.status !== 'done' || !build.blob) {
      return { status: build.status, message: build.message }
    }
    try {
      await DemoSiteService.uploadFinalVideo(demoSiteId, build.blob)
    } catch (error) {
      return { status: 'failed', message: error instanceof Error ? error.message : 'Envoi de la vidéo échoué.' }
    }
    return { status: 'done' }
  }

  /**
   * Render a CALIBRATION preview of the video on the desktop, publishing nothing.
   *
   * Same local pipeline as a real generation, but the given (possibly unsaved)
   * timings override the stored settings and the mp4 comes straight back to be
   * played inline — the site's real video is untouched.
   * @param demoSiteId - The demo site used as the example.
   * @param overrides - Timings from the settings form.
   * @returns The rendered mp4, or why it could not be produced.
   */
  static async buildPreviewVideo(demoSiteId: number, overrides: PreviewTimingOverrides): Promise<PreviewVideoResult> {
    const build: { status: FullVideoBuildStatus; blob?: Blob; message?: string } =
      await StoryblokSidecarService.requestFullBuild(demoSiteId, { ...overrides, preview: true })
    if (build.status !== 'done' || !build.blob) {
      return { status: build.status, message: build.message }
    }
    return { status: 'done', video: build.blob }
  }

  /**
   * Current phase of a local video build for a site (polled by the progress modal).
   * @param slug - Slug of the demo site being rendered.
   * @returns The reported phase, or null outside the desktop app / when unreachable.
   */
  static async getVideoBuildProgress(slug: string): Promise<VideoBuildProgress | null> {
    const info: Awaited<ReturnType<typeof getScraperSidecarInfo>> = await getScraperSidecarInfo()
    if (!info) return null
    try {
      const response: Response = await fetch(
        `http://127.0.0.1:${info.port}/video/build-progress?slug=${encodeURIComponent(slug)}`,
        { headers: { 'X-Sidecar-Token': info.token } },
      )
      if (!response.ok) return null
      const body: { step?: string; message?: string; reason?: string | null; updated_at?: number } =
        await response.json()
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
   * Run the sidecar's full desktop build (capture + montage) for a site.
   *
   * Shared by the real generation and the calibration preview; ``payloadExtras``
   * is merged over the API context (e.g. timing overrides, the preview flag).
   * The build is DETACHED sidecar-side (a single multi-minute response gets
   * killed by the webview): start it, poll its progress, then fetch the file.
   * @param demoSiteId - The demo site to render.
   * @param payloadExtras - Fields merged over the context before sending.
   * @returns The produced file, or the failure status.
   */
  private static async requestFullBuild(
    demoSiteId: number,
    payloadExtras: Record<string, unknown>,
  ): Promise<{ status: FullVideoBuildStatus; blob?: Blob; message?: string }> {
    const info: Awaited<ReturnType<typeof getScraperSidecarInfo>> = await getScraperSidecarInfo()
    if (!info) return { status: 'unavailable' }

    let context: Awaited<ReturnType<typeof DemoSiteService.getVideoBackgroundContext>>
    let presenter: Blob
    try {
      context = await DemoSiteService.getVideoBackgroundContext(demoSiteId)
      presenter = await DemoSiteService.fetchPresenterVideoFile()
    } catch (error) {
      return { status: 'failed', message: error instanceof Error ? error.message : 'Contexte vidéo indisponible.' }
    }
    // La photo est optionnelle : son absence (ou une erreur) ne bloque jamais le build.
    let presenterPhoto: Blob | null = null
    try {
      presenterPhoto = await ProfilePhotoService.fetchProfilePhotoBlob()
    } catch {
      presenterPhoto = null
    }

    const formData: FormData = new FormData()
    formData.append('payload', JSON.stringify({ ...context, ...payloadExtras }))
    formData.append('presenter', presenter, 'presenter.mp4')
    if (presenterPhoto) {
      formData.append('presenter_photo', presenterPhoto, 'presenter-photo.jpg')
    }

    let startResponse: Response
    try {
      startResponse = await fetch(`http://127.0.0.1:${info.port}/video/build-full`, {
        method: 'POST',
        headers: { 'X-Sidecar-Token': info.token },
        body: formData,
      })
    } catch {
      return { status: 'failed', message: 'Le générateur local ne répond pas.' }
    }

    if (startResponse.status === 409) {
      const reason: string | null = await startResponse
        .json()
        .then((body: { reason?: string }): string | null => body?.reason ?? null)
        .catch((): null => null)
      return { status: reason === 'needs_login' ? 'needs_login' : 'failed' }
    }
    if (!startResponse.ok) {
      return { status: 'failed', message: await StoryblokSidecarService.readSidecarError(startResponse) }
    }

    // The build runs detached — follow it through the progress endpoint.
    const startedAtMs: number = Date.now()
    const deadlineMs: number = startedAtMs + BUILD_WAIT_LIMIT_MS
    while (Date.now() < deadlineMs) {
      await new Promise<void>((resolve: () => void): void => {
        window.setTimeout(resolve, 2000)
      })
      const progress: VideoBuildProgress | null = await StoryblokSidecarService.getVideoBuildProgress(context.slug)
      if (!progress || progress.updatedAt * 1000 < startedAtMs - 2000) continue
      if (progress.step === 'error') {
        if (progress.reason === 'needs_login') return { status: 'needs_login' }
        return { status: 'failed', message: progress.message || 'Échec de la génération locale.' }
      }
      if (progress.step === 'done') {
        let resultResponse: Response
        try {
          resultResponse = await fetch(
            `http://127.0.0.1:${info.port}/video/build-result?slug=${encodeURIComponent(context.slug)}`,
            { headers: { 'X-Sidecar-Token': info.token } },
          )
        } catch {
          return { status: 'failed', message: 'Résultat de la génération inaccessible.' }
        }
        if (!resultResponse.ok) {
          return { status: 'failed', message: await StoryblokSidecarService.readSidecarError(resultResponse) }
        }
        try {
          return { status: 'done', blob: await resultResponse.blob() }
        } catch (error) {
          return {
            status: 'failed',
            message: error instanceof Error ? error.message : 'Lecture du résultat impossible.',
          }
        }
      }
    }
    return { status: 'failed', message: 'Génération trop longue — réessayez.' }
  }

  /**
   * Produce a site's video background on the sidecar and upload it to the API.
   *
   * Best-effort: returns `skipped` when there is no Storyblok session (the montage
   * then composes without the editor sequence) and `unavailable` outside the desktop
   * shell. Runs the browser capture, so it takes a minute or two.
   *
   * @param demoSiteId - The demo site to prepare.
   * @returns What happened, for the caller to message the user.
   */
  static async prepareVideoBackground(demoSiteId: number): Promise<BackgroundPreparation> {
    const info: Awaited<ReturnType<typeof getScraperSidecarInfo>> = await getScraperSidecarInfo()
    if (!info) return 'unavailable'

    const context: Record<string, unknown> = await DemoSiteService.getVideoBackgroundContext(demoSiteId)

    let response: Response
    try {
      response = await fetch(`http://127.0.0.1:${info.port}/storyblok/background-clip`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'X-Sidecar-Token': info.token },
        body: JSON.stringify(context),
      })
    } catch {
      return 'skipped'
    }

    // 409 = no usable Storyblok session. reason=needs_login means the session is
    // expired/absent → the caller prompts a reconnect (never a silent VPS fallback);
    // any other 409 is a transient skip (montage proceeds site-only).
    if (response.status === 409) {
      const reason: string | null = await response
        .json()
        .then((body: { reason?: string }): string | null => body?.reason ?? null)
        .catch((): null => null)
      return reason === 'needs_login' ? 'needs_login' : 'skipped'
    }
    // Any other failure is surfaced so the cause (session, capture, upload) is visible.
    if (!response.ok) throw new Error(await StoryblokSidecarService.readSidecarError(response))

    const clip: Blob = await response.blob()
    await DemoSiteService.uploadVideoBackground(demoSiteId, clip)
    return 'uploaded'
  }

  /**
   * Extract the most precise message a failed sidecar response offers.
   * @param response - The failed response.
   * @returns The sidecar `detail` field, or the raw body / status text.
   */
  private static async readSidecarError(response: Response): Promise<string> {
    const raw: string = await response.text().catch((): string => '')
    if (!raw) return `Séquence Storyblok : erreur ${response.status}`
    try {
      return (JSON.parse(raw).detail as string) || raw
    } catch {
      return raw
    }
  }
}
