/** Index of a pipeline story act (0 = find, 1 = generate, 2 = reach out, 3 = get paid). */
export type LandingStoryActIndex = 0 | 1 | 2 | 3

export type LandingStoryVisualProps = {
  actIndex: LandingStoryActIndex
}
