/** An API error as `$fetch` throws it: the HTTP status, and FastAPI's `detail` (a sentence, or a list of field errors). */
export type ApiRefusal = {
  statusCode?: number
  data?: { detail?: unknown }
}
