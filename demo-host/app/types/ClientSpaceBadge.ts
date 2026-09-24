/** How a badge reads: tinted with the business's colour, alarming, or discreet. */
export type ClientSpaceBadgeTone = 'accent' | 'danger' | 'outline'

/** Props of a client-space badge. */
export type ClientSpaceBadgeProps = {
  tone: ClientSpaceBadgeTone
}
