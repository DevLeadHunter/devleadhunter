/** Shape of the realtime events pushed on the tickets websocket. */
export type SupportWebsocketEvent = {
  event?: string
  data?: Record<string, unknown>
}
