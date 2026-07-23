import type { LandingStoryActIndex } from '~/types/LandingStoryVisual'

/** One act of the prospect journey shown in the scroll narrative. */
export type LandingStoryAct = {
  actIndex: LandingStoryActIndex
  verbKey: string
  descriptionKey: string
}
