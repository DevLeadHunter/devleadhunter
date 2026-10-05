import type { PresenterVideoTake } from '~/types/PresenterVideoTake'

export type PresenterVideoTakeCardProps = {
  take: PresenterVideoTake
  canBuildExample: boolean
  isBuildingExample: boolean
  isAnotherBuildRunning: boolean
  isActivating: boolean
  isDeleting: boolean
  canDelete: boolean
  selectedExampleDemoId: number | null
}

export type PresenterVideoTakeCardEmits = {
  activate: []
  'build-example': []
  delete: []
}
