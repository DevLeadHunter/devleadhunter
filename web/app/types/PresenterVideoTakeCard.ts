import type { PresenterVideoTake } from '~/types/PresenterVideoTake'

export type PresenterVideoTakeCardProps = {
  take: PresenterVideoTake
  isActivating: boolean
  isDeleting: boolean
  canDelete: boolean
  selectedExampleDemoId: number | null
}

export type PresenterVideoTakeCardEmits = {
  activate: []
  delete: []
}
