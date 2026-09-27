/** PostHog events emitted by the prospection-video player page, read back by the API lead scoring. */
export type DemoVideoEvent =
  | 'demo_video_play'
  | 'demo_video_resume'
  | 'demo_video_pause'
  | 'demo_video_replay'
  | 'demo_video_progress'
  | 'demo_video_complete'
  | 'demo_video_watch_time'
  | 'demo_video_seek'
  | 'demo_video_fullscreen'
  | 'demo_video_mute'
  | 'demo_video_cta_click'
  | 'demo_video_endcard_shown'

export type DemoVideoEventCapture = (event: DemoVideoEvent, properties?: Record<string, unknown>) => void

/** Module the video page belongs to: 'demo' for the website (/v), 'assistant' for the receptionist (/va). */
export type DemoVideoSurface = 'demo' | 'assistant'
