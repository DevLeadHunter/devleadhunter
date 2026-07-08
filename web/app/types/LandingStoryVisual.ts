/** Index of a pipeline story act (0 = find, 1 = generate, 2 = reach out, 3 = get paid). */
export type LandingStoryActIndex = 0 | 1 | 2 | 3

/**
 * Props for the LandingStoryVisual component.
 */
export interface LandingStoryVisualProps {
  /** Which act of the prospect journey this visual illustrates. */
  actIndex: LandingStoryActIndex
}
