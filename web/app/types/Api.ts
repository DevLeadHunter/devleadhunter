/** The body FastAPI sends with an error: a sentence, or a list of field errors after a validation failure. */
export type ApiErrorBody = {
  detail?: string | unknown[]
}
