/** The business identity an embedder pushes through `dlh:preview`: a field is null when the message carried no valid value. */
export type DemoPreviewIdentity = {
  businessName: string | null
  phone: string | null
  city: string | null
  area: string | null
  logoUrl: string | null
}
