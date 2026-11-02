import type { DemoPreviewIdentity } from '~/types/DemoPreviewIdentity'

const MINIMUM_REPLACED_VALUE_LENGTH: number = 3

const IDENTITY_FIELDS: readonly string[] = ['businessName', 'phone', 'city', 'area', 'logo']

/** Merges a live-edit identity into a site's content: the identity fields, then every text repeating a published value. */
export class DemoPreviewIdentityUtils {
  /**
   * The content with the identity applied. The published content is left untouched.
   * @param content - The flat site content being assembled for the preview.
   * @param identity - The identity pushed by the embedder (null fields are left as published).
   * @returns A new content object.
   */
  static apply(content: Record<string, unknown>, identity: DemoPreviewIdentity): Record<string, unknown> {
    const replacements: Array<[string, string]> = DemoPreviewIdentityUtils.replacements(content, identity)
    const rewritten: Record<string, unknown> = DemoPreviewIdentityUtils.rewriteTexts(content, replacements) as Record<
      string,
      unknown
    >
    const area: string | null = identity.area ?? identity.city

    if (identity.businessName) {
      rewritten.businessName = identity.businessName
    }
    if (identity.phone) {
      rewritten.phone = identity.phone
    }
    if (identity.city) {
      rewritten.city = identity.city
    }
    if (area) {
      rewritten.area = area
    }
    if (identity.logoUrl) {
      rewritten.logo = identity.logoUrl
    }
    return rewritten
  }

  /**
   * The published value → new value pairs worth swapping inside the texts, longest first so « Rennes
   * Métropole » is replaced before « Rennes ».
   * @param content - The published content.
   * @param identity - The identity pushed by the embedder.
   * @returns The pairs, without duplicates.
   */
  private static replacements(
    content: Record<string, unknown>,
    identity: DemoPreviewIdentity,
  ): Array<[string, string]> {
    const candidates: Array<[unknown, string | null]> = [
      [content.businessName, identity.businessName],
      [content.area, identity.area ?? identity.city],
      [content.city, identity.city],
      [content.phone, identity.phone],
    ]
    const pairs: Map<string, string> = new Map<string, string>()

    for (const [published, next] of candidates) {
      if (typeof published !== 'string' || !next) {
        continue
      }
      const previous: string = published.trim()

      if (previous.length < MINIMUM_REPLACED_VALUE_LENGTH || previous === next || pairs.has(previous)) {
        continue
      }
      pairs.set(previous, next)
    }
    return Array.from(pairs.entries()).sort(
      (first: [string, string], second: [string, string]): number => second[0].length - first[0].length,
    )
  }

  /**
   * A copy of a content node with the replacements applied to every text that is neither a URL nor one of
   * the identity fields themselves.
   * @param node - Any value of the content tree.
   * @param replacements - The published value → new value pairs.
   * @returns The rewritten copy (the same value for numbers, booleans and null).
   */
  private static rewriteTexts(node: unknown, replacements: Array<[string, string]>): unknown {
    if (replacements.length === 0) {
      return node
    }
    if (typeof node === 'string') {
      return DemoPreviewIdentityUtils.rewriteText(node, replacements)
    }
    if (Array.isArray(node)) {
      return node.map((item: unknown): unknown => DemoPreviewIdentityUtils.rewriteTexts(item, replacements))
    }
    if (typeof node === 'object' && node !== null) {
      const rewritten: Record<string, unknown> = {}

      for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
        rewritten[key] = IDENTITY_FIELDS.includes(key)
          ? value
          : DemoPreviewIdentityUtils.rewriteTexts(value, replacements)
      }
      return rewritten
    }
    return node
  }

  /**
   * One text with the replacements applied; a URL is never touched.
   * @param text - The text.
   * @param replacements - The published value → new value pairs.
   * @returns The rewritten text.
   */
  private static rewriteText(text: string, replacements: Array<[string, string]>): string {
    if (/^(https?:\/\/|data:)/.test(text)) {
      return text
    }
    let rewritten: string = text

    for (const [previous, next] of replacements) {
      rewritten = rewritten.split(previous).join(next)
    }
    return rewritten
  }
}
