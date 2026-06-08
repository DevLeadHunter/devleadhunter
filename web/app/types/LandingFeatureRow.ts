/**
 * Accent color key for a landing feature row.
 * Maps to the emerald (growth) / blue (data & intelligence) brand accents.
 */
export type LandingFeatureRowAccent = 'emerald' | 'blue'

/**
 * Props for the LandingFeatureRow component.
 */
export interface LandingFeatureRowProps {
  /** FontAwesome icon class for the section badge (e.g. `fa-wand-magic-sparkles`). */
  icon: string
  /** Short eyebrow label shown in the badge above the heading. */
  badge: string
  /** Section heading. */
  heading: string
  /** Supporting paragraph under the heading. */
  description: string
  /** Bullet list of concrete capabilities. */
  features: string[]
  /** Render the visual on the left and the copy on the right when true. */
  reversed?: boolean
  /** Accent color used for the badge, icon and bullet checks. */
  accent?: LandingFeatureRowAccent
}
