/** A demo event captured before the shared PostHog instance was ready, replayed once it is. */
export type DemoEventCapturedBeforeInit = {
  event: string
  properties: Record<string, unknown>
}
