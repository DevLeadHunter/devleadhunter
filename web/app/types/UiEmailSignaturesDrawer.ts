/** Internal view of the drawer (list of signatures vs single-signature editor). */
export type SignaturesDrawerView = 'list' | 'editor'

/** Local shape of the signature editor form. */
export type SignatureForm = {
  name: string
  content_html: string
  is_default: boolean
}
