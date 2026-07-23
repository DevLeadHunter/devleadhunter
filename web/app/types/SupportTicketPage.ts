/** Shape of the realtime events pushed on the support websockets. */
export type SupportWebsocketEvent = {
  event?: string
  data?: Record<string, unknown>
}
