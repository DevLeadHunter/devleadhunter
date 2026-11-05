/** A demo event captured before the shared PostHog instance was ready, replayed once it is. */
export type DemoEventCapturedBeforeInit = {
  event: string
  properties: Record<string, unknown>
}

export type DemoPageTrackingOptions = {
  shouldCapturePageViews: boolean
  shouldSendEachEventAtOnce: boolean
  slugPropertyName: 'demo_slug' | 'withdrawn_demo_slug'
}
