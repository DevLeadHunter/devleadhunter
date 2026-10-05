import type { PresenterVideoSource } from '~/services/presenterVideoService'

export type PresenterVideoTake = {
  id: number
  take_number: number
  is_active: boolean
  original_filename: string | null
  duration_seconds: number
  intro_seconds: number
  outro_seconds: number
  site_seconds: number | null
  auto_generate: boolean
  source: PresenterVideoSource
  clip_url: string | null
  is_clip_missing: boolean
  example_video_url: string | null
  example_subject_id: number | null
  example_subject_name: string | null
  example_generated_at: string | null
  created_at: string | null
  updated_at: string | null
}

export type PresenterVideoTakeList = {
  takes: PresenterVideoTake[]
  auto_generate: boolean
}
