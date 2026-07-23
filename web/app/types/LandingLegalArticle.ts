/**
 * Props for the LandingLegalArticle component.
 */
export type LandingLegalArticleProps = {
  /** i18n key of the article title (e.g. `legal.privacy.title`). */
  titleKey: string
  /** i18n key of the introduction paragraph. */
  introKey: string
  /** Base i18n keys of the sections; `.title` and `.body` are appended (e.g. `legal.privacy.s1`). */
  sectionKeys: string[]
}
