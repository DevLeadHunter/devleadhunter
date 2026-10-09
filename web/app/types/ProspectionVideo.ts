export type ProspectionVideoStatus = 'ready' | 'failed'

export type ProspectionVideoState = {
  video_status: ProspectionVideoStatus | null
  video_error: string | null
  video_generated_at: string | null
  video_desktop_requested_at: string | null
  is_video_desktop_build_started: boolean
  is_video_made_with_older_clip: boolean
  video_page_url: string | null
  video_thumbnail_url: string | null
}

export type ProspectionVideoSubject = {
  video_status?: string | null
  video_error?: string | null
  video_desktop_requested_at?: string | null
  is_video_desktop_build_started?: boolean
}
