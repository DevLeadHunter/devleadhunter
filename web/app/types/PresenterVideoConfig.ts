/** How the user can obtain the clip. */
export type PresenterVideoCaptureMode = 'record' | 'import'

export type PresenterVideoConfigEmits = {
  'has-video': [hasVideo: boolean]
}
