/** A demo event captured before the shared PostHog instance was ready, replayed once it is. */
export type DemoEventCapturedBeforeInit = {
  event: string
  properties: Record<string, unknown>
}

export type DemoBeaconBrowserSignals = {
  browser_timezone: string | null
  browser_language: string | null
  is_automated_browser: boolean
}

export type DemoPageTrackingOptions = {
  shouldCapturePageViews: boolean
  shouldSendEachEventAtOnce: boolean
  slugPropertyName: 'demo_slug' | 'withdrawn_demo_slug'
}

/** Module a tracked page belongs to: its PostHog `surface` name and whether it still tracks in a frame. */
export type DemoTrackingSurface = {
  name: string
  shouldTrackInsideFrame: boolean
}
